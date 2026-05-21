"""Read-only Stage 6 recovery checker for the Windows operator PC.

Run this locally on the operator PC after ``Restart-Service sshd`` when a
remote Stage 6 smoke was interrupted. It does not clean up or reconfigure
anything; it only reports whether the weekly scheduled task still points at the
expected runtime when an expected action is explicitly supplied and whether
known interrupted-smoke artifacts remain.
"""

from __future__ import annotations

import argparse
import json
import locale
import os
import platform
import socket
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn
from xml.etree import ElementTree

TASK_NAME = "EIDP Weekly Run"
CMD_META_CHARS = frozenset('&|<>^%!"\r\n')
DEFAULT_INTERRUPTED_STAGE6_PATHS: tuple[str, ...] = (
    r"%USERPROFILE%\EIDP-v384-75732b0-ocr-sr-sandbox",
    r"%USERPROFILE%\v384_ocr_sr_smoke.ps1",
    r"%USERPROFILE%\eidp-windows-v384.zip",
    r"%USERPROFILE%\eidp-windows-v384.zip.sha256",
    r"%USERPROFILE%\eidp-ocr-addon-windows-v383-smoke.zip",
    r"%USERPROFILE%\eidp_v384_ocr_sr_smoke.py",
    r"%USERPROFILE%\eidp-v384-ocr-sr-source.sqlite3",
)


def _disable_wmi_platform_queries() -> None:
    """Avoid Windows WMI hangs before emitting diagnostics.

    This script is run directly from the scripts directory during diagnostics, so it does
    not import ``eidp`` and cannot rely on the package startup hook.
    """

    wmi_query = getattr(platform, "_wmi_query", None)
    if wmi_query is None or getattr(wmi_query, "_eidp_wmi_disabled", False):
        return

    def _raise_oserror(*_args: object, **_kwargs: object) -> NoReturn:
        raise OSError("WMI disabled for EIDP Windows platform detection")

    setattr(_raise_oserror, "_eidp_wmi_disabled", True)
    setattr(platform, "_wmi_query", _raise_oserror)


_disable_wmi_platform_queries()


@dataclass(frozen=True)
class ScheduledTaskSnapshot:
    exists: bool
    execute: str | None = None
    arguments: str | None = None
    error: str | None = None


def _task_xml_text(root: ElementTree.Element, local_name: str) -> str | None:
    for elem in root.iter():
        if elem.tag.rsplit("}", 1)[-1] == local_name and elem.text:
            return elem.text.strip()
    return None


def parse_task_xml(xml_text: str) -> ScheduledTaskSnapshot:
    root = ElementTree.fromstring(xml_text)
    return ScheduledTaskSnapshot(
        exists=True,
        execute=_task_xml_text(root, "Command"),
        arguments=_task_xml_text(root, "Arguments"),
    )


def _decode_process_output(data: bytes) -> str:
    if not data:
        return ""

    # Some Windows schtasks builds emit ASCII/UTF-8 bytes while the XML header
    # still declares UTF-16. Decoding those bytes as utf-16 can succeed into
    # garbage, so only prefer UTF-16 when the byte shape makes it plausible.
    likely_utf16 = data.startswith((b"\xff\xfe", b"\xfe\xff")) or b"\x00" in data[:80]
    encodings = (
        ("utf-16", "utf-8-sig", locale.getpreferredencoding(False))
        if likely_utf16
        else ("utf-8-sig", locale.getpreferredencoding(False), "utf-16")
    )
    for encoding in encodings:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode(errors="replace")


def query_weekly_task(task_name: str = TASK_NAME) -> ScheduledTaskSnapshot:
    try:
        proc = subprocess.run(
            ["schtasks", "/Query", "/TN", task_name, "/XML"],
            check=False,
            capture_output=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return ScheduledTaskSnapshot(exists=False, error=str(exc))

    if proc.returncode != 0:
        detail = (_decode_process_output(proc.stderr) or _decode_process_output(proc.stdout)).strip()
        return ScheduledTaskSnapshot(exists=False, error=detail or f"schtasks returned {proc.returncode}")

    try:
        return parse_task_xml(_decode_process_output(proc.stdout))
    except ElementTree.ParseError as exc:
        return ScheduledTaskSnapshot(exists=True, error=f"failed to parse schtasks XML: {exc}")


def _normalise_windows_path(value: str | None) -> str | None:
    if not value:
        return None
    return os.path.normcase(value.strip().strip('"').replace("/", "\\"))


def _path_status(raw_path: str) -> dict[str, object]:
    expanded = os.path.expandvars(raw_path)
    return {
        "path": expanded,
        "exists": Path(expanded).exists(),
    }


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _default_lock_path() -> str:
    app_root = Path(os.environ.get("EIDP_APP_ROOT") or _repo_root())
    return str(app_root / "data" / ".lock")


def _tail_text(value: str | bytes | None, *, max_chars: int = 2000) -> str:
    if value is None:
        return ""
    text = value.decode(errors="replace") if isinstance(value, bytes) else value
    return text[-max_chars:]


def _weekly_probe_command(weekly_action: str) -> list[str]:
    if os.name == "nt":  # pragma: no cover - exercised on the operator PC.
        if any(char in weekly_action for char in CMD_META_CHARS):
            raise ValueError("weekly_run.bat path contains unsafe cmd.exe metacharacters")
        return ["cmd.exe", "/D", "/C", f'call "{weekly_action}"']
    return [weekly_action]


def probe_weekly_dry_run(weekly_action: str, *, timeout_seconds: float = 60.0) -> dict[str, object]:
    expanded = os.path.expandvars(weekly_action)
    if not Path(expanded).exists():
        return {
            "enabled": True,
            "ok": False,
            "path": expanded,
            "error": "weekly_run.bat path does not exist",
            "timeout_seconds": timeout_seconds,
        }

    env = os.environ.copy()
    env.update(
        {
            "EIDP_WEEKLY_DRY_RUN": "1",
            "EIDP_WEEKLY_LIMIT": "0",
            "EIDP_WEEKLY_BATCH_SIZE": "1",
            "EIDP_WEEKLY_RATE_LIMIT": "0",
            "EIDP_WEEKLY_REQUEST_TIMEOUT": "1",
        }
    )
    try:
        proc = subprocess.run(
            _weekly_probe_command(expanded),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "enabled": True,
            "ok": False,
            "path": expanded,
            "error": "weekly_run.bat dry-run probe timed out",
            "timeout_seconds": timeout_seconds,
            "stdout_tail": _tail_text(exc.stdout),
            "stderr_tail": _tail_text(exc.stderr),
        }
    except ValueError as exc:
        return {
            "enabled": True,
            "ok": False,
            "path": expanded,
            "error": str(exc),
            "timeout_seconds": timeout_seconds,
        }
    except OSError as exc:
        return {
            "enabled": True,
            "ok": False,
            "path": expanded,
            "error": str(exc),
            "timeout_seconds": timeout_seconds,
        }

    return {
        "enabled": True,
        "ok": proc.returncode == 0,
        "path": expanded,
        "returncode": proc.returncode,
        "timeout_seconds": timeout_seconds,
        "stdout_tail": _tail_text(proc.stdout),
        "stderr_tail": _tail_text(proc.stderr),
    }


def probe_data_lock(lock_path: str | None = None) -> dict[str, object]:
    expanded = os.path.expandvars(lock_path or _default_lock_path())
    src_root = _repo_root() / "src"
    if src_root.exists() and str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))

    try:
        from eidp.db.locking import probe_lock as _probe_lock

        status = _probe_lock(Path(expanded))
    except Exception as exc:  # pragma: no cover - defensive Windows diagnostics path.
        return {
            "enabled": True,
            "ok": False,
            "path": expanded,
            "error": f"{type(exc).__name__}: {exc}",
        }

    return {
        "enabled": True,
        "ok": not status.held,
        "path": expanded,
        "held": status.held,
        "owner": status.owner,
        "pid": status.pid,
        "started_at": status.started_at,
    }


def build_report(
    *,
    expected_weekly_action: str | None,
    check_paths: list[str],
    task: ScheduledTaskSnapshot | None = None,
    probe_weekly_dry_run: bool = False,
    weekly_probe_timeout_seconds: float = 60.0,
    weekly_probe_runner: Callable[..., dict[str, object]] | None = None,
    probe_lock: bool = False,
    lock_path: str | None = None,
    lock_probe_runner: Callable[..., dict[str, object]] | None = None,
) -> dict[str, object]:
    task = task or query_weekly_task()
    expected_norm = _normalise_windows_path(expected_weekly_action)
    actual_norm = _normalise_windows_path(task.execute)
    action_matches = (actual_norm == expected_norm) if expected_norm is not None else None
    residual_paths = [_path_status(path) for path in check_paths]
    residual_existing = [item for item in residual_paths if item["exists"]]
    weekly_probe: dict[str, object] = {"enabled": False}
    if probe_weekly_dry_run:
        probe_action = expected_weekly_action or task.execute
        if probe_action:
            runner = weekly_probe_runner or probe_weekly_dry_run_fn
            weekly_probe = runner(probe_action, timeout_seconds=weekly_probe_timeout_seconds)
        else:
            weekly_probe = {
                "enabled": True,
                "ok": False,
                "error": "no weekly_run.bat action available to probe",
            }
    lock_probe: dict[str, object] = {"enabled": False}
    if probe_lock:
        lock_runner = lock_probe_runner or probe_data_lock
        lock_probe = lock_runner(lock_path)

    task_action_ok = expected_norm is None or action_matches is True
    weekly_probe_ok = not weekly_probe.get("enabled") or weekly_probe.get("ok") is True
    lock_probe_ok = not lock_probe.get("enabled") or lock_probe.get("ok") is True
    ok = bool(
        task.exists
        and not task.error
        and task_action_ok
        and not residual_existing
        and weekly_probe_ok
        and lock_probe_ok
    )
    recommendations: list[str] = []
    if task.error:
        recommendations.append("Confirm the EIDP Weekly Run scheduled task manually.")
    if expected_norm is None:
        recommendations.append(
            "Scheduled task action check skipped; pass --expected-weekly-action to verify the production runtime path."
        )
    elif not action_matches:
        recommendations.append("Restore EIDP Weekly Run to the production weekly_run.bat before resuming Stage 6.")
    if residual_existing:
        recommendations.append("Review and remove interrupted smoke artifacts before rerunning copied-DB smoke.")
    if weekly_probe.get("enabled") and weekly_probe.get("ok") is not True:
        recommendations.append(
            "weekly_run.bat dry-run probe failed; rerun setup or inspect the weekly log before Stage 6."
        )
    if lock_probe.get("enabled") and lock_probe.get("ok") is not True:
        recommendations.append("Wait for the current EIDP operation to finish, then rerun the recovery check.")

    return {
        "ok": ok,
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "task": {
            "name": TASK_NAME,
            "exists": task.exists,
            "execute": task.execute,
            "arguments": task.arguments,
            "error": task.error,
            "expected_action": expected_weekly_action,
            "action_matches_expected": action_matches,
        },
        "weekly_dry_run_probe": weekly_probe,
        "lock_probe": lock_probe,
        "residual_paths": residual_paths,
        "recommendations": recommendations,
    }


probe_weekly_dry_run_fn = probe_weekly_dry_run


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--expected-weekly-action",
        help=(
            r"Expected production weekly_run.bat path, "
            r"e.g. C:\Users\eidp_operator\EIDP-vXXX-abcdef0\scripts\weekly_run.bat"
        ),
    )
    parser.add_argument(
        "--check-path",
        action="append",
        default=[],
        help="Additional interrupted-smoke path to check. Can be repeated.",
    )
    parser.add_argument(
        "--probe-weekly-dry-run",
        action="store_true",
        help="Run weekly_run.bat with EIDP_WEEKLY_DRY_RUN=1 and EIDP_WEEKLY_LIMIT=0 to verify executability.",
    )
    parser.add_argument(
        "--weekly-probe-timeout",
        type=float,
        default=60.0,
        help="Timeout in seconds for --probe-weekly-dry-run.",
    )
    parser.add_argument(
        "--probe-lock",
        action="store_true",
        help="Probe the shared EIDP data/.lock and fail if another process currently holds it.",
    )
    parser.add_argument(
        "--lock-path",
        help=r"Override lock path for --probe-lock. Defaults to %EIDP_APP_ROOT%\data\.lock.",
    )
    parser.add_argument("--json", action="store_true", help="Emit compact JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    check_paths = [*DEFAULT_INTERRUPTED_STAGE6_PATHS, *args.check_path]
    report = build_report(
        expected_weekly_action=args.expected_weekly_action,
        check_paths=check_paths,
        probe_weekly_dry_run=args.probe_weekly_dry_run,
        weekly_probe_timeout_seconds=args.weekly_probe_timeout,
        probe_lock=args.probe_lock,
        lock_path=args.lock_path,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

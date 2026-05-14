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
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn
from xml.etree import ElementTree

TASK_NAME = "EIDP Weekly Run"
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


def build_report(
    *,
    expected_weekly_action: str | None,
    check_paths: list[str],
    task: ScheduledTaskSnapshot | None = None,
) -> dict[str, object]:
    task = task or query_weekly_task()
    expected_norm = _normalise_windows_path(expected_weekly_action)
    actual_norm = _normalise_windows_path(task.execute)
    action_matches = (actual_norm == expected_norm) if expected_norm is not None else None
    residual_paths = [_path_status(path) for path in check_paths]
    residual_existing = [item for item in residual_paths if item["exists"]]

    task_action_ok = expected_norm is None or action_matches is True
    ok = bool(task.exists and not task.error and task_action_ok and not residual_existing)
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
        "residual_paths": residual_paths,
        "recommendations": recommendations,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--expected-weekly-action",
        help=r"Expected production weekly_run.bat path, e.g. C:\Users\cyo20\EIDP-v380-f6a5e6d\scripts\weekly_run.bat",
    )
    parser.add_argument(
        "--check-path",
        action="append",
        default=[],
        help="Additional interrupted-smoke path to check. Can be repeated.",
    )
    parser.add_argument("--json", action="store_true", help="Emit compact JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    check_paths = [*DEFAULT_INTERRUPTED_STAGE6_PATHS, *args.check_path]
    report = build_report(expected_weekly_action=args.expected_weekly_action, check_paths=check_paths)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

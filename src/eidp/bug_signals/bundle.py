"""Build sanitized local bug-report bundles."""

from __future__ import annotations

import json
import platform
import re
import shutil
import sys
import zipfile
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eidp.bug_signals.detector import BugSignal, scan_bug_signals

SCRUB_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"C:[\\/]+Users[\\/]+[^\\/\"'\r\n]+", re.IGNORECASE), "C:/Users/<REDACTED>"),
    (re.compile(r"/Users/[^/\"'\r\n]+"), r"/Users/<REDACTED>"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "<EMAIL>"),
    (
        re.compile(
            r"\b([A-Z0-9_]*(?:API[_-]?KEY|TOKEN|SECRET|PASSWORD|PASS|CREDENTIAL)[A-Z0-9_]*\s*[:=]\s*)"
            r"[^\s,;\"']+",
            re.IGNORECASE,
        ),
        r"\1<REDACTED>",
    ),
    (re.compile(r'("school_name"\s*:\s*")[^"]+(")'), r'\1<REDACTED>\2'),
    (re.compile(r'("operator_name"\s*:\s*")[^"]+(")'), r'\1<REDACTED>\2'),
    (re.compile(r"(学校名\s*[:=]\s*)[^\r\n,]+"), r"\1<REDACTED>"),
    (re.compile(r"(操作員\s*[:=]\s*)[^\r\n,]+"), r"\1<REDACTED>"),
)


def scrub_text(text: str) -> str:
    """Remove high-risk local PII while keeping debug structure intact."""

    scrubbed = text
    for pattern, replacement in SCRUB_REPLACEMENTS:
        scrubbed = pattern.sub(replacement, scrubbed)
    return scrubbed


def scrub_json_value(value: Any) -> Any:
    """Recursively scrub JSON-like values before showing them in UI/CLI output."""

    if isinstance(value, str):
        return scrub_text(value)
    if isinstance(value, list):
        return [scrub_json_value(item) for item in value]
    if isinstance(value, dict):
        scrubbed: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if key_text in {"school_name", "operator_name", "学校名", "操作員"} and isinstance(item, str):
                scrubbed[key_text] = "<REDACTED>"
            else:
                scrubbed[key_text] = scrub_json_value(item)
        return scrubbed
    return value


def _now_utc(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(UTC)
    if now.tzinfo is None:
        return now.replace(tzinfo=UTC)
    return now.astimezone(UTC)


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _tail_text(path: Path, *, max_lines: int = 200) -> str | None:
    text = _read_text(path)
    if text is None:
        return None
    return "\n".join(text.splitlines()[-max_lines:]) + "\n"


def _latest_file(root: Path, pattern: str) -> Path | None:
    matches = [path for path in root.glob(pattern) if path.is_file()]
    if not matches:
        return None
    return max(matches, key=lambda path: (path.stat().st_mtime, path.as_posix()))


def _write_text_member(
    zf: zipfile.ZipFile,
    *,
    arcname: str,
    text: str,
    included: list[dict[str, Any]],
) -> None:
    payload = scrub_text(text)
    zf.writestr(arcname, payload)
    included.append({"path": arcname, "size": len(payload.encode("utf-8"))})


def _write_file_member(
    zf: zipfile.ZipFile,
    *,
    root: Path,
    rel_path: str,
    included: list[dict[str, Any]],
) -> None:
    path = root / rel_path
    text = _read_text(path)
    if text is None:
        return
    _write_text_member(zf, arcname=rel_path, text=text, included=included)


def _lock_state(root: Path, now: datetime) -> dict[str, Any]:
    lock_path = root / "data" / ".lock"
    if not lock_path.exists():
        return {"exists": False, "path": "data/.lock"}
    mtime = datetime.fromtimestamp(lock_path.stat().st_mtime, tz=UTC)
    return {
        "exists": True,
        "path": "data/.lock",
        "mtime_utc": mtime.isoformat(timespec="seconds"),
        "age_seconds": int((now - mtime).total_seconds()),
        "size": lock_path.stat().st_size,
    }


def _manifest(
    *,
    root: Path,
    archive_path: Path,
    signals: list[BugSignal],
    operator_note: str,
    included: list[dict[str, Any]],
    now: datetime,
) -> dict[str, Any]:
    total, used, free = shutil.disk_usage(root)
    return {
        "generated_at_utc": now.isoformat(timespec="seconds"),
        "app_root": scrub_text(str(root)),
        "archive": scrub_text(str(archive_path)),
        "signals": [asdict(signal) for signal in signals],
        "operator_note": scrub_text(operator_note),
        "platform": platform.platform(),
        "python_version": sys.version.split()[0],
        "disk": {
            "total": total,
            "used": used,
            "free": free,
        },
        "included": included,
        "excluded": {
            "database": "data/eidp.sqlite3 and sidecars are never bundled",
            "pdfs": "data/pdfs is never bundled",
            "excel": "data/output/*.xlsx is never bundled",
            "upload": "local-only bundle; no network upload performed",
        },
    }


def build_bug_report_bundle(
    app_root: Path,
    *,
    signals: list[BugSignal] | None = None,
    operator_note: str = "",
    out_path: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Create a sanitized local ZIP for developer triage."""

    root = app_root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"app root does not exist: {root}")

    generated_at = _now_utc(now)
    resolved_signals = signals if signals is not None else scan_bug_signals(root, now=generated_at)
    out_dir = root / "data" / "output" / "bug_reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = generated_at.strftime("%Y%m%d-%H%M%S")
    archive_path = (out_path or out_dir / f"bug-report-{stamp}.zip").resolve()
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    included: list[dict[str, Any]] = []
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        _write_file_member(zf, root=root, rel_path="BUILD_INFO.json", included=included)
        _write_file_member(zf, root=root, rel_path="data/output/last_run.json", included=included)

        latest_run_log = _latest_file(root / "logs", "run-*.log")
        if latest_run_log is not None:
            tail = _tail_text(latest_run_log)
            if tail is not None:
                _write_text_member(zf, arcname="logs/run-latest-tail.txt", text=tail, included=included)

        latest_diagnostics = _latest_file(root / "logs", "diagnostics-*.txt")
        if latest_diagnostics is not None:
            text = _tail_text(latest_diagnostics, max_lines=300)
            if text is not None:
                _write_text_member(zf, arcname="logs/diagnostics-latest-tail.txt", text=text, included=included)

        lock_state = _lock_state(root, generated_at)
        _write_text_member(
            zf,
            arcname="lock-state.json",
            text=json.dumps(lock_state, ensure_ascii=False, indent=2) + "\n",
            included=included,
        )
        _write_text_member(
            zf,
            arcname="bug-signals.json",
            text=json.dumps([signal.to_dict() for signal in resolved_signals], ensure_ascii=False, indent=2) + "\n",
            included=included,
        )
        manifest = _manifest(
            root=root,
            archive_path=archive_path,
            signals=resolved_signals,
            operator_note=operator_note,
            included=included,
            now=generated_at,
        )
        _write_text_member(
            zf,
            arcname="manifest.json",
            text=json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            included=included,
        )

    return {
        "ok": True,
        "archive": str(archive_path),
        "signal_count": len(resolved_signals),
        "signals": scrub_json_value([signal.to_dict() for signal in resolved_signals]),
        "included_count": len(included),
    }

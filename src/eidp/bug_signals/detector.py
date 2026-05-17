"""Local bug-signal detection for the operator UI.

Phase 1 is intentionally local-only: it detects operational signals and feeds a
sanitized ZIP bundle. It does not upload anything or require network access.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

SIGNAL_ID_VOLATILE_DETAIL_KEYS = frozenset({"age_seconds"})


@dataclass(frozen=True)
class BugSignal:
    signal_id: str
    severity: str
    kind: str
    title: str
    evidence_path: str | None
    detected_at: str
    detail: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now_utc(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(UTC)
    if now.tzinfo is None:
        return now.replace(tzinfo=UTC)
    return now.astimezone(UTC)


def _json_object(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _latest_file(root: Path, pattern: str) -> Path | None:
    matches = [path for path in root.glob(pattern) if path.is_file()]
    if not matches:
        return None
    return max(matches, key=lambda path: (path.stat().st_mtime, path.as_posix()))


def _tail_text(path: Path, *, max_lines: int = 200) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return "\n".join(text.splitlines()[-max_lines:])


def _signal_id(kind: str, evidence_path: str | None, detail: dict[str, str]) -> str:
    stable_detail = {
        key: value
        for key, value in detail.items()
        if key not in SIGNAL_ID_VOLATILE_DETAIL_KEYS
    }
    stable = {
        "kind": kind,
        "evidence_path": evidence_path,
        "detail": stable_detail,
    }
    encoded = json.dumps(stable, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _signal(
    *,
    kind: str,
    title: str,
    evidence_path: Path | None,
    detected_at: datetime,
    detail: dict[str, str],
    severity: str = "P0",
) -> BugSignal:
    evidence = evidence_path.as_posix() if evidence_path is not None else None
    return BugSignal(
        signal_id=_signal_id(kind, evidence, detail),
        severity=severity,
        kind=kind,
        title=title,
        evidence_path=evidence,
        detected_at=detected_at.isoformat(timespec="seconds"),
        detail=detail,
    )


def _sqlite_integrity_signal(app_root: Path, detected_at: datetime) -> BugSignal | None:
    db_path = app_root / "data" / "eidp.sqlite3"
    if not db_path.is_file():
        return None
    try:
        conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro&immutable=1", uri=True)
        try:
            row = conn.execute("PRAGMA integrity_check").fetchone()
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return _signal(
            kind="sqlite_integrity_error",
            title="SQLite integrity check could not run",
            evidence_path=db_path,
            detected_at=detected_at,
            detail={"error": f"{type(exc).__name__}: {exc}"},
        )
    status = str(row[0] if row else "")
    if status.lower() == "ok":
        return None
    return _signal(
        kind="sqlite_integrity_failed",
        title="SQLite integrity check failed",
        evidence_path=db_path,
        detected_at=detected_at,
        detail={"integrity_check": status[:500]},
    )


def scan_bug_signals(
    app_root: Path,
    *,
    now: datetime | None = None,
    lock_stale_after: timedelta = timedelta(hours=2),
    weekly_timeout_after: timedelta = timedelta(hours=1),
    check_sqlite: bool = True,
) -> list[BugSignal]:
    """Return local P0/P1 signals visible from files under ``app_root``."""

    root = app_root.resolve()
    detected_at = _now_utc(now)
    signals: list[BugSignal] = []

    last_run_path = root / "data" / "output" / "last_run.json"
    last_run = _json_object(last_run_path)
    if last_run is not None:
        status = str(last_run.get("status") or "")
        error = str(last_run.get("error") or "")
        if status in {"error", "failed"} or (error and status != "success"):
            signals.append(
                _signal(
                    kind="weekly_run_error",
                    title="Weekly run ended with an error",
                    evidence_path=last_run_path,
                    detected_at=detected_at,
                    detail={"status": status or "unknown", "error": error[:500]},
                )
            )

    lock_path = root / "data" / ".lock"
    if lock_path.exists():
        mtime = datetime.fromtimestamp(lock_path.stat().st_mtime, tz=UTC)
        age_seconds = int((detected_at - mtime).total_seconds())
        if age_seconds >= int(lock_stale_after.total_seconds()):
            signals.append(
                _signal(
                    kind="stale_lock",
                    title="Application lock file appears stale",
                    evidence_path=lock_path,
                    detected_at=detected_at,
                    detail={
                        "lock_mtime_utc": mtime.isoformat(timespec="seconds"),
                        "age_seconds": str(age_seconds),
                    },
                )
            )

    latest_run_log = _latest_file(root / "logs", "run-*.log")
    if latest_run_log is not None:
        tail = _tail_text(latest_run_log)
        log_mtime = datetime.fromtimestamp(latest_run_log.stat().st_mtime, tz=UTC)
        log_age_seconds = int((detected_at - log_mtime).total_seconds())
        last_run_is_fresh = False
        if last_run_path.is_file():
            last_run_mtime = datetime.fromtimestamp(last_run_path.stat().st_mtime, tz=UTC)
            last_run_is_fresh = last_run_mtime >= log_mtime
        if (
            "[weekly_run] start" in tail
            and "[weekly_run] end" not in tail
            and log_age_seconds >= int(weekly_timeout_after.total_seconds())
            and not last_run_is_fresh
        ):
            signals.append(
                _signal(
                    kind="weekly_run_timeout_no_last_run",
                    title="Weekly run appears timed out without a fresh last_run.json",
                    evidence_path=latest_run_log,
                    detected_at=detected_at,
                    detail={
                        "log_mtime_utc": log_mtime.isoformat(timespec="seconds"),
                        "age_seconds": str(log_age_seconds),
                    },
                    severity="P1",
                )
            )
        if "Traceback (most recent call last)" in tail or "ERROR:" in tail:
            marker = "Traceback" if "Traceback (most recent call last)" in tail else "ERROR:"
            signals.append(
                _signal(
                    kind="weekly_run_log_error",
                    title="Latest weekly run log contains an error marker",
                    evidence_path=latest_run_log,
                    detected_at=detected_at,
                    detail={"marker": marker},
                )
            )

    if check_sqlite:
        sqlite_signal = _sqlite_integrity_signal(root, detected_at)
        if sqlite_signal is not None:
            signals.append(sqlite_signal)

    unique: dict[str, BugSignal] = {}
    for signal in signals:
        unique[signal.signal_id] = signal
    return list(unique.values())


def scan_p0_bug_signals(
    app_root: Path,
    *,
    now: datetime | None = None,
    lock_stale_after: timedelta = timedelta(hours=2),
    weekly_timeout_after: timedelta = timedelta(hours=1),
    check_sqlite: bool = True,
) -> list[BugSignal]:
    """Compatibility wrapper for callers using the Phase 1 P0-era name."""

    return scan_bug_signals(
        app_root,
        now=now,
        lock_stale_after=lock_stale_after,
        weekly_timeout_after=weekly_timeout_after,
        check_sqlite=check_sqlite,
    )

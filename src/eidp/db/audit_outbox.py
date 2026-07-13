"""Audit outbox — after-commit JSONL export of manual_action_log (Sprint 8.2.c).

DB is authoritative; the JSONL file at ``data/audit/manual-actions.jsonl`` is
a derived stream useful for human grep / external monitoring / disaster
recovery reading. Critically:

  * The export runs *after* the caller commits the audit row. Failures here
    must never roll back the user's action.
  * Each row carries an ``action_id`` (UUID) assigned at insert time. A flush
    is dedup-tolerant: it scans both the DB and the JSONL file by action_id
    so a partial previous flush + a fresh flush yields exactly one JSONL line
    per action_id.
  * On a hard write failure the ``jsonl_export_error`` column captures a
    short reason; the row stays exportable next time ``eidp audit-flush``
    runs.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from eidp.db.models import ManualActionLog
from eidp.identity import IdentitySource

DEFAULT_OUTBOX_PATH = Path("data/audit/manual-actions.jsonl")
OUTBOX_ARCHIVE_GLOB = "manual-actions-*.jsonl"
log = structlog.get_logger(__name__)


def _candidate_outbox_paths(jsonl_path: Path) -> list[Path]:
    """Return active and archived JSONL outbox files to use for dedup."""

    paths = [jsonl_path]
    if jsonl_path.parent.exists():
        paths.extend(
            sorted(
                p
                for p in jsonl_path.parent.iterdir()
                if not p.is_symlink() and p.is_file() and _is_matching_outbox_archive(jsonl_path, p)
            )
        )
    return list(dict.fromkeys(paths))


def _is_matching_outbox_archive(jsonl_path: Path, archive_path: Path) -> bool:
    """Return true for archives rotated from the same outbox filename stem."""

    return archive_path.suffix == ".jsonl" and archive_path.name.startswith(f"{jsonl_path.stem}-")


def _read_existing_action_ids(jsonl_path: Path) -> set[str]:
    """Collect action_ids already written to active or archived JSONL files."""
    seen: set[str] = set()
    for path in _candidate_outbox_paths(jsonl_path):
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                aid = rec.get("action_id")
                if aid:
                    seen.add(aid)
    return seen


def _row_to_dict(row: ManualActionLog) -> dict[str, object]:
    return {
        "action_id": row.action_id,
        "timestamp": row.timestamp.isoformat() if row.timestamp else None,
        "actor": row.actor,
        "identity_source": (
            row.identity_source
            if row.identity_source is not None
            else IdentitySource.LEGACY_UNSPECIFIED.value
        ),
        "action_type": row.action_type,
        "target_table": row.target_table,
        "target_id": row.target_id,
        "document_id": row.document_id,
        "old_value": json.loads(row.old_value) if row.old_value else None,
        "new_value": json.loads(row.new_value) if row.new_value else None,
        "reason": row.reason,
    }


def flush_audit_outbox(
    session: Session,
    *,
    jsonl_path: Path | None = None,
) -> dict[str, int]:
    """Export pending manual_action_log rows to the JSONL outbox.

    Pending = ``jsonl_exported_at IS NULL``. Idempotent: if a row's
    ``action_id`` already appears in the file (e.g. a previous flush wrote
    the line but crashed before updating the column), the line is NOT
    duplicated; the column is just stamped.

    Returns a stats dict with ``exported``, ``already_present``, and
    ``failed`` counts. The session is committed at the end.
    """
    target_path = jsonl_path or DEFAULT_OUTBOX_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)

    existing_ids = _read_existing_action_ids(target_path)
    pending = session.execute(
        select(ManualActionLog).where(ManualActionLog.jsonl_exported_at.is_(None))
    ).scalars().all()

    stats = {"exported": 0, "already_present": 0, "failed": 0}
    now = datetime.now(UTC)

    with target_path.open("a", encoding="utf-8") as fh:
        for row in pending:
            try:
                if row.action_id in existing_ids:
                    stats["already_present"] += 1
                else:
                    fh.write(json.dumps(_row_to_dict(row), ensure_ascii=False) + "\n")
                    fh.flush()
                    os.fsync(fh.fileno())
                    existing_ids.add(row.action_id)
                    stats["exported"] += 1
                row.jsonl_exported_at = now
                row.jsonl_export_error = None
            except Exception as exc:  # pragma: no cover — disk full / permission
                log.exception(
                    "audit_outbox_export_failed",
                    action_id=row.action_id,
                    jsonl_path=str(target_path),
                    error_type=type(exc).__name__,
                )
                row.jsonl_export_error = str(exc)[:500]
                stats["failed"] += 1

    session.commit()
    return stats

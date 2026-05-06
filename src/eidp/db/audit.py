"""Audit logging — DB-authoritative manual_action_log writer (Sprint 8.2.c).

The DB row is the source of truth. JSONL outbox export is handled by
``eidp.db.audit_outbox`` after the caller commits. ``log_manual_action``
inserts the row but does NOT commit; the caller owns the transaction
boundary so override + audit can sit in a single transaction.

Each row gets a stable ``action_id`` (UUID4) so the outbox can dedup against
the DB even if a flush re-runs.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy.orm import Session

from eidp.db.models import ManualActionLog


def _to_json_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def log_manual_action(
    session: Session,
    *,
    action_type: str,
    target_table: str,
    target_id: int | None = None,
    document_id: int | None = None,
    old_value: Any = None,
    new_value: Any = None,
    reason: str | None = None,
    actor: str = "operator",
) -> ManualActionLog:
    """Insert a manual_action_log row (no commit).

    Parameters
    ----------
    action_type :
        e.g. ``"fiscal_year_override"``, ``"manual_entry"``, ``"dept_change"``.
        Historical DBs may still contain ``"r8_override"`` rows.
    target_table :
        Table whose row was changed: ``"document"``, ``"department_yearly"``,
        ``"support_recipient"``, or ``"school_year_status"``.
    target_id :
        Primary key of the changed row. May be None when the operation
        spans multiple rows; the document_id then identifies the scope.
    old_value, new_value :
        Anything JSON-serializable. Stored as JSON text. ``None`` becomes a
        NULL column rather than the JSON string ``"null"`` so callers can
        easily distinguish "no prior value" from "prior value was JSON null".
    reason :
        Free-text rationale entered by the operator.
    actor :
        Defaults to ``"operator"`` for the single-business-user PC deployment.
    """
    row = ManualActionLog(
        action_id=str(uuid.uuid4()),
        actor=actor,
        action_type=action_type,
        target_table=target_table,
        target_id=target_id,
        document_id=document_id,
        old_value=_to_json_or_none(old_value),
        new_value=_to_json_or_none(new_value),
        reason=reason,
    )
    session.add(row)
    session.flush()  # populate row.id and timestamp without committing
    return row

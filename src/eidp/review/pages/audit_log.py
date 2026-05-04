"""Streamlit page: 監査ログ (Sprint 8.4.c.4).

Operator-facing browser over ``manual_action_log`` plus the JSONL
outbox flush surface. Closes the 4-page UI commitment from v6.

Architecture
------------
Same shape as the other three UI pages. Pure helpers under unit test:

  * ``list_recent_actions(session, *, limit, action_type, target_table)``
  * ``outbox_pending_count(session)``
  * ``flush_outbox_via_ui(session, jsonl_path)`` — wraps
    ``audit_outbox.flush_audit_outbox`` so the page never imports
    audit_outbox directly.

Read-mostly page. The flush button writes the JSONL outbox file but
does not modify business data; it sits outside the lock contract for
the same reason ``audit-flush`` CLI does (the only side effect is
appending to the outbox file + stamping ``jsonl_exported_at``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from sqlalchemy import func
from sqlalchemy.orm import Session

from eidp.db.audit_outbox import flush_audit_outbox
from eidp.db.locking import probe_lock
from eidp.db.models import ManualActionLog


@dataclass(frozen=True)
class ActionRow:
    """UI projection of one manual_action_log row."""

    id: int
    action_id: str
    timestamp: str | None
    actor: str
    action_type: str
    target_table: str
    target_id: int | None
    document_id: int | None
    reason: str | None
    old_value: dict | list | str | int | float | bool | None
    new_value: dict | list | str | int | float | bool | None
    jsonl_exported_at: str | None


# Distinct action_types we surface in the filter dropdown. Mirrors the
# vocabulary other modules use when calling log_manual_action.
ACTION_TYPES: tuple[str, ...] = (
    "manual_entry",
    "fiscal_year_override",
    "r8_override",
    "dept_change",
)

# Same idea for target_table.
TARGET_TABLES: tuple[str, ...] = (
    "document",
    "department",
    "department_yearly",
    "department_change",
    "support_recipient",
    "school_year_status",
)


def _maybe_parse_json(value: str | None):
    if value is None:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def list_recent_actions(
    session: Session,
    *,
    limit: int = 200,
    action_type: str | None = None,
    target_table: str | None = None,
    actions: Iterable[ManualActionLog] | None = None,
) -> list[ActionRow]:
    """Return manual_action_log rows ordered newest-first.

    ``actions`` is an injection seam used by tests that want to stub
    the query result. Production callers leave it None and let us
    issue the query.
    """
    if actions is None:
        q = session.query(ManualActionLog)
        if action_type:
            q = q.filter(ManualActionLog.action_type == action_type)
        if target_table:
            q = q.filter(ManualActionLog.target_table == target_table)
        actions = (
            q.order_by(ManualActionLog.id.desc())
            .limit(limit)
            .all()
        )

    out: list[ActionRow] = []
    for a in actions:
        out.append(ActionRow(
            id=a.id,
            action_id=a.action_id,
            timestamp=a.timestamp.isoformat() if a.timestamp else None,
            actor=a.actor,
            action_type=a.action_type,
            target_table=a.target_table,
            target_id=a.target_id,
            document_id=a.document_id,
            reason=a.reason,
            old_value=_maybe_parse_json(a.old_value),
            new_value=_maybe_parse_json(a.new_value),
            jsonl_exported_at=(
                a.jsonl_exported_at.isoformat() if a.jsonl_exported_at else None
            ),
        ))
    return out


def outbox_pending_count(session: Session) -> int:
    """Count of ``manual_action_log`` rows still pending JSONL export."""
    return (
        session.query(func.count(ManualActionLog.id))
        .filter(ManualActionLog.jsonl_exported_at.is_(None))
        .scalar()
        or 0
    )


def flush_outbox_via_ui(session: Session, jsonl_path: Path) -> dict[str, int]:
    """Page-side wrapper around ``audit_outbox.flush_audit_outbox`` so
    tests can monkeypatch this single seam to assert the page calls
    it (and not, say, write JSONL directly)."""
    return flush_audit_outbox(session, jsonl_path=jsonl_path)


# ---------------------------------------------------------------------------
# Streamlit render
# ---------------------------------------------------------------------------


def render(  # pragma: no cover - thin streamlit shell
    session: Session,
    *,
    lock_path: Path,
    jsonl_path: Path,
) -> None:
    """Top-level Streamlit render for the 監査ログ page."""
    import streamlit as st

    st.subheader("監査ログ")
    status = probe_lock(lock_path)
    if status.held:
        st.info(
            f"週次処理中 (owner={status.owner})。"
            " このページは読み取り中心です。"
        )

    pending = outbox_pending_count(session)
    cols = st.columns([2, 1])
    cols[0].metric("JSONL outbox 未送信", pending)
    if cols[1].button("Outbox を flush", type="primary"):
        with st.spinner("flushing..."):
            stats = flush_outbox_via_ui(session, jsonl_path)
        st.success(
            f"exported={stats['exported']} "
            f"already_present={stats['already_present']} "
            f"failed={stats['failed']}"
        )

    st.markdown("---")
    cols = st.columns(2)
    action_type = cols[0].selectbox(
        "action_type で絞り込み",
        options=["", *ACTION_TYPES],
        index=0,
    )
    target_table = cols[1].selectbox(
        "target_table で絞り込み",
        options=["", *TARGET_TABLES],
        index=0,
    )

    rows = list_recent_actions(
        session,
        action_type=action_type or None,
        target_table=target_table or None,
        limit=200,
    )
    if not rows:
        st.caption("(該当する監査ログはありません)")
        return

    st.caption(f"最近 {len(rows)} 件")
    for r in rows:
        with st.expander(
            f"#{r.id} [{r.action_type}] {r.target_table}#{r.target_id} "
            f"by {r.actor} @ {r.timestamp}"
        ):
            st.write(f"action_id: `{r.action_id}`")
            if r.document_id is not None:
                st.write(f"document_id: {r.document_id}")
            if r.reason:
                st.write(f"reason: {r.reason}")
            if r.old_value is not None:
                st.write("old_value:")
                st.json(r.old_value)
            if r.new_value is not None:
                st.write("new_value:")
                st.json(r.new_value)
            if r.jsonl_exported_at:
                st.caption(f"JSONL exported at {r.jsonl_exported_at}")
            else:
                st.caption("JSONL outbox: 未送信")

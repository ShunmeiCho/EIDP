"""Streamlit page: 監査ログ (Sprint 8.4.c.4).

Operator-facing browser over ``manual_action_log`` plus the JSONL
outbox flush surface. Closes the 4-page UI commitment from v6.

Architecture
------------
Same shape as the other three UI pages. Pure helpers under unit test:

  * ``list_recent_actions(session, *, limit, action_type, target_table)``
  * ``outbox_pending_count(session)``
  * ``flush_outbox_with_lock(session, jsonl_path, lock_path)`` — locks
    the shared write lane before exporting the JSONL outbox.

Read-mostly page. The flush button still writes JSONL and stamps
``jsonl_exported_at``, so the UI routes it through the same shared lock
as other operator writes. If the weekly runner is active, the button is
disabled and the helper also returns ``lock_busy`` defensively.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from sqlalchemy import func
from sqlalchemy.orm import Session

from eidp.db.audit_outbox import flush_audit_outbox
from eidp.db.locking import LockBusyError, acquire_lock, probe_lock
from eidp.db.models import Document, ManualActionLog

JSONValue = dict[str, object] | list[object] | str | int | float | bool | None


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
    old_value: JSONValue
    new_value: JSONValue
    jsonl_exported_at: str | None


@dataclass(frozen=True)
class FlushOutcome:
    """Return shape for UI-triggered JSONL outbox flushes."""

    ok: bool
    lock_busy: bool = False
    lock_owner: str | None = None
    lock_started_at: str | None = None
    stats: dict[str, int] | None = None
    error: str | None = None


@dataclass(frozen=True)
class QueueDepth:
    """Sprint 8.6.d.4 — operator dashboard counts.

    Surfaces the queue depth across the buckets that drive the
    PDF確認・手入力 workflow so the audit page can show "how much work
    is waiting" without the operator having to switch tabs.

    ``review_pending`` and ``ocr_pending`` are the high-priority
    buckets. ``parse_failed`` and ``school_mismatch`` are recoverable
    but stuck without operator action. ``ingested`` and ``support_only``
    are healthy outcomes. ``other`` is a catch-all for anything else
    so a future status drift doesn't silently disappear from totals.
    """

    review_pending: int
    ocr_pending: int
    parse_failed: int
    school_mismatch: int
    ingested: int
    support_only: int
    other: int
    total: int


# Distinct action_types we surface in the filter dropdown. Mirrors the
# vocabulary other modules use when calling log_manual_action.
ACTION_TYPES: tuple[str, ...] = (
    "manual_entry",
    "fiscal_year_override",
    "r8_override",  # legacy Sprint 8.x rows; new writes use fiscal_year_override.
    "dept_change",
    "operator_settings_saved",
    "excel_preview_generated",
    "excel_export_generated",
    "school_year_tasks_rebuilt",
    "operator_url_submitted",
    "operator_url_bulk_imported",
    "url_auto_discovery",
    "url_candidate_proposed",
    "url_candidate_manual_required",
    "url_candidate_approved",
    "url_candidate_rejected",
    "prefecture_remark_approved",
    "prefecture_remark_rejected",
    "school_code_approved",
    "school_code_corrected",
    "school_code_rejected",
    "school_code_skipped",
    "school_alias_approved",
    "dept_alias_approved",
    "dept_change_void",
)

# Same idea for target_table.
TARGET_TABLES: tuple[str, ...] = (
    "document",
    "department",
    "department_yearly",
    "department_change",
    "support_recipient",
    "school_year_status",
    "school_fiscal_year_status",
    "school",
    "school_alias",
    "review_item",
    "school_site",
    "excel_export",
    "operator_settings",
)


def _maybe_parse_json(value: str | None) -> JSONValue:
    if value is None:
        return None
    try:
        return cast(JSONValue, json.loads(value))
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


_KNOWN_QUEUE_STATUSES = (
    "review_pending",
    "ocr_pending",
    "parse_failed",
    "school_mismatch",
    "ingested",
    "support_only",
)


def queue_depth(session: Session) -> QueueDepth:
    """Group every Document by ``ingest_status`` and return a
    structured count. Used by the audit page header to show queue
    depth at a glance.

    NULL ``ingest_status`` rows count under ``other`` so a partially
    initialized DB doesn't silently drop documents from the total.
    """
    rows = (
        session.query(Document.ingest_status, func.count(Document.id))
        .group_by(Document.ingest_status)
        .all()
    )
    counts: dict[str, int] = {}
    for status, count in rows:
        key = status if status else "_null"
        counts[key] = int(count or 0)

    review = counts.get("review_pending", 0)
    ocr = counts.get("ocr_pending", 0)
    parse_failed = counts.get("parse_failed", 0)
    mismatch = counts.get("school_mismatch", 0)
    ingested = counts.get("ingested", 0)
    support_only = counts.get("support_only", 0)
    known_total = review + ocr + parse_failed + mismatch + ingested + support_only
    grand_total = sum(counts.values())
    other = grand_total - known_total

    return QueueDepth(
        review_pending=review,
        ocr_pending=ocr,
        parse_failed=parse_failed,
        school_mismatch=mismatch,
        ingested=ingested,
        support_only=support_only,
        other=other,
        total=grand_total,
    )


def flush_outbox_with_lock(session: Session, *, jsonl_path: Path, lock_path: Path) -> FlushOutcome:
    """Flush audit JSONL outbox only after acquiring the shared UI lock."""
    try:
        with acquire_lock(lock_path, owner="ui_audit_flush"):
            try:
                stats = flush_outbox_via_ui(session, jsonl_path)
            except Exception as exc:
                session.rollback()
                return FlushOutcome(ok=False, error=str(exc))
            return FlushOutcome(ok=True, stats=stats)
    except LockBusyError:
        status = probe_lock(lock_path)
        return FlushOutcome(
            ok=False,
            lock_busy=True,
            lock_owner=status.owner,
            lock_started_at=status.started_at,
        )


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
            " このページは読み取り専用です。"
        )

    # Sprint 8.6.d.4 — queue depth dashboard. Operator sees the
    # actionable buckets (review_pending / ocr_pending / parse_failed /
    # school_mismatch) before scrolling into the audit log itself.
    depth = queue_depth(session)
    st.markdown("**待機キュー**")
    qcols = st.columns(4)
    qcols[0].metric("要レビュー", depth.review_pending)
    qcols[1].metric("OCR 待ち", depth.ocr_pending)
    qcols[2].metric("解析失敗", depth.parse_failed)
    qcols[3].metric("学校不一致", depth.school_mismatch)
    icols = st.columns(3)
    icols[0].metric("採録済み", depth.ingested)
    icols[1].metric("対象比率のみ", depth.support_only)
    icols[2].metric("その他", depth.other)

    pending = outbox_pending_count(session)
    cols = st.columns([2, 1])
    cols[0].metric("JSONL outbox 未送信", pending)
    if cols[1].button("Outbox を flush", type="primary", disabled=status.held):
        with st.spinner("flushing..."):
            outcome = flush_outbox_with_lock(session, jsonl_path=jsonl_path, lock_path=lock_path)
        if outcome.lock_busy:
            st.warning(
                f"週次処理中、Outbox flush は一時停止しています "
                f"(owner={outcome.lock_owner}, started_at={outcome.lock_started_at})"
            )
            return
        if not outcome.ok or outcome.stats is None:
            st.error(f"Outbox flush に失敗しました: {outcome.error}")
            return
        stats = outcome.stats
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

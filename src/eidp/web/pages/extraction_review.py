"""Extraction review page for Linux/Web MVP."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import streamlit as st
from sqlalchemy.orm import Session, sessionmaker

from eidp.config import settings
from eidp.db.audit_outbox import flush_audit_outbox
from eidp.db.locking import LockBusyError
from eidp.identity import ResolvedIdentity
from eidp.pipeline.extraction_review import (
    ReviewStatus,
    ReviewValidationError,
    accept_review_record,
    correct_review_record,
    ensure_review_records,
    exclude_review_record,
    load_review_records,
    mark_review_needs_review,
)
from eidp.pipeline.review_decision import overlay_review_decisions
from eidp.web.components.evidence_panel import render_evidence_panel
from eidp.web.components.extracted_rows_table import render_extracted_review_table
from eidp.web.locking import acquire_web_write_lock, web_write_lock_path


def render_extraction_review_page(
    *,
    identity: ResolvedIdentity,
    session_factory: sessionmaker[Session],
    intake_root: Path | None = None,
) -> None:
    resolved_root = intake_root or Path(settings.data_dir) / "web-intake"
    st.title("EIDP Extraction Review")
    st.caption("Review extracted rows and evidence. This page does not write final Excel output.")

    try:
        with acquire_web_write_lock(resolved_root, owner="web_review_sync"):
            records = ensure_review_records(resolved_root)
    except LockBusyError as exc:
        st.warning(str(exc))
        records = load_review_records(resolved_root)
    with session_factory() as session:
        records = overlay_review_decisions(session, records)
    extracted_count = sum(1 for record in records if record.metric)
    exception_count = sum(1 for record in records if not record.metric)
    reviewed_count = sum(
        1
        for record in records
        if record.review_status in {ReviewStatus.ACCEPTED, ReviewStatus.CORRECTED, ReviewStatus.EXCLUDED}
    )
    col_extracted, col_exception, col_reviewed = st.columns(3)
    col_extracted.metric("Extracted rows", extracted_count)
    col_exception.metric("Manual/OCR tasks", exception_count)
    col_reviewed.metric("Reviewed", reviewed_count)

    render_extracted_review_table(records)
    if not records:
        return

    labels = [_review_label(record) for record in records]
    selected_label = str(st.selectbox("Review row", labels))
    selected = records[labels.index(selected_label)]
    render_evidence_panel(selected)

    review_note = st.text_area("review_note")
    corrected_value = st.number_input("corrected_value", value=int(selected.extracted_value or 0), step=1)
    action_cols = st.columns(4)
    if action_cols[0].button("Accept", type="primary"):
        _run_action(
            resolved_root,
            session_factory=session_factory,
            action=lambda session: accept_review_record(
                session,
                intake_root=resolved_root,
                review_id=selected.review_id,
                identity=identity,
                review_note=review_note,
            ),
        )
    if action_cols[1].button("Correct"):
        _run_action(
            resolved_root,
            session_factory=session_factory,
            action=lambda session: correct_review_record(
                session,
                intake_root=resolved_root,
                review_id=selected.review_id,
                corrected_value=int(corrected_value),
                identity=identity,
                review_note=review_note,
            ),
        )
    if action_cols[2].button("Needs review"):
        _run_action(
            resolved_root,
            session_factory=session_factory,
            action=lambda session: mark_review_needs_review(
                session,
                intake_root=resolved_root,
                review_id=selected.review_id,
                identity=identity,
                review_note=review_note,
            ),
        )
    if action_cols[3].button("Exclude"):
        _run_action(
            resolved_root,
            session_factory=session_factory,
            action=lambda session: exclude_review_record(
                session,
                intake_root=resolved_root,
                review_id=selected.review_id,
                identity=identity,
                review_note=review_note,
            ),
        )


def _review_label(record: object) -> str:
    department = getattr(record, "department_name") or "manual/OCR"
    metric = getattr(record, "metric") or "task"
    return f"{getattr(record, 'school_name')} / {department} / {metric}"


def _run_action(
    intake_root: Path,
    *,
    session_factory: sessionmaker[Session],
    action: Callable[[Session], object],
) -> None:
    decision_committed = False
    outbox_stats: dict[str, int] | None = None
    try:
        with acquire_web_write_lock(intake_root, owner="web_extraction_review"):
            with session_factory() as session:
                try:
                    action(session)
                    session.commit()
                    decision_committed = True
                except Exception:
                    session.rollback()
                    raise
                outbox_stats = flush_audit_outbox(
                    session,
                    jsonl_path=web_write_lock_path(intake_root).parent / "audit" / "manual-actions.jsonl",
                )
    except (KeyError, LockBusyError, ReviewValidationError) as exc:
        st.error(str(exc))
        return
    except Exception:
        if decision_committed:
            st.warning("Review saved, but audit JSONL projection is pending. The database decision is preserved.")
        else:
            st.error("Review could not be saved. No decision was recorded.")
        return
    assert outbox_stats is not None
    if outbox_stats["failed"]:
        st.warning("Review saved, but audit JSONL export failed. The database decision is preserved for retry.")
        return
    st.success("Review saved.")
    st.rerun()

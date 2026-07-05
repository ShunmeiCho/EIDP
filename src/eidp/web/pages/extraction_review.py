"""Extraction review page for Linux/Web MVP."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from eidp.config import settings
from eidp.pipeline.extraction_review import (
    ReviewStatus,
    ReviewValidationError,
    accept_review_record,
    correct_review_record,
    ensure_review_records,
    exclude_review_record,
    mark_review_needs_review,
    review_report_csv,
)
from eidp.web.components.evidence_panel import render_evidence_panel
from eidp.web.components.extracted_rows_table import render_extracted_review_table


def render_extraction_review_page(*, intake_root: Path | None = None) -> None:
    resolved_root = intake_root or Path(settings.data_dir) / "web-intake"
    st.title("EIDP Extraction Review")
    st.caption("Review extracted rows and evidence. This page does not write final Excel output.")

    records = ensure_review_records(resolved_root)
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

    reviewed_by = st.text_input("reviewed_by")
    review_note = st.text_area("review_note")
    corrected_value = st.number_input("corrected_value", value=int(selected.extracted_value or 0), step=1)
    action_cols = st.columns(4)
    if action_cols[0].button("Accept", type="primary"):
        _run_action(
            lambda: accept_review_record(
                intake_root=resolved_root,
                review_id=selected.review_id,
                reviewed_by=reviewed_by,
                review_note=review_note,
            )
        )
    if action_cols[1].button("Correct"):
        _run_action(
            lambda: correct_review_record(
                intake_root=resolved_root,
                review_id=selected.review_id,
                corrected_value=int(corrected_value),
                reviewed_by=reviewed_by,
                review_note=review_note,
            )
        )
    if action_cols[2].button("Needs review"):
        _run_action(
            lambda: mark_review_needs_review(
                intake_root=resolved_root,
                review_id=selected.review_id,
                reviewed_by=reviewed_by,
                review_note=review_note,
            )
        )
    if action_cols[3].button("Exclude"):
        _run_action(
            lambda: exclude_review_record(
                intake_root=resolved_root,
                review_id=selected.review_id,
                reviewed_by=reviewed_by,
                review_note=review_note,
            )
        )

    st.download_button(
        "Download review_report.csv",
        data=review_report_csv(resolved_root),
        file_name="review_report.csv",
        mime="text/csv",
    )


def _review_label(record: object) -> str:
    department = getattr(record, "department_name") or "manual/OCR"
    metric = getattr(record, "metric") or "task"
    return f"{getattr(record, 'school_name')} / {department} / {metric}"


def _run_action(action: object) -> None:
    try:
        if callable(action):
            action()
    except (KeyError, ReviewValidationError) as exc:
        st.error(str(exc))
        return
    st.success("Review saved.")
    st.rerun()

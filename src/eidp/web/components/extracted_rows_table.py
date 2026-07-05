"""Review table rows for extracted metrics."""

from __future__ import annotations

import streamlit as st

from eidp.pipeline.extraction_review import ExtractionReviewRecord, is_final_ready


def extracted_review_table_rows(records: list[ExtractionReviewRecord]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for record in records:
        rows.append(
            {
                "review_id": record.review_id,
                "task_type": record.task_type.value,
                "review_status": record.review_status.value,
                "school_name": record.school_name,
                "school_id": record.school_id or "",
                "fiscal_year": record.fiscal_year,
                "department_name": record.department_name or "",
                "metric": record.metric or "",
                "extracted_value": record.extracted_value if record.extracted_value is not None else "",
                "corrected_value": record.corrected_value if record.corrected_value is not None else "",
                "confidence": record.confidence,
                "source_pdf": record.source_pdf or "",
                "raw_label": record.raw_label or "",
                "raw_value": record.raw_value or "",
                "final_ready": is_final_ready(record),
            }
        )
    return rows


def render_extracted_review_table(records: list[ExtractionReviewRecord]) -> None:
    rows = extracted_review_table_rows(records)
    if not rows:
        st.info("No extracted rows or manual/OCR tasks are ready for review.")
        return
    st.dataframe(rows, hide_index=True, use_container_width=True)

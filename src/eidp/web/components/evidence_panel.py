"""Evidence display for one extracted value."""

from __future__ import annotations

import streamlit as st

from eidp.pipeline.extraction_review import ExtractionReviewRecord, ReviewTaskType


def render_evidence_panel(record: ExtractionReviewRecord) -> None:
    if record.task_type == ReviewTaskType.EXCEPTION_MANUAL_OCR:
        st.warning("画像PDF: OCR済みPDFをアップロード、または手入力してください。")
        st.write(
            {
                "source_pdf": record.source_pdf or "",
                "next_action": record.next_action.value if record.next_action is not None else "",
                "source_page_url": record.source_page_url,
            }
        )
        return

    st.write(
        {
            "source_pdf": record.source_pdf or "",
            "page_no": record.page_no,
            "table_index": record.table_index,
            "row_index": record.row_index,
            "col_index": record.col_index,
            "raw_label": record.raw_label or "",
            "raw_value": record.raw_value or "",
            "canonical_metric": record.canonical_metric or "",
        }
    )

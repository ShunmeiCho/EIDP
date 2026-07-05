"""Intake queue table rendering."""

from __future__ import annotations

import streamlit as st

from eidp.pipeline.pdf_intake import PdfIntakeRecord


def intake_table_rows(records: list[PdfIntakeRecord]) -> list[dict[str, object]]:
    return [
        {
            "created_at_utc": record.created_at_utc,
            "lane": record.lane.value,
            "school_name": record.school_name,
            "school_id": record.school_id or "",
            "fiscal_year": record.fiscal_year,
            "source_type": record.source_type.value,
            "pdf_kind": record.pdf_kind.value if record.pdf_kind is not None else "",
            "sha256": record.sha256 or "",
            "stored_path": record.stored_path or "",
            "source_page_url": record.source_page_url,
            "pdf_url": record.pdf_url or "",
            "original_filename": record.original_filename or "",
        }
        for record in records
    ]


def render_intake_table(records: list[PdfIntakeRecord]) -> None:
    rows = intake_table_rows(records)
    if not rows:
        st.info("Intake queue is empty.")
        return
    st.dataframe(rows, hide_index=True, use_container_width=True)

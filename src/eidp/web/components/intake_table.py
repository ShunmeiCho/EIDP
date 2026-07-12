"""Intake queue table rendering."""

from __future__ import annotations

import streamlit as st

from eidp.pipeline.extraction_queue import ExtractionQueueItem, extraction_status_label
from eidp.pipeline.pdf_intake import PdfIntakeRecord


def intake_table_rows(
    records: list[PdfIntakeRecord],
    extraction_items: list[ExtractionQueueItem] | None = None,
) -> list[dict[str, object]]:
    items_by_intake_id = {item.intake_record_id: item for item in extraction_items or []}
    rows: list[dict[str, object]] = []
    for record in records:
        item = items_by_intake_id.get(record.record_id)
        rows.append(
            {
                "created_at_utc": record.created_at_utc,
                "lane": record.lane.value,
                "extraction_status": extraction_status_label(item),
                "next_action": item.next_action.value if item is not None and item.next_action is not None else "",
                "rows_written": item.rows_written if item is not None else "",
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
        )
    return rows


def render_intake_table(
    records: list[PdfIntakeRecord],
    extraction_items: list[ExtractionQueueItem] | None = None,
) -> None:
    rows = intake_table_rows(records, extraction_items=extraction_items)
    if not rows:
        st.info("Intake queue is empty.")
        return
    st.dataframe(rows, hide_index=True, use_container_width=True)

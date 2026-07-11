"""Read-only extraction queue page for the Linux/Web MVP."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from eidp.config import settings
from eidp.db.locking import LockBusyError
from eidp.pipeline.extraction_queue import ensure_extraction_queue, load_extraction_queue
from eidp.pipeline.pdf_intake import load_intake_queue
from eidp.web.components.intake_table import render_intake_table
from eidp.web.locking import acquire_web_write_lock


def render_extraction_queue_page(*, intake_root: Path | None = None) -> None:
    resolved_root = intake_root or Path(settings.data_dir) / "web-intake"
    st.title("EIDP Extraction Queue")
    st.caption("Text PDFs wait for extraction. Image PDFs stay in the manual/OCR exception lane.")
    records = load_intake_queue(resolved_root)
    try:
        with acquire_web_write_lock(resolved_root, owner="web_extraction_queue_sync"):
            extraction_items = ensure_extraction_queue(resolved_root)
    except LockBusyError as exc:
        st.warning(str(exc))
        extraction_items = load_extraction_queue(resolved_root)
    render_intake_table(records, extraction_items=extraction_items)

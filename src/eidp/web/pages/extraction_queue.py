"""Served extraction queue page for the Linux/Web MVP."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from eidp.config import settings
from eidp.db.locking import LockBusyError
from eidp.identity import ResolvedIdentity
from eidp.pipeline.extraction_queue import (
    ExtractionQueueItem,
    ExtractionQueueType,
    ExtractionStatus,
    ensure_extraction_queue,
    load_extraction_queue,
)
from eidp.pipeline.pdf_intake import load_intake_queue
from eidp.web.components.intake_table import render_intake_table
from eidp.web.locking import acquire_web_write_lock
from eidp.web.services.extraction import run_extraction


def render_extraction_queue_page(*, identity: ResolvedIdentity, intake_root: Path | None = None) -> None:
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
    _render_extraction_actions(resolved_root, identity, extraction_items)


def _render_extraction_actions(
    intake_root: Path,
    identity: ResolvedIdentity,
    items: list[ExtractionQueueItem],
) -> None:
    for item in items:
        if item.queue_type != ExtractionQueueType.TEXT_EXTRACTION:
            continue
        if item.status == ExtractionStatus.EXTRACTION_FAILED and item.error_reason:
            st.error(f"Extraction failed for {item.school_name}: {item.error_reason}")
        if item.status == ExtractionStatus.PENDING_EXTRACTION:
            if st.button("Run", key=f"run_extraction_{item.intake_record_id}", type="primary"):
                _run_extraction_action(intake_root, item.intake_record_id, identity)
        elif item.status == ExtractionStatus.EXTRACTION_FAILED:
            if st.button("Retry", key=f"retry_extraction_{item.intake_record_id}", type="primary"):
                _run_extraction_action(intake_root, item.intake_record_id, identity)


def _run_extraction_action(intake_root: Path, intake_record_id: str, identity: ResolvedIdentity) -> None:
    try:
        with acquire_web_write_lock(intake_root, owner="web_served_extraction"):
            run_extraction(
                intake_root=intake_root,
                intake_record_id=intake_record_id,
                identity=identity,
            )
    except LockBusyError as exc:
        st.warning(str(exc))
        return
    st.rerun()

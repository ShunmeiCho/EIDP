"""Served bridge from the extraction queue UI to the extraction core."""

from __future__ import annotations

from pathlib import Path

import structlog

from eidp.identity import ResolvedIdentity
from eidp.pdf.table_grid_extractor import extract_table_grid_records
from eidp.pipeline.extraction_queue import ExtractionQueueItem, ExtractorFunc, process_intake_record

log = structlog.get_logger(__name__)


def run_extraction(
    *,
    intake_root: Path,
    intake_record_id: str,
    identity: ResolvedIdentity,
    extractor_func: ExtractorFunc = extract_table_grid_records,
) -> ExtractionQueueItem:
    """Record a safe served-request event and run the reproducible extraction core."""

    log.info(
        "served_extraction_requested",
        actor=identity.actor,
        identity_source=identity.source.value,
        intake_record_id=intake_record_id,
    )
    return process_intake_record(
        intake_root=intake_root,
        intake_record_id=intake_record_id,
        extractor_func=extractor_func,
    )


__all__ = ["run_extraction"]

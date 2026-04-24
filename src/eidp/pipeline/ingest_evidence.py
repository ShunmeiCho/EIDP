"""Ingest-side rejection evidence trail.

Mirrors scraper/discovery_evidence.py for the ingest stage. When a document
is rejected for no_file / school_mismatch / parse_failed / non_target /
ocr_pending / hash_dedup / transient_error, emit one JSON line with the
doc_id, school_id, reason, detail, and timestamp so operators can audit
why a document did not reach the DB.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import structlog

log = structlog.get_logger()


@dataclass(frozen=True)
class IngestRejection:
    doc_id: int
    school_id: int | None
    file_path: str | None
    source_url: str | None
    pdf_type: str | None
    reason: str
    detail: dict[str, str] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class IngestEvidenceRecorder:
    """Append-only JSONL writer. Never raises into the caller."""

    def __init__(self, path: Path | None) -> None:
        self.path = path
        self._fh = None
        if path is not None:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                self._fh = path.open("a", encoding="utf-8")
            except OSError as e:
                log.warning("ingest_evidence_open_failed", path=str(path), error=str(e))
                self._fh = None

    def record(self, ev: IngestRejection) -> None:
        if self._fh is None:
            return
        try:
            self._fh.write(json.dumps(asdict(ev), ensure_ascii=False) + "\n")
            self._fh.flush()
        except OSError as e:
            log.warning("ingest_evidence_write_failed", error=str(e))

    def close(self) -> None:
        if self._fh is None:
            return
        try:
            self._fh.close()
        finally:
            self._fh = None

    def __enter__(self) -> "IngestEvidenceRecorder":
        return self

    def __exit__(self, *_args) -> None:
        self.close()

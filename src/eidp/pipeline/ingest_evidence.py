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
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import TextIO

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
        default_factory=lambda: datetime.now(UTC).isoformat()
    )


class IngestEvidenceRecorder:
    """Append-only JSONL writer. Never raises into the caller."""

    def __init__(self, path: Path | None) -> None:
        self.path = path
        self._fh: TextIO | None = None

    def _open_handle(self) -> TextIO | None:
        if self.path is not None:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                return self.path.open("a", encoding="utf-8")
            except OSError as e:
                log.warning("ingest_evidence_open_failed", path=str(self.path), error=str(e))
        return None

    def _write_json_line(self, fh: TextIO, ev: IngestRejection) -> None:
        fh.write(json.dumps(asdict(ev), ensure_ascii=False) + "\n")
        fh.flush()

    def record(self, ev: IngestRejection) -> None:
        if self.path is None:
            return
        try:
            if self._fh is not None:
                self._write_json_line(self._fh, ev)
                return
            fh = self._open_handle()
            if fh is None:
                return
            try:
                self._write_json_line(fh, ev)
            finally:
                fh.close()
        except OSError as e:
            log.warning("ingest_evidence_write_failed", error=str(e))

    def close(self) -> None:
        if self._fh is None:
            return
        try:
            self._fh.close()
        finally:
            self._fh = None

    def __enter__(self) -> IngestEvidenceRecorder:
        self._fh = self._open_handle()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

"""Persistent evidence trail for discovery decisions.

discover-pdfs deletes/skips a lot of candidate URLs (non_target classification,
HTTP errors, attachment-keyword negative scores). Without a permanent record,
debugging cases like 滋慶 — where every candidate gets rejected and the school
ends up with no document — is blind work.

This recorder appends one JSON line per decision to a file so a later
investigation can grep `school_id` and reconstruct what URLs were attempted,
their scores, anchor text, and the accepted/rejected reason.
"""
from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

import structlog

log = structlog.get_logger()


@dataclass(frozen=True)
class RejectionEvidence:
    """One accepted, rejected, or never-tried PDF candidate captured for debug."""

    school_id: int
    pdf_url: str
    page_url: str = ""
    anchor_text: str = ""
    pattern_type: str = ""
    score: float = 0.0
    reason: str = ""
    pdf_type: str | None = None
    detected_fiscal_year: int | None = None
    year_evidence: str = ""
    trusted_year_evidence: str = ""
    extra: dict[str, str] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )


@dataclass(frozen=True)
class UrlSearchEvidence:
    """One Web-search decision used while looking for a school disclosure page."""

    school_id: int
    school_name: str = ""
    school_type: str = ""
    corporation_name: str = ""
    provider: str = ""
    query: str = ""
    result_url: str = ""
    result_title: str = ""
    result_description: str = ""
    score: float = 0.0
    decision: str = ""
    reason: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )


class EvidenceRecorder:
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
                log.warning("evidence_recorder_open_failed", path=str(self.path), error=str(e))
        return None

    def _write_json_line(self, fh: TextIO, evidence: RejectionEvidence | UrlSearchEvidence) -> None:
        fh.write(json.dumps(asdict(evidence), ensure_ascii=False) + "\n")
        fh.flush()

    def record(self, evidence: RejectionEvidence | UrlSearchEvidence) -> None:
        if self.path is None:
            return
        try:
            if self._fh is not None:
                self._write_json_line(self._fh, evidence)
                return
            fh = self._open_handle()
            if fh is None:
                return
            try:
                self._write_json_line(fh, evidence)
            finally:
                fh.close()
        except OSError as e:
            log.warning("evidence_recorder_write_failed", error=str(e))

    def record_many(self, items: Iterable[RejectionEvidence | UrlSearchEvidence]) -> None:
        for item in items:
            self.record(item)

    def close(self) -> None:
        if self._fh is None:
            return
        try:
            self._fh.close()
        finally:
            self._fh = None

    def __enter__(self) -> EvidenceRecorder:
        self._fh = self._open_handle()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

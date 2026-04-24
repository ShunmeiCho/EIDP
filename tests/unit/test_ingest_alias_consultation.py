"""Tests that ingest consults SchoolAlias when matching school identity.

Historical/renamed school names recorded as SchoolAlias rows must count as
a legitimate match during ingest, otherwise a renamed 滋慶 school (e.g.
'東京ダンス&アクターズ専門学校' → '東京ダンス・俳優＆舞台芸術専門学校')
will be stuck in school_mismatch indefinitely.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.models import Base, Document, School, SchoolAlias
from eidp.pdf.schema import SchoolAnnotation
from eidp.pipeline.ingest import ingest_document
from eidp.pipeline.ingest_evidence import IngestEvidenceRecorder


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _setup_doc(session: Session, file_content: bytes, tmp_path: Path) -> Document:
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(file_content)
    doc = Document(
        id=100,
        school_id=1,
        source_url="https://example.ac.jp/x.pdf",
        file_path=str(pdf),
        file_hash="deadbeef" * 8,
        pdf_type="target",
        content_type="text",
    )
    session.add(doc)
    session.flush()
    return doc


def test_ingest_accepts_matching_alias_and_does_not_mark_mismatch(tmp_path: Path) -> None:
    session = _session()
    try:
        session.add(School(
            id=1, prefecture="東京", corporation_name="滋慶",
            school_name="東京ダンス・俳優＆舞台芸術専門学校",
        ))
        session.add(SchoolAlias(
            school_id=1,
            alias_name="東京ダンス&アクターズ専門学校",
            alias_type="historical",
            source="rename",
        ))
        doc = _setup_doc(session, b"%PDF-1.5\n" + b"x" * 2000, tmp_path)

        # Mock parse_pdf to return the historical (alias) name.
        fake = SchoolAnnotation(
            school_name="東京ダンス&アクターズ専門学校",
            corporation_name=None,
            fiscal_year="令和7年度",
            departments=[],
        )
        with patch("eidp.pipeline.ingest.parse_pdf", return_value=fake):
            stats = ingest_document(session, doc, recorder=None)

        # No school_mismatch — the alias was consulted and matched.
        assert doc.ingest_status != "school_mismatch"
        assert stats.get("skip_reason") != "school_mismatch"
    finally:
        session.close()


def test_short_alias_does_not_falsely_match_by_substring(tmp_path: Path) -> None:
    """Short aliases (< 6 chars) must be exact-match only.

    Regression for Codex-flagged risk: 'TCA in 東京TCA情報学院' style
    substring would otherwise let a 3-letter alias bleed across schools.
    """
    session = _session()
    try:
        session.add(School(
            id=1, prefecture="東京", corporation_name="A",
            school_name="学校A",
        ))
        session.add(SchoolAlias(
            school_id=1, alias_name="TCA", alias_type="short",
            source="test",
        ))
        doc = _setup_doc(session, b"%PDF-1.5\n" + b"x" * 2000, tmp_path)

        # Parsed name contains 'TCA' but is a different school entirely
        fake = SchoolAnnotation(
            school_name="大阪TCA情報学院",
            corporation_name=None,
            fiscal_year="令和7年度",
            departments=[],
        )
        with patch("eidp.pipeline.ingest.parse_pdf", return_value=fake):
            ingest_document(session, doc, recorder=None)

        # Short 3-char alias must NOT match by substring → school_mismatch
        assert doc.ingest_status == "school_mismatch"
    finally:
        session.close()


def test_ingest_records_evidence_on_mismatch_including_aliases_tried(tmp_path: Path) -> None:
    session = _session()
    log_path = tmp_path / "ingest_rej.jsonl"
    try:
        session.add(School(
            id=1, prefecture="東京", corporation_name="A",
            school_name="学校A",
        ))
        session.add(SchoolAlias(
            school_id=1, alias_name="A学園", alias_type="alt", source="test",
        ))
        doc = _setup_doc(session, b"%PDF-1.5\n" + b"x" * 2000, tmp_path)

        fake = SchoolAnnotation(
            school_name="まったく別の学校",
            corporation_name=None,
            fiscal_year="令和7年度",
            departments=[],
        )
        recorder = IngestEvidenceRecorder(log_path)
        with patch("eidp.pipeline.ingest.parse_pdf", return_value=fake):
            ingest_document(session, doc, recorder=recorder)
        recorder.close()

        assert doc.ingest_status == "school_mismatch"
        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        row = json.loads(lines[0])
        assert row["reason"] == "school_mismatch"
        assert row["detail"]["parsed_school_name"] == "まったく別の学校"
        assert row["detail"]["target_school_name"] == "学校A"
        assert row["detail"]["alias_count"] == "1"
    finally:
        session.close()

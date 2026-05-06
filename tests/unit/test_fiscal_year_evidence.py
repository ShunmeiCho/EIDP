from __future__ import annotations

from eidp.db.models import Document
from eidp.fiscal_year_evidence import fiscal_year_evidence_for_document


def test_pdf_text_year_conflict_beats_target_year_url_hint() -> None:
    doc = Document(
        school_id=1,
        source_url="https://example.ac.jp/2026/application.pdf",
        fiscal_year=2025,
        pdf_type="target",
        ingest_status="ingested",
    )

    evidence = fiscal_year_evidence_for_document(doc, target_fiscal_year=2026)

    assert evidence.level == "conflict"
    assert evidence.detected_fiscal_year == 2025
    assert evidence.conflict_reason == "pdf_text_mismatch"


def test_operator_override_is_strongest_target_year_evidence() -> None:
    doc = Document(
        school_id=1,
        source_url="https://example.ac.jp/r7/application.pdf",
        fiscal_year=2025,
        fiscal_year_override=2026,
        pdf_type="target",
        ingest_status="ingested",
    )

    evidence = fiscal_year_evidence_for_document(doc, target_fiscal_year=2026)

    assert evidence.level == "operator_override"
    assert evidence.rank > 4
    assert evidence.confirms_target is True


def test_url_hint_is_lower_than_parsed_pdf_text() -> None:
    doc = Document(
        school_id=1,
        source_url="https://example.ac.jp/2026/application.pdf",
        discovered_from="https://example.ac.jp/info",
        fiscal_year=None,
        pdf_type="target",
        ingest_status="pending",
    )

    evidence = fiscal_year_evidence_for_document(doc, target_fiscal_year=2026)

    assert evidence.level == "url_hint"
    assert evidence.detected_fiscal_year == 2026

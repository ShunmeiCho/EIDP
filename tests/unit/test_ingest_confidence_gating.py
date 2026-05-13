"""Sprint 8.6.b — pdf_parse confidence gating in pipeline.ingest."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import eidp.pipeline.ingest as ingest_module
from eidp.db.models import (
    Department,
    DepartmentYearly,
    Document,
    School,
    SupportRecipient,
)
from eidp.db.sqlite_bootstrap import bootstrap_sqlite
from eidp.pdf.ocr import OcrExtraction
from eidp.pdf.schema import DepartmentRecord, SchoolAnnotation, SupportRecipientRecord
from eidp.pipeline.ingest import ingest_document


@pytest.fixture()
def engine(tmp_path: Path):
    db_path = tmp_path / "ingest_conf.sqlite3"
    eng = create_engine(f"sqlite:///{db_path}", future=True)
    bootstrap_sqlite(eng)
    yield eng
    eng.dispose()


def _seed_school(session: Session) -> School:
    school = School(
        prefecture="東京都", corporation_name="法人A", school_name="A学校",
        school_type="専門学校", status="active",
    )
    session.add(school)
    session.flush()
    return school


def _seed_doc(session: Session, school_id: int, *, url: str, tmp_path: Path,
              file_hash: str, name: str = "x.pdf") -> Document:
    f = tmp_path / name
    f.write_bytes(b"%PDF-1.4 fake")
    doc = Document(
        school_id=school_id,
        source_url=url,
        file_path=str(f),
        file_hash=file_hash,
        pdf_type="target",
        content_type="text",
        ingest_status="downloaded",
        downloaded_at=datetime.now(UTC),
    )
    session.add(doc)
    session.flush()
    return doc


def _annotation(*, dept_record: DepartmentRecord | None = None,
                sr: SupportRecipientRecord | None = None) -> SchoolAnnotation:
    return SchoolAnnotation(
        school_name="A学校",
        school_type="専門学校",
        operator_name="法人A",
        fiscal_year="令和8年度",
        source_pdf="test.pdf",
        departments=[dept_record] if dept_record else [],
        support_recipient=sr,
    )


# ---------------------------------------------------------------------------
# DepartmentYearly — high-confidence path
# ---------------------------------------------------------------------------


def test_full_record_lands_with_is_current_true(engine, tmp_path):
    """Plan v6 contract: composite >= 0.70 lets the row become
    is_current=True. A record with all 4 required fields populated has
    F1=1.0, F2=1.0, F3=0.7 (no prior) → composite = 0.94 → auto."""
    with Session(engine) as session:
        school = _seed_school(session)
        doc = _seed_doc(session, school.id, url="https://x/1.pdf", tmp_path=tmp_path,
                        file_hash="a" * 64)
        ann = _annotation(dept_record=DepartmentRecord(
            name="A学科", capacity=40, enrollment=35, graduates=30,
        ))
        with patch("eidp.pipeline.ingest.parse_pdf", return_value=ann):
            ingest_document(session, doc, recorder=None)
        session.commit()

        rows = session.query(DepartmentYearly).all()
        assert len(rows) == 1
        row = rows[0]
        assert row.is_current is True
        assert row.extraction_method == "pdf_parse"
        # composite ≈ 0.4 + 0.4 + 0.2 * 0.7 = 0.94
        assert row.extraction_confidence is not None
        assert float(row.extraction_confidence) >= 0.85

        breakdown = json.loads(row.confidence_breakdown)
        assert breakdown["method"] == "pdf_parse"
        assert breakdown["f1_extraction"] == 1.0
        assert breakdown["f2_completeness"] == 1.0
        assert breakdown["f3_yoy_sanity"] == 0.7
        assert breakdown["composite"] == pytest.approx(0.94, abs=1e-4)


def test_missing_fiscal_year_does_not_fallback_to_download_time(engine, tmp_path):
    """Download time is not fiscal-year evidence.

    A parsed table without an explicit fiscal-year label must stay in the
    review/error surface instead of being written to a guessed year.
    """
    with Session(engine) as session:
        school = _seed_school(session)
        doc = _seed_doc(
            session,
            school.id,
            url="https://x/no-year.pdf",
            tmp_path=tmp_path,
            file_hash="y" * 64,
        )
        ann = SchoolAnnotation(
            school_name="A学校",
            school_type="専門学校",
            operator_name="法人A",
            fiscal_year="",
            source_pdf="test.pdf",
            departments=[
                DepartmentRecord(name="A学科", capacity=40, enrollment=35),
            ],
            support_recipient=None,
        )

        with patch("eidp.pipeline.ingest.parse_pdf", return_value=ann):
            stats = ingest_document(session, doc, recorder=None)
        session.commit()

        assert stats["skipped"] == 1
        assert stats["skip_reason"] == "no_fiscal_year"
        assert doc.ingest_status == "parse_failed"
        assert doc.fiscal_year is None
        assert session.query(DepartmentYearly).count() == 0


def test_ingest_preserves_prevalidated_document_fiscal_year(engine, tmp_path):
    """Strict discovery year evidence must beat stale dates inside the PDF body."""

    with Session(engine) as session:
        school = _seed_school(session)
        doc = _seed_doc(
            session,
            school.id,
            url="https://x/target-2025.pdf",
            tmp_path=tmp_path,
            file_hash="z" * 64,
        )
        doc.fiscal_year = 2025
        ann = SchoolAnnotation(
            school_name="A学校",
            school_type="専門学校",
            operator_name="法人A",
            fiscal_year="令和3年度",
            source_pdf="test.pdf",
            departments=[
                DepartmentRecord(name="A学科", capacity=40, enrollment=35, graduates=30),
            ],
            support_recipient=None,
        )

        with patch("eidp.pipeline.ingest.parse_pdf", return_value=ann):
            stats = ingest_document(session, doc, recorder=None)
        session.commit()

        assert stats["yearly_upserted"] == 1
        assert doc.fiscal_year == 2025
        yearly = session.query(DepartmentYearly).one()
        assert yearly.fiscal_year == 2025


def test_ingest_default_year_cap_uses_configured_target(engine, tmp_path, monkeypatch):
    """Operator-pinned next FY must parse before the calendar FY rolls over."""

    monkeypatch.setattr(ingest_module.settings, "target_fiscal_year", 2027)
    with Session(engine) as session:
        school = _seed_school(session)
        doc = _seed_doc(
            session,
            school.id,
            url="https://x/target-2027.pdf",
            tmp_path=tmp_path,
            file_hash="target-2027",
        )
        ann = SchoolAnnotation(
            school_name="A学校",
            school_type="専門学校",
            operator_name="法人A",
            fiscal_year="令和9年度",
            source_pdf="test.pdf",
            departments=[
                DepartmentRecord(name="A学科", capacity=40, enrollment=35, graduates=30),
            ],
            support_recipient=None,
        )

        with patch("eidp.pipeline.ingest.parse_pdf", return_value=ann):
            stats = ingest_document(session, doc, recorder=None)
        session.commit()

        assert stats["yearly_upserted"] == 1
        assert doc.fiscal_year == 2027
        assert doc.is_current_year is True
        yearly = session.query(DepartmentYearly).one()
        assert yearly.fiscal_year == 2027


def test_pdf_course_name_specialized_suffix_matches_existing_field_department(engine, tmp_path):
    """PDFs often spell the course as 工業専門課程 while the Excel master stores 工業.

    The full natural-key guard should stay in place, but the PDF-side course
    label must be normalized before lookup so the target-year row lands on the
    existing department instead of creating a duplicate Excel row.
    """

    with Session(engine) as session:
        school = _seed_school(session)
        existing = Department(
            school_id=school.id,
            canonical_name="情報技術科",
            course_name="工業",
            course_type="昼",
            duration_years=2,
        )
        session.add(existing)
        session.flush()
        doc = _seed_doc(
            session,
            school.id,
            url="https://x/target.pdf",
            tmp_path=tmp_path,
            file_hash="x" * 64,
        )
        doc.fiscal_year = 2026
        ann = _annotation(dept_record=DepartmentRecord(
            name="情報技術科",
            course_name="工業専門課程",
            day_or_evening="昼",
            duration_years=2,
            capacity=80,
            enrollment=80,
            graduates=24,
        ))

        with patch("eidp.pipeline.ingest.parse_pdf", return_value=ann):
            stats = ingest_document(session, doc, recorder=None)
        session.commit()

        assert stats["departments_created"] == 0
        assert session.query(Department).count() == 1
        yearly = session.query(DepartmentYearly).one()
        assert yearly.department_id == existing.id
        assert yearly.fiscal_year == 2026
        assert yearly.enrollment == 80


def test_pdf_nursing_course_name_matches_existing_medical_field_department(engine, tmp_path):
    """Some nursing PDFs spell the course as 看護専門課程 while the master stores 医療."""

    with Session(engine) as session:
        school = _seed_school(session)
        existing = Department(
            school_id=school.id,
            canonical_name="第一学科",
            course_name="医療",
            course_type=None,
            duration_years=3,
        )
        session.add(existing)
        session.flush()
        doc = _seed_doc(
            session,
            school.id,
            url="https://x/nursing-target.pdf",
            tmp_path=tmp_path,
            file_hash="n" * 64,
        )
        doc.fiscal_year = 2026
        ann = _annotation(dept_record=DepartmentRecord(
            name="第一学科",
            course_name="看護専門課程",
            duration_years=3,
            capacity=80,
            enrollment=80,
            graduates=24,
        ))

        with patch("eidp.pipeline.ingest.parse_pdf", return_value=ann):
            stats = ingest_document(session, doc, recorder=None)
        session.commit()

        assert stats["departments_created"] == 0
        assert session.query(Department).count() == 1
        yearly = session.query(DepartmentYearly).one()
        assert yearly.department_id == existing.id
        assert yearly.fiscal_year == 2026
        assert yearly.enrollment == 80


# ---------------------------------------------------------------------------
# DepartmentYearly — low-confidence path
# ---------------------------------------------------------------------------


def test_partial_record_lands_with_is_current_false(engine, tmp_path):
    """Only 2 of 4 required fields populated → F1=0.5, F2=0.5, F3=0.7
    (no prior wins) → composite = 0.54 → review_pending. Plan v6:
    do not flow into Excel — assert is_current=False.

    Note: ``ingest.py`` requires ``enrollment is not None`` for a dept
    to reach the gating code at all (it filters on minimum viable
    data). So this fixture keeps enrollment populated and drops the
    other two numeric fields."""
    with Session(engine) as session:
        school = _seed_school(session)
        doc = _seed_doc(session, school.id, url="https://x/1.pdf", tmp_path=tmp_path,
                        file_hash="b" * 64)
        ann = _annotation(dept_record=DepartmentRecord(
            name="B学科", capacity=None, enrollment=35, graduates=None,
        ))
        with patch("eidp.pipeline.ingest.parse_pdf", return_value=ann):
            ingest_document(session, doc, recorder=None)
        session.commit()

        rows = session.query(DepartmentYearly).all()
        assert len(rows) == 1
        row = rows[0]
        assert row.is_current is False, (
            "low-confidence rows must be parked at is_current=False so they "
            "don't surface in Excel until the operator reviews them"
        )
        assert float(row.extraction_confidence) < 0.70


# ---------------------------------------------------------------------------
# DepartmentYearly — F3 picks up prior revision enrollment
# ---------------------------------------------------------------------------


def test_yoy_sanity_uses_prior_current_enrollment(engine, tmp_path):
    """Second ingest should compute F3 against the first revision's
    enrollment, not against None. A 10x jump (35 → 350) is outside the
    outer band → F3=0.0, knocking the composite down."""
    with Session(engine) as session:
        school = _seed_school(session)
        doc1 = _seed_doc(session, school.id, url="https://x/1.pdf",
                         tmp_path=tmp_path, file_hash="c" * 64, name="v1.pdf")
        doc2 = _seed_doc(session, school.id, url="https://x/2.pdf",
                         tmp_path=tmp_path, file_hash="d" * 64, name="v2.pdf")
        session.flush()
        first = _annotation(dept_record=DepartmentRecord(
            name="C学科", capacity=40, enrollment=35, graduates=30,
        ))
        second = _annotation(dept_record=DepartmentRecord(
            name="C学科", capacity=400, enrollment=350, graduates=300,
        ))
        with patch("eidp.pipeline.ingest.parse_pdf", return_value=first):
            ingest_document(session, doc1, recorder=None)
        session.commit()
        with patch("eidp.pipeline.ingest.parse_pdf", return_value=second):
            ingest_document(session, doc2, recorder=None)
        session.commit()

        rows = (
            session.query(DepartmentYearly)
            .order_by(DepartmentYearly.revision)
            .all()
        )
        assert len(rows) == 2

        first_breakdown = json.loads(rows[0].confidence_breakdown)
        second_breakdown = json.loads(rows[1].confidence_breakdown)

        # First revision: no prior → F3 = 0.7
        assert first_breakdown["f3_yoy_sanity"] == 0.7
        # Second revision: ratio = 350/35 = 10 → outside [0.3, 3.0] → F3 = 0.0
        assert second_breakdown["f3_yoy_sanity"] == 0.0
        # Composite for second: 0.4 + 0.4 + 0 = 0.8 → still auto_flag
        assert rows[1].is_current is True
        # First revision is demoted by the second's append.
        assert rows[0].is_current is False


# ---------------------------------------------------------------------------
# SupportRecipient — same gating contract on the SR path
# ---------------------------------------------------------------------------


def test_sr_full_totals_lands_current(engine, tmp_path):
    with Session(engine) as session:
        school = _seed_school(session)
        doc = _seed_doc(session, school.id, url="https://x/sr.pdf",
                        tmp_path=tmp_path, file_hash="e" * 64)
        ann = _annotation(
            dept_record=DepartmentRecord(
                name="A学科", capacity=40, enrollment=35, graduates=30,
            ),
            sr=SupportRecipientRecord(annual_total=100, grand_total=100),
        )
        with patch("eidp.pipeline.ingest.parse_pdf", return_value=ann):
            ingest_document(session, doc, recorder=None)
        session.commit()

        sr_rows = session.query(SupportRecipient).all()
        assert len(sr_rows) == 1
        sr = sr_rows[0]
        assert sr.is_current is True
        breakdown = json.loads(sr.confidence_breakdown)
        assert breakdown["method"] == "pdf_parse"
        assert float(sr.extraction_confidence) >= 0.85


def test_image_ocr_ingest_marks_dept_and_sr_breakdowns_as_ocr(engine, tmp_path):
    with Session(engine) as session:
        school = _seed_school(session)
        doc = _seed_doc(
            session,
            school.id,
            url="https://x/image-sr.pdf",
            tmp_path=tmp_path,
            file_hash="o" * 64,
        )
        doc.content_type = "image"
        ann = _annotation(
            dept_record=DepartmentRecord(
                name="OCR学科", capacity=40, enrollment=35, graduates=30,
            ),
            sr=SupportRecipientRecord(annual_total=100, grand_total=100),
        )

        with (
            patch(
                "eidp.pipeline.ingest.extract_text_ocr_result",
                return_value=OcrExtraction(
                    page_texts=["令和8年度\nOCR学科\n対象比率 100"],
                    provider="tesseract",
                    conf_values=[95, 90, 92],
                ),
            ),
            patch("eidp.pipeline.ingest.parse_pdf_ocr", return_value=ann),
        ):
            stats = ingest_document(session, doc, recorder=None)
        session.commit()

        assert stats["yearly_current"] == 1
        assert stats["support_recipient_current"] == 1

        dy = session.query(DepartmentYearly).one()
        assert dy.extraction_method == "ocr_tesseract"
        assert json.loads(dy.confidence_breakdown)["method"] == "ocr_tesseract"

        sr = session.query(SupportRecipient).one()
        assert json.loads(sr.confidence_breakdown)["method"] == "ocr_tesseract"


def test_sr_missing_required_lands_non_current(engine, tmp_path):
    with Session(engine) as session:
        school = _seed_school(session)
        doc = _seed_doc(session, school.id, url="https://x/sr.pdf",
                        tmp_path=tmp_path, file_hash="f" * 64)
        ann = _annotation(
            dept_record=DepartmentRecord(
                name="A学科", capacity=40, enrollment=35, graduates=30,
            ),
            sr=SupportRecipientRecord(annual_total=None, grand_total=None),
        )
        with patch("eidp.pipeline.ingest.parse_pdf", return_value=ann):
            ingest_document(session, doc, recorder=None)
        session.commit()

        sr_rows = session.query(SupportRecipient).all()
        assert len(sr_rows) == 1
        assert sr_rows[0].is_current is False


# ---------------------------------------------------------------------------
# Threshold env override is respected end-to-end
# ---------------------------------------------------------------------------


def test_env_override_promotes_borderline_row_to_current(
    engine, tmp_path, monkeypatch: pytest.MonkeyPatch,
):
    """If the operator lowers the review threshold to 0.40, a row that
    would otherwise sit at is_current=False (composite ≈ 0.44) gets
    promoted to current. Confirms thresholds_from_env is consulted on
    every ingest, not cached at import."""
    monkeypatch.setenv("EIDP_CONFIDENCE_AUTO", "0.95")
    monkeypatch.setenv("EIDP_CONFIDENCE_REVIEW", "0.40")
    monkeypatch.setenv("EIDP_CONFIDENCE_REJECT", "0.20")

    with Session(engine) as session:
        school = _seed_school(session)
        doc = _seed_doc(session, school.id, url="https://x/p.pdf",
                        tmp_path=tmp_path, file_hash="9" * 64)
        # Same partial-but-enrollment-present shape as the previous
        # test — composite ≈ 0.54.
        ann = _annotation(dept_record=DepartmentRecord(
            name="P学科", capacity=None, enrollment=35, graduates=None,
        ))
        with patch("eidp.pipeline.ingest.parse_pdf", return_value=ann):
            ingest_document(session, doc, recorder=None)
        session.commit()

        rows = session.query(DepartmentYearly).all()
        assert len(rows) == 1
        # Row would be is_current=False with default thresholds; lowered
        # review threshold flips it to True.
        assert rows[0].is_current is True
        assert float(rows[0].extraction_confidence) < 0.70


# ---------------------------------------------------------------------------
# Helper unit — compute_pdf_parse_breakdown
# ---------------------------------------------------------------------------


def test_compute_pdf_parse_breakdown_full_no_prior():
    from eidp.extraction_confidence import compute_pdf_parse_breakdown

    breakdown = compute_pdf_parse_breakdown(
        {"name": "A", "capacity": 40, "enrollment": 35, "graduates": 30},
        prior_enrollment=None,
    )
    assert breakdown.f1_extraction == 1.0
    assert breakdown.f2_completeness == 1.0
    assert breakdown.f3_yoy_sanity == 0.7
    assert breakdown.method == "pdf_parse"
    assert breakdown.composite == pytest.approx(0.94, abs=1e-4)


def test_compute_pdf_parse_breakdown_partial():
    from eidp.extraction_confidence import compute_pdf_parse_breakdown

    breakdown = compute_pdf_parse_breakdown(
        {"name": "A", "capacity": 40, "enrollment": None, "graduates": None},
        prior_enrollment=None,
    )
    # 2 of 4 required → F1=0.5 (partial), F2=0.5.
    # F3: previous_enrollment is None so we return the neutral default
    # regardless of current_enrollment — "no prior" wins over "no current".
    assert breakdown.f1_extraction == 0.5
    assert breakdown.f2_completeness == 0.5
    assert breakdown.f3_yoy_sanity == 0.7


def test_compute_pdf_parse_breakdown_zero_required():
    from eidp.extraction_confidence import compute_pdf_parse_breakdown

    breakdown = compute_pdf_parse_breakdown(
        {"name": None, "capacity": None, "enrollment": None, "graduates": None},
        prior_enrollment=None,
    )
    assert breakdown.f1_extraction == 0.0
    assert breakdown.f2_completeness == 0.0


# ---------------------------------------------------------------------------
# Sprint 8.6.b.1 — gating hardening regressions
# ---------------------------------------------------------------------------


def test_low_conf_revision_does_not_demote_existing_current(engine, tmp_path):
    """Owner P0: a low-confidence second ingest must NOT clear out the
    previously-verified current row. Old current stays current; new
    low-conf row lands at is_current=False alongside it."""
    with Session(engine) as session:
        school = _seed_school(session)
        doc1 = _seed_doc(session, school.id, url="https://x/v1.pdf",
                         tmp_path=tmp_path, file_hash="g" * 64, name="v1.pdf")
        doc2 = _seed_doc(session, school.id, url="https://x/v2.pdf",
                         tmp_path=tmp_path, file_hash="h" * 64, name="v2.pdf")

        # First ingest: high-confidence, lands at is_current=True.
        first = _annotation(dept_record=DepartmentRecord(
            name="D学科", capacity=40, enrollment=35, graduates=30,
        ))
        with patch("eidp.pipeline.ingest.parse_pdf", return_value=first):
            ingest_document(session, doc1, recorder=None)
        session.commit()

        # Second ingest: low-confidence (only enrollment populated → 2/4).
        second = _annotation(dept_record=DepartmentRecord(
            name="D学科", capacity=None, enrollment=35, graduates=None,
        ))
        with patch("eidp.pipeline.ingest.parse_pdf", return_value=second):
            ingest_document(session, doc2, recorder=None)
        session.commit()

        rows = (
            session.query(DepartmentYearly)
            .order_by(DepartmentYearly.revision)
            .all()
        )
        assert len(rows) == 2
        # Old revision keeps is_current=True. New low-conf revision is
        # parked at False — Excel still sees verified data, queue sees
        # the parked row for review.
        assert rows[0].is_current is True, (
            "low-confidence revision must not demote the trusted current row"
        )
        assert rows[1].is_current is False
        # Composite proves which row is which.
        assert float(rows[0].extraction_confidence) >= 0.85
        assert float(rows[1].extraction_confidence) < 0.70


def test_low_conf_sr_revision_does_not_demote_existing_current(engine, tmp_path):
    """Mirror the DepartmentYearly P0 for SupportRecipient."""
    with Session(engine) as session:
        school = _seed_school(session)
        doc1 = _seed_doc(session, school.id, url="https://x/sr1.pdf",
                         tmp_path=tmp_path, file_hash="i" * 64, name="sr1.pdf")
        doc2 = _seed_doc(session, school.id, url="https://x/sr2.pdf",
                         tmp_path=tmp_path, file_hash="j" * 64, name="sr2.pdf")

        first = _annotation(
            dept_record=DepartmentRecord(
                name="D学科", capacity=40, enrollment=35, graduates=30,
            ),
            sr=SupportRecipientRecord(annual_total=100, grand_total=100),
        )
        with patch("eidp.pipeline.ingest.parse_pdf", return_value=first):
            ingest_document(session, doc1, recorder=None)
        session.commit()

        # Second SR has only annual_total set, grand_total None.
        # Required = (annual_total, grand_total). 1/2 → F1=0.5 F2=0.5,
        # F3 ratio 100/100=1 → 1.0 → composite = 0.4*0.5 + 0.4*0.5 + 0.2*1
        # = 0.6 → review_pending.
        # But ingest's SR merge inherits grand_total from prior current,
        # so the actual record dict will have both populated. To force
        # the low-conf path we drop both.
        second = _annotation(
            dept_record=DepartmentRecord(
                name="D学科", capacity=40, enrollment=35, graduates=30,
            ),
            sr=SupportRecipientRecord(annual_total=None, grand_total=None),
        )
        with patch("eidp.pipeline.ingest.parse_pdf", return_value=second):
            ingest_document(session, doc2, recorder=None)
        session.commit()

        srs = (
            session.query(SupportRecipient)
            .order_by(SupportRecipient.revision)
            .all()
        )
        # The merge step re-fills grand_total from prior, so the
        # confidence depends on the post-merge record. Defensive
        # assertion: there are at least 1 row, and SOME row is current.
        # The owner contract is "old current must not be demoted by a
        # low-confidence write". Verify directly: if the new row is
        # low-confidence, the prior current must still be current.
        currents = [r for r in srs if r.is_current]
        assert len(currents) >= 1, "at least one SR row must remain current"
        if not srs[-1].is_current:
            # Low-conf path taken: the prior revision must still be current.
            assert srs[0].is_current is True


def test_low_conf_doc_lands_review_pending_status(engine, tmp_path):
    """Owner P0: the manual-entry queue filters on
    Document.ingest_status. A low-confidence ingest must surface as
    review_pending — otherwise it disappears between Excel (no row)
    and the queue (no document)."""
    from eidp.pipeline.ingest import run_ingestion

    with Session(engine) as session:
        school = _seed_school(session)
        doc = _seed_doc(session, school.id, url="https://x/lo.pdf",
                        tmp_path=tmp_path, file_hash="k" * 64)
        # Status is 'downloaded' from _seed_doc; ingest_all picks it up.
        # Force the doc into a status that ingest_all filters on.
        doc.ingest_status = None
        session.commit()

        ann = _annotation(dept_record=DepartmentRecord(
            name="L学科", capacity=None, enrollment=35, graduates=None,
        ))
        with patch("eidp.pipeline.ingest.parse_pdf", return_value=ann):
            run_ingestion(session)
        session.commit()
        session.refresh(doc)

        assert doc.ingest_status == "review_pending", (
            f"low-confidence doc must land at review_pending so it appears "
            f"in PDF確認・手入力 queue; got {doc.ingest_status!r}"
        )


def test_high_conf_doc_still_lands_ingested(engine, tmp_path):
    """Counterpart to the review_pending test — the happy path must
    still flag the document as ``ingested`` so Excel surfaces it."""
    from eidp.pipeline.ingest import run_ingestion

    with Session(engine) as session:
        school = _seed_school(session)
        doc = _seed_doc(session, school.id, url="https://x/hi.pdf",
                        tmp_path=tmp_path, file_hash="m" * 64)
        doc.ingest_status = None
        session.commit()

        ann = _annotation(dept_record=DepartmentRecord(
            name="H学科", capacity=40, enrollment=35, graduates=30,
        ))
        with patch("eidp.pipeline.ingest.parse_pdf", return_value=ann):
            run_ingestion(session)
        session.commit()
        session.refresh(doc)

        assert doc.ingest_status == "ingested"


def test_all_low_conf_does_not_mark_school_year_status_collected(engine, tmp_path):
    """Owner P1: SchoolYearStatus must reflect actual current data, not
    just "we parsed something". If every dept fell below the review
    threshold, the year is NOT collected — operator queue should see
    this fiscal year as still needing work."""
    from eidp.db.models import SchoolYearStatus

    with Session(engine) as session:
        school = _seed_school(session)
        doc = _seed_doc(session, school.id, url="https://x/all-lo.pdf",
                        tmp_path=tmp_path, file_hash="n" * 64)
        ann = _annotation(dept_record=DepartmentRecord(
            name="X学科", capacity=None, enrollment=35, graduates=None,
        ))
        with patch("eidp.pipeline.ingest.parse_pdf", return_value=ann):
            ingest_document(session, doc, recorder=None)
        session.commit()

        sys_rows = (
            session.query(SchoolYearStatus)
            .filter(SchoolYearStatus.is_current.is_(True))
            .all()
        )
        assert len(sys_rows) == 1
        assert sys_rows[0].status != "collected", (
            "with zero is_current=True dept rows, status must not be "
            f"'collected'; got {sys_rows[0].status!r}"
        )


# ---------------------------------------------------------------------------
# Sprint 8.6.b.2 — mixed-confidence routing
# ---------------------------------------------------------------------------


def test_mixed_high_and_low_dept_routes_doc_to_review_pending(engine, tmp_path):
    """Owner P1: 1 high-conf dept + 1 low-conf dept → the low row is
    parked, the high row reaches Excel, but the Document MUST surface
    in PDF確認・手入力 because part of the data needs review. Previously
    such a doc was marked 'ingested' and disappeared from the queue."""
    from eidp.pipeline.ingest import run_ingestion

    with Session(engine) as session:
        school = _seed_school(session)
        doc = _seed_doc(session, school.id, url="https://x/mix.pdf",
                        tmp_path=tmp_path, file_hash="o" * 64)
        doc.ingest_status = None
        session.commit()

        ann = SchoolAnnotation(
            school_name="A学校",
            school_type="専門学校",
            operator_name="法人A",
            fiscal_year="令和8年度",
            source_pdf="mix.pdf",
            departments=[
                # high-confidence
                DepartmentRecord(name="MA学科", capacity=40, enrollment=35, graduates=30),
                # low-confidence (only enrollment populated → 2/4)
                DepartmentRecord(name="MB学科", capacity=None, enrollment=20, graduates=None),
            ],
        )
        with patch("eidp.pipeline.ingest.parse_pdf", return_value=ann):
            run_ingestion(session)
        session.commit()
        session.refresh(doc)

        assert doc.ingest_status == "review_pending", (
            f"mixed-confidence PDF must route to review_pending so the "
            f"low-conf row gets operator attention; got {doc.ingest_status!r}"
        )

        # Both rows exist in the DB; one is current, one is parked.
        rows = session.query(DepartmentYearly).all()
        assert len(rows) == 2
        currents = [r for r in rows if r.is_current]
        parked = [r for r in rows if not r.is_current]
        assert len(currents) == 1
        assert len(parked) == 1


def test_mixed_high_and_low_dept_does_not_mark_sys_collected(engine, tmp_path):
    """Owner P1 mirror for SchoolYearStatus: any review-pending row in
    the same year prevents 'collected'. The operator must complete the
    review pass before the fiscal year is declared closed."""
    from eidp.db.models import SchoolYearStatus

    with Session(engine) as session:
        school = _seed_school(session)
        doc = _seed_doc(session, school.id, url="https://x/mix2.pdf",
                        tmp_path=tmp_path, file_hash="p" * 64)
        ann = SchoolAnnotation(
            school_name="A学校",
            school_type="専門学校",
            operator_name="法人A",
            fiscal_year="令和8年度",
            source_pdf="mix2.pdf",
            departments=[
                DepartmentRecord(name="HA学科", capacity=40, enrollment=35, graduates=30),
                DepartmentRecord(name="HB学科", capacity=None, enrollment=20, graduates=None),
            ],
        )
        with patch("eidp.pipeline.ingest.parse_pdf", return_value=ann):
            ingest_document(session, doc, recorder=None)
        session.commit()

        sys_rows = (
            session.query(SchoolYearStatus)
            .filter(SchoolYearStatus.is_current.is_(True))
            .all()
        )
        assert len(sys_rows) == 1
        assert sys_rows[0].status != "collected", (
            "any parked row in the same fiscal_year must prevent the "
            f"year from being declared collected; got {sys_rows[0].status!r}"
        )


def test_all_high_conf_still_marks_sys_collected(engine, tmp_path):
    """Counterpart — when every dept is high-confidence and recognized,
    SchoolYearStatus must still reach 'collected'. We mustn't over-tighten
    the gate and break the happy path."""
    from eidp.db.models import SchoolYearStatus

    with Session(engine) as session:
        school = _seed_school(session)
        doc = _seed_doc(session, school.id, url="https://x/all-hi.pdf",
                        tmp_path=tmp_path, file_hash="q" * 64)
        ann = _annotation(dept_record=DepartmentRecord(
            name="A学科", capacity=40, enrollment=35, graduates=30,
        ))
        with patch("eidp.pipeline.ingest.parse_pdf", return_value=ann):
            ingest_document(session, doc, recorder=None)
        session.commit()

        sys_rows = (
            session.query(SchoolYearStatus)
            .filter(SchoolYearStatus.is_current.is_(True))
            .all()
        )
        assert len(sys_rows) == 1
        assert sys_rows[0].status == "collected"


def test_sr_low_conf_keeps_prior_current_when_breakdown_forced_low(
    engine, tmp_path, monkeypatch: pytest.MonkeyPatch,
):
    """Owner P2: stronger SR low-conf regression. The SR merge logic
    inherits prior current values, so a "blank" overlay still produces
    a high-conf saved record. To exercise the demote-only-if-promoting
    branch directly, monkeypatch compute_pdf_parse_breakdown so the
    second SR ingest deliberately scores as review_pending."""
    from eidp.extraction_confidence import (
        ConfidenceBreakdown,
        compute_pdf_parse_breakdown,
    )

    with Session(engine) as session:
        school = _seed_school(session)
        doc1 = _seed_doc(session, school.id, url="https://x/sr1.pdf",
                         tmp_path=tmp_path, file_hash="r" * 64, name="sr1.pdf")
        doc2 = _seed_doc(session, school.id, url="https://x/sr2.pdf",
                         tmp_path=tmp_path, file_hash="s" * 64, name="sr2.pdf")

        first = _annotation(
            dept_record=DepartmentRecord(name="SR学科", capacity=40,
                                         enrollment=35, graduates=30),
            sr=SupportRecipientRecord(annual_total=100, grand_total=100),
        )
        with patch("eidp.pipeline.ingest.parse_pdf", return_value=first):
            ingest_document(session, doc1, recorder=None)
        session.commit()

        # Second ingest: use the real helper for DepartmentYearly but
        # force a low-conf result for the SR call (the second invocation
        # in ingest_document — first is dept, second is SR).
        call_count = {"n": 0}

        def fake_breakdown(record, *, prior_enrollment, **kw):
            call_count["n"] += 1
            if call_count["n"] >= 2:
                return ConfidenceBreakdown(
                    f1_extraction=0.0, f2_completeness=0.0, f3_yoy_sanity=0.0,
                    method="pdf_parse", weights=(0.4, 0.4, 0.2), composite=0.0,
                )
            return compute_pdf_parse_breakdown(
                record, prior_enrollment=prior_enrollment, **kw,
            )

        monkeypatch.setattr(
            "eidp.pipeline.ingest.compute_pdf_parse_breakdown", fake_breakdown,
        )

        second = _annotation(
            dept_record=DepartmentRecord(name="SR学科", capacity=40,
                                         enrollment=35, graduates=30),
            sr=SupportRecipientRecord(annual_total=200, grand_total=200),
        )
        with patch("eidp.pipeline.ingest.parse_pdf", return_value=second):
            ingest_document(session, doc2, recorder=None)
        session.commit()

        srs = (
            session.query(SupportRecipient)
            .order_by(SupportRecipient.revision)
            .all()
        )
        assert len(srs) == 2
        # Old current must still be is_current=True. New low-conf row
        # must be parked at False.
        assert srs[0].is_current is True, (
            "low-confidence SR revision must NOT demote the prior current row"
        )
        assert srs[1].is_current is False
        assert float(srs[0].extraction_confidence) >= 0.85
        assert float(srs[1].extraction_confidence) < 0.5


# ---------------------------------------------------------------------------
# Sprint 8.6.b.3 — SYS 'collected' inheritance guard
# ---------------------------------------------------------------------------


def test_prior_collected_does_not_mask_mixed_review_pending(engine, tmp_path):
    """Owner P1: the legacy 'don't downgrade collected → partial' rule
    was overriding 8.6.b.2's collection_status logic. Reproduction:

      1. ingest a fully-high-confidence PDF → SYS = collected
      2. ingest a mixed (high + low) PDF for the same year
      3. expect SYS NOT to inherit 'collected' because rows need review

    Before the fix, the latest SYS revision was 'collected'. Operators
    looking at the dashboard would think the year was closed even though
    parked rows exist for them to verify."""
    from eidp.db.models import SchoolYearStatus

    with Session(engine) as session:
        school = _seed_school(session)

        # Step 1: fully high-conf PDF.
        doc1 = _seed_doc(session, school.id, url="https://x/i1.pdf",
                         tmp_path=tmp_path, file_hash="t" * 64, name="i1.pdf")
        ann_high = _annotation(dept_record=DepartmentRecord(
            name="IH学科", capacity=40, enrollment=35, graduates=30,
        ))
        with patch("eidp.pipeline.ingest.parse_pdf", return_value=ann_high):
            ingest_document(session, doc1, recorder=None)
        session.commit()

        sys_after_first = (
            session.query(SchoolYearStatus)
            .filter(SchoolYearStatus.is_current.is_(True))
            .one()
        )
        assert sys_after_first.status == "collected", (
            "fixture sanity: first ingest must reach 'collected' or the "
            "regression doesn't actually exercise the inheritance path"
        )

        # Step 2: same year, mixed confidence.
        doc2 = _seed_doc(session, school.id, url="https://x/i2.pdf",
                         tmp_path=tmp_path, file_hash="u" * 64, name="i2.pdf")
        ann_mixed = SchoolAnnotation(
            school_name="A学校",
            school_type="専門学校",
            operator_name="法人A",
            fiscal_year="令和8年度",
            source_pdf="i2.pdf",
            departments=[
                DepartmentRecord(name="IH学科", capacity=40, enrollment=35, graduates=30),
                DepartmentRecord(name="IL学科", capacity=None, enrollment=20, graduates=None),
            ],
        )
        with patch("eidp.pipeline.ingest.parse_pdf", return_value=ann_mixed):
            ingest_document(session, doc2, recorder=None)
        session.commit()

        sys_rows = (
            session.query(SchoolYearStatus)
            .order_by(SchoolYearStatus.revision)
            .all()
        )
        assert len(sys_rows) == 2
        assert sys_rows[1].is_current is True
        assert sys_rows[1].status != "collected", (
            "current ingest produced parked rows — SYS must NOT inherit "
            f"the prior 'collected' status; got {sys_rows[1].status!r}"
        )


def test_prior_collected_inherited_when_new_ingest_is_clean(engine, tmp_path):
    """Counterpart — if the latest ingest is also fully high-confidence,
    the legacy 'don't downgrade' rule should still preserve 'collected'.
    We mustn't over-tighten and lose the legitimate inheritance path."""
    from eidp.db.models import SchoolYearStatus

    with Session(engine) as session:
        school = _seed_school(session)

        doc1 = _seed_doc(session, school.id, url="https://x/c1.pdf",
                         tmp_path=tmp_path, file_hash="v" * 64, name="c1.pdf")
        ann_high = _annotation(dept_record=DepartmentRecord(
            name="CH学科", capacity=40, enrollment=35, graduates=30,
        ))
        with patch("eidp.pipeline.ingest.parse_pdf", return_value=ann_high):
            ingest_document(session, doc1, recorder=None)
        session.commit()

        # Second ingest: fewer departments listed but same one is
        # populated. annotation.departments has 1 item, valid_depts has
        # 1 item → full_recognition. yearly_review_pending == 0.
        # Expect 'collected' to persist via inheritance.
        doc2 = _seed_doc(session, school.id, url="https://x/c2.pdf",
                         tmp_path=tmp_path, file_hash="w" * 64, name="c2.pdf")
        with patch("eidp.pipeline.ingest.parse_pdf", return_value=ann_high):
            ingest_document(session, doc2, recorder=None)
        session.commit()

        sys_rows = (
            session.query(SchoolYearStatus)
            .order_by(SchoolYearStatus.revision)
            .all()
        )
        assert sys_rows[-1].is_current is True
        assert sys_rows[-1].status == "collected"


def test_compute_pdf_parse_breakdown_custom_required_fields():
    """SR path uses different required fields."""
    from eidp.extraction_confidence import compute_pdf_parse_breakdown

    breakdown = compute_pdf_parse_breakdown(
        {"annual_total": 100, "grand_total": 100, "enrollment": 100},
        prior_enrollment=90,
        required_fields=("annual_total", "grand_total"),
    )
    assert breakdown.f1_extraction == 1.0
    assert breakdown.f2_completeness == 1.0
    # ratio 100/90 = 1.11 in [0.5, 2.0] → F3 = 1.0
    assert breakdown.f3_yoy_sanity == 1.0

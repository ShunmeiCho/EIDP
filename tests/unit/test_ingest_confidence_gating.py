"""Sprint 8.6.b — pdf_parse confidence gating in pipeline.ingest."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.models import (
    DepartmentYearly,
    Document,
    School,
    SupportRecipient,
)
from eidp.db.sqlite_bootstrap import bootstrap_sqlite
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

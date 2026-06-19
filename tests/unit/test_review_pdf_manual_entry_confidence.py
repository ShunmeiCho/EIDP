"""Sprint 8.6.d.2 — 申請書PDF確認 confidence summary."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.models import (
    Department,
    DepartmentYearly,
    Document,
    School,
    SupportRecipient,
)
from eidp.db.sqlite_bootstrap import bootstrap_sqlite
from eidp.extraction_confidence import breakdown_to_json, build_breakdown
from eidp.review._pages.pdf_manual_entry import (
    DocConfidenceSummary,
    summarize_confidence_for_document,
)


@pytest.fixture()
def engine(tmp_path: Path):
    db_path = tmp_path / "conf.sqlite3"
    eng = create_engine(f"sqlite:///{db_path}", future=True)
    bootstrap_sqlite(eng)
    yield eng
    eng.dispose()


def _make_school(session: Session) -> School:
    s = School(
        prefecture="東京都", corporation_name="法人", school_name="A学校",
        school_type="専門学校", status="active",
    )
    session.add(s)
    session.flush()
    return s


def _make_doc(session: Session, school_id: int, *, file_hash: str) -> Document:
    doc = Document(
        school_id=school_id,
        source_url="https://example.com/x.pdf",
        file_hash=file_hash,
        pdf_type="target", content_type="text",
        ingest_status="review_pending",
        downloaded_at=datetime.now(UTC),
    )
    session.add(doc)
    session.flush()
    return doc


def _make_dy(session: Session, *, dept_id: int, doc_id: int, fy: int,
             revision: int, is_current: bool, breakdown_json: str | None) -> DepartmentYearly:
    dy = DepartmentYearly(
        department_id=dept_id,
        document_id=doc_id,
        fiscal_year=fy,
        revision=revision,
        is_current=is_current,
        capacity=40, enrollment=35, graduates=30,
        extraction_method="pdf_parse",
        extraction_confidence=0.9,
        confidence_breakdown=breakdown_json,
    )
    session.add(dy)
    return dy


# ---------------------------------------------------------------------------
# summarize_confidence_for_document
# ---------------------------------------------------------------------------


def test_summary_empty_when_no_rows(engine):
    with Session(engine) as session:
        school = _make_school(session)
        doc = _make_doc(session, school.id, file_hash="0" * 64)
        session.commit()
        summary = summarize_confidence_for_document(session, doc.id)

    assert isinstance(summary, DocConfidenceSummary)
    assert summary.rows == []
    assert summary.worst_verdict is None
    assert "信頼度情報なし" in summary.summary_line


def test_summary_collects_every_dy_row(engine):
    with Session(engine) as session:
        school = _make_school(session)
        doc = _make_doc(session, school.id, file_hash="1" * 64)
        dept_a = Department(school_id=school.id, canonical_name="A学科")
        dept_b = Department(school_id=school.id, canonical_name="B学科")
        session.add_all([dept_a, dept_b])
        session.flush()

        # One auto, one review_pending.
        auto_blob = breakdown_to_json(
            build_breakdown(f1=1.0, f2=1.0, f3=1.0, method="pdf_parse"),
        )
        review_blob = breakdown_to_json(
            build_breakdown(f1=0.5, f2=0.5, f3=0.7, method="pdf_parse"),
        )
        _make_dy(session, dept_id=dept_a.id, doc_id=doc.id, fy=2026,
                 revision=1, is_current=True, breakdown_json=auto_blob)
        _make_dy(session, dept_id=dept_b.id, doc_id=doc.id, fy=2026,
                 revision=1, is_current=False, breakdown_json=review_blob)
        session.commit()

        summary = summarize_confidence_for_document(session, doc.id)

    assert len(summary.rows) == 2
    verdicts = {r.panel.verdict for r in summary.rows}
    assert verdicts == {"auto", "review_pending"}


def test_summary_worst_verdict_priority(engine):
    """Worst verdict ordering: rejected > review_pending > auto_flag > auto.
    A document with one auto and one review_pending must surface
    review_pending in worst_verdict."""
    with Session(engine) as session:
        school = _make_school(session)
        doc = _make_doc(session, school.id, file_hash="2" * 64)
        dept_a = Department(school_id=school.id, canonical_name="HiA")
        dept_b = Department(school_id=school.id, canonical_name="LoB")
        session.add_all([dept_a, dept_b])
        session.flush()
        _make_dy(session, dept_id=dept_a.id, doc_id=doc.id, fy=2026, revision=1,
                 is_current=True,
                 breakdown_json=breakdown_to_json(
                     build_breakdown(f1=1.0, f2=1.0, f3=1.0, method="pdf_parse"),
                 ))
        _make_dy(session, dept_id=dept_b.id, doc_id=doc.id, fy=2026, revision=1,
                 is_current=False,
                 breakdown_json=breakdown_to_json(
                     build_breakdown(f1=0.5, f2=0.5, f3=0.7, method="pdf_parse"),
                 ))
        session.commit()

        summary = summarize_confidence_for_document(session, doc.id)

    assert summary.worst_verdict == "review_pending"


def test_summary_worst_verdict_is_rejected_when_present(engine):
    with Session(engine) as session:
        school = _make_school(session)
        doc = _make_doc(session, school.id, file_hash="3" * 64)
        dept_a = Department(school_id=school.id, canonical_name="A")
        dept_b = Department(school_id=school.id, canonical_name="B")
        session.add_all([dept_a, dept_b])
        session.flush()
        _make_dy(session, dept_id=dept_a.id, doc_id=doc.id, fy=2026, revision=1,
                 is_current=True,
                 breakdown_json=breakdown_to_json(
                     build_breakdown(f1=1.0, f2=1.0, f3=1.0, method="pdf_parse"),
                 ))
        _make_dy(session, dept_id=dept_b.id, doc_id=doc.id, fy=2026, revision=1,
                 is_current=False,
                 breakdown_json=breakdown_to_json(
                     build_breakdown(f1=0.0, f2=0.0, f3=0.0, method="pdf_parse"),
                 ))
        session.commit()
        summary = summarize_confidence_for_document(session, doc.id)
    assert summary.worst_verdict == "rejected"


def test_summary_includes_support_recipient_rows(engine):
    with Session(engine) as session:
        school = _make_school(session)
        doc = _make_doc(session, school.id, file_hash="4" * 64)
        sr_blob = breakdown_to_json(
            build_breakdown(f1=1.0, f2=1.0, f3=1.0, method="pdf_parse"),
        )
        sr = SupportRecipient(
            school_id=school.id,
            document_id=doc.id,
            fiscal_year=2026,
            revision=1, is_current=True,
            annual_total=100, grand_total=100,
            extraction_confidence=0.9,
            confidence_breakdown=sr_blob,
        )
        session.add(sr)
        session.commit()
        summary = summarize_confidence_for_document(session, doc.id)

    kinds = [r.kind for r in summary.rows]
    assert "support_recipient" in kinds
    sr_panel = next(r for r in summary.rows if r.kind == "support_recipient")
    assert "対象比率" in sr_panel.label


def test_summary_skips_legacy_rows_without_breakdown(engine):
    """Pre-8.6.b rows have confidence_breakdown=None. They must be
    silently skipped — the summary surfaces "(信頼度情報なし)" for an
    all-legacy document, but does not crash."""
    with Session(engine) as session:
        school = _make_school(session)
        doc = _make_doc(session, school.id, file_hash="5" * 64)
        dept = Department(school_id=school.id, canonical_name="L")
        session.add(dept)
        session.flush()
        _make_dy(session, dept_id=dept.id, doc_id=doc.id, fy=2025, revision=1,
                 is_current=True, breakdown_json=None)
        session.commit()
        summary = summarize_confidence_for_document(session, doc.id)

    assert summary.rows == []
    assert summary.worst_verdict is None


def test_summary_skips_malformed_breakdown_blob(engine):
    """A bad blob must not poison the queue — skip the row, render the
    rest. We catch the parse error rather than letting it crash the
    page for one bad document."""
    with Session(engine) as session:
        school = _make_school(session)
        doc = _make_doc(session, school.id, file_hash="6" * 64)
        dept_good = Department(school_id=school.id, canonical_name="G")
        dept_bad = Department(school_id=school.id, canonical_name="B")
        session.add_all([dept_good, dept_bad])
        session.flush()
        _make_dy(session, dept_id=dept_good.id, doc_id=doc.id, fy=2026,
                 revision=1, is_current=True,
                 breakdown_json=breakdown_to_json(
                     build_breakdown(f1=1.0, f2=1.0, f3=1.0, method="pdf_parse"),
                 ))
        _make_dy(session, dept_id=dept_bad.id, doc_id=doc.id, fy=2026,
                 revision=1, is_current=False,
                 breakdown_json="not-json{")
        session.commit()
        summary = summarize_confidence_for_document(session, doc.id)

    # One good row survived; the malformed one was dropped.
    assert len(summary.rows) == 1
    assert summary.rows[0].kind == "department"


def test_summary_line_indicates_review_count(engine):
    with Session(engine) as session:
        school = _make_school(session)
        doc = _make_doc(session, school.id, file_hash="7" * 64)
        dept_a = Department(school_id=school.id, canonical_name="A")
        dept_b = Department(school_id=school.id, canonical_name="B")
        dept_c = Department(school_id=school.id, canonical_name="C")
        session.add_all([dept_a, dept_b, dept_c])
        session.flush()
        # 1 auto + 2 review_pending → "要レビュー 2/3"
        auto_blob = breakdown_to_json(
            build_breakdown(f1=1.0, f2=1.0, f3=1.0, method="pdf_parse"),
        )
        review_blob = breakdown_to_json(
            build_breakdown(f1=0.5, f2=0.5, f3=0.7, method="pdf_parse"),
        )
        _make_dy(session, dept_id=dept_a.id, doc_id=doc.id, fy=2026, revision=1,
                 is_current=True, breakdown_json=auto_blob)
        _make_dy(session, dept_id=dept_b.id, doc_id=doc.id, fy=2026, revision=1,
                 is_current=False, breakdown_json=review_blob)
        _make_dy(session, dept_id=dept_c.id, doc_id=doc.id, fy=2026, revision=1,
                 is_current=False, breakdown_json=review_blob)
        session.commit()
        summary = summarize_confidence_for_document(session, doc.id)

    assert "要レビュー 2/3" in summary.summary_line
    assert summary.worst_verdict == "review_pending"


def test_summary_line_for_all_auto_says_total_count(engine):
    """When everything is auto, the summary still tells the operator
    how many rows landed so they can sanity-check the count."""
    with Session(engine) as session:
        school = _make_school(session)
        doc = _make_doc(session, school.id, file_hash="8" * 64)
        dept = Department(school_id=school.id, canonical_name="A")
        session.add(dept)
        session.flush()
        _make_dy(session, dept_id=dept.id, doc_id=doc.id, fy=2026, revision=1,
                 is_current=True,
                 breakdown_json=breakdown_to_json(
                     build_breakdown(f1=1.0, f2=1.0, f3=1.0, method="pdf_parse"),
                 ))
        session.commit()
        summary = summarize_confidence_for_document(session, doc.id)

    assert "全1件" in summary.summary_line
    assert summary.worst_verdict == "auto"

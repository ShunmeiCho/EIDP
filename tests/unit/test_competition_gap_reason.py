from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.models import (
    Base,
    Department,
    DepartmentYearly,
    Document,
    School,
)
from eidp.excel.competition_exporter import (
    MatchResult,
    TemplateRow,
    _diagnose_gap,
)


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _template_row(school_name: str = "東京X", dept_name: str | None = "X科") -> TemplateRow:
    return TemplateRow(
        row_index=1,
        school_name=school_name,
        dept_name=dept_name,
        duration_label="2年制",
    )


def _match(school_id: int | None, dept_ids: list[int] | None = None) -> MatchResult:
    return MatchResult(
        template_row=_template_row(),
        sheet_name="ゲーム",
        school_id=school_id,
        department_ids=dept_ids or [],
        matched_via="exact" if school_id else "unmatched",
    )


def test_school_missing_when_school_id_is_none() -> None:
    session = _session()
    reason, _ = _diagnose_gap(session, _match(None), 2026)
    assert reason == "school_missing"


def test_school_no_document_when_school_has_no_docs() -> None:
    session = _session()
    session.add(School(id=1, prefecture="東京", corporation_name="C", school_name="X"))
    session.flush()
    reason, _ = _diagnose_gap(session, _match(1), 2026)
    assert reason == "school_no_document"


def test_school_mismatch_doc_rejected() -> None:
    session = _session()
    session.add(School(id=1, prefecture="東京", corporation_name="C", school_name="X"))
    session.add(Document(
        id=10, school_id=1,
        source_url="https://x.ac.jp/pdf/y.pdf",
        pdf_type="target",
        ingest_status="school_mismatch",
    ))
    session.flush()
    reason, detail = _diagnose_gap(session, _match(1), 2026)
    assert reason == "school_mismatch_doc_rejected"
    assert "x.ac.jp" in detail


def test_school_doc_old_year_only_when_fy_coverage_is_stale() -> None:
    session = _session()
    session.add(School(id=1, prefecture="東京", corporation_name="C", school_name="X"))
    session.add(Document(
        id=10, school_id=1,
        source_url="https://x.ac.jp/pdf/y.pdf",
        pdf_type="target",
        ingest_status="ingested",
        fiscal_year=2025,
    ))
    session.flush()
    reason, detail = _diagnose_gap(session, _match(1), 2026)
    assert reason == "school_doc_old_year_only"
    assert "2025" in detail


def test_dept_unmatched_when_school_fy_ok_but_no_dept_match() -> None:
    session = _session()
    session.add(School(id=1, prefecture="東京", corporation_name="C", school_name="X"))
    session.add(Department(id=5, school_id=1, canonical_name="他の科"))
    session.add(Document(
        id=10, school_id=1,
        source_url="u", pdf_type="target",
        ingest_status="ingested", fiscal_year=2026,
    ))
    session.flush()
    # dept_ids empty → dept_unmatched
    reason, detail = _diagnose_gap(session, _match(1, dept_ids=[]), 2026)
    assert reason == "dept_unmatched"
    assert "db_dept_count=1" in detail


def test_no_fy_data_when_dept_matched_but_yearly_missing() -> None:
    session = _session()
    session.add(School(id=1, prefecture="東京", corporation_name="C", school_name="X"))
    session.add(Department(id=5, school_id=1, canonical_name="X科"))
    session.add(Document(
        id=10, school_id=1,
        source_url="u", pdf_type="target",
        ingest_status="ingested", fiscal_year=2026,
    ))
    session.flush()
    reason, _ = _diagnose_gap(session, _match(1, dept_ids=[5]), 2026)
    assert reason == "no_fy_data"

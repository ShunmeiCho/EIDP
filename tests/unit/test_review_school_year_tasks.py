from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.models import Base, Document, School, SchoolFiscalYearStatus, SchoolSite
from eidp.review._pages.school_year_tasks import (
    list_school_year_tasks,
    next_action_for_status,
    school_task_summary,
)


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _school(session: Session, school_id: int, *, name: str, pref: str = "東京") -> School:
    school = School(
        id=school_id,
        school_code=f"S{school_id}",
        prefecture=pref,
        corporation_name=f"法人{school_id}",
        school_name=name,
        school_type="専門学校",
        status="active",
    )
    session.add(school)
    return school


def _status(
    session: Session,
    school_id: int,
    *,
    fiscal_year: int = 2026,
    url_status: str = "pref_url",
    pdf_status: str = "none",
    extract_status: str = "none",
    excel_ready: bool = False,
    blocking_reason: str | None = "no_target_pdf",
    evidence_level: str = "none",
) -> SchoolFiscalYearStatus:
    row = SchoolFiscalYearStatus(
        school_id=school_id,
        fiscal_year=fiscal_year,
        url_status=url_status,
        pdf_status=pdf_status,
        extract_status=extract_status,
        yoy_diff_status="unchecked",
        excel_ready=excel_ready,
        blocking_reason=blocking_reason,
        evidence_level=evidence_level,
    )
    session.add(row)
    return row


def _site(session: Session, school_id: int, url: str) -> None:
    session.add(
        SchoolSite(
            school_id=school_id,
            url=url,
            discovery_method="prefecture_aggregator",
            http_status=200,
        )
    )


def _doc(
    session: Session,
    doc_id: int,
    school_id: int,
    *,
    fy: int,
    status: str = "ingested",
) -> None:
    session.add(
        Document(
            id=doc_id,
            school_id=school_id,
            source_url=f"https://school{school_id}.example/{doc_id}.pdf",
            file_hash=f"{doc_id:064x}"[-64:],
            fiscal_year=fy,
            pdf_type="target",
            ingest_status=status,
        )
    )


def test_school_task_summary_groups_operator_counts() -> None:
    session = _session()
    try:
        for school_id in range(1, 5):
            _school(session, school_id, name=f"学校{school_id}")
        _status(
            session,
            1,
            pdf_status="confirmed_target",
            extract_status="parsed",
            excel_ready=True,
            blocking_reason=None,
            evidence_level="pdf_text",
        )
        _status(session, 2, pdf_status="rejected_stale", blocking_reason="stale_pdf_only")
        _status(session, 3, url_status="no_url", blocking_reason="no_url")
        _status(session, 4, pdf_status="image_pending", extract_status="ocr_pending", blocking_reason="ocr_pending")
        _school(session, 5, name="学校5")
        _status(
            session,
            5,
            pdf_status="confirmed_target",
            extract_status="parsed",
            blocking_reason="dept_change_review",
        )
        session.commit()

        summary = school_task_summary(session, fiscal_year=2026, school_type="専門学校")

        assert summary.total == 5
        assert summary.excel_ready == 1
        assert summary.needs_action == 4
        assert summary.confirmed_target == 2
        assert summary.stale_fallback == 1
        assert summary.no_url == 1
        assert summary.review_or_parse == 1
        assert summary.dept_change_review == 1
    finally:
        session.close()


def test_list_school_year_tasks_defaults_to_actionable_rows_and_enriches_latest_context() -> None:
    session = _session()
    try:
        _school(session, 1, name="出力可学校")
        _school(session, 2, name="旧年度学校")
        _school(session, 3, name="URLなし学校")
        _status(
            session,
            1,
            pdf_status="confirmed_target",
            extract_status="parsed",
            excel_ready=True,
            blocking_reason=None,
            evidence_level="pdf_text",
        )
        _status(session, 2, pdf_status="rejected_stale", blocking_reason="stale_pdf_only")
        _status(session, 3, url_status="no_url", blocking_reason="no_url")
        _site(session, 2, "https://school2.example/info")
        _doc(session, 20, 2, fy=2025)
        _doc(session, 21, 2, fy=2024)
        session.commit()

        rows = list_school_year_tasks(session, fiscal_year=2026, school_type="専門学校")

        assert [row.school_id for row in rows] == [3, 2]
        by_id = {row.school_id: row for row in rows}
        assert by_id[3].next_action == "URL追加"
        assert by_id[2].next_action == "公示待ち/再取得"
        assert by_id[2].latest_site_url == "https://school2.example/info"
        assert by_id[2].latest_document_id == 21
        assert by_id[2].latest_document_fiscal_year == 2024
    finally:
        session.close()


def test_list_school_year_tasks_filters_scope_reason_prefecture_and_search() -> None:
    session = _session()
    try:
        _school(session, 1, name="東京Ready", pref="東京")
        _school(session, 2, name="大阪Stale", pref="大阪")
        _school(session, 3, name="東京Missing", pref="東京")
        _status(
            session,
            1,
            pdf_status="confirmed_target",
            extract_status="parsed",
            excel_ready=True,
            blocking_reason=None,
            evidence_level="pdf_text",
        )
        _status(session, 2, pdf_status="rejected_stale", blocking_reason="stale_pdf_only")
        _status(session, 3, blocking_reason="no_target_pdf")
        session.commit()

        ready = list_school_year_tasks(session, fiscal_year=2026, scope="excel_ready")
        stale = list_school_year_tasks(session, fiscal_year=2026, blocking_reason="stale_pdf_only")
        tokyo = list_school_year_tasks(session, fiscal_year=2026, scope="all", prefecture="東京")
        searched = list_school_year_tasks(session, fiscal_year=2026, scope="all", search="Missing")

        assert [row.school_id for row in ready] == [1]
        assert [row.school_id for row in stale] == [2]
        assert {row.school_id for row in tokyo} == {1, 3}
        assert [row.school_id for row in searched] == [3]
    finally:
        session.close()


def test_next_action_labels_are_operator_tasks() -> None:
    session = _session()
    try:
        _school(session, 1, name="学校")
        row = _status(session, 1, blocking_reason="parse_failed")
        action, hint = next_action_for_status(row)
        assert action == "手入力"
        assert "PDF" in hint

        row.excel_ready = True
        row.blocking_reason = None
        action, hint = next_action_for_status(row)
        assert action == "Excel出力可"
        assert "Excel" in hint
    finally:
        session.close()


def test_next_action_surfaces_identical_previous_year_review() -> None:
    session = _session()
    try:
        _school(session, 1, name="学校")
        row = _status(
            session,
            1,
            pdf_status="confirmed_target",
            extract_status="parsed",
            blocking_reason="review_required",
            evidence_level="pdf_text",
        )
        row.yoy_diff_status = "identical_to_prev_fy"

        action, hint = next_action_for_status(row)

        assert action == "前年差分確認"
        assert "前年" in hint
    finally:
        session.close()


def test_next_action_surfaces_department_change_review() -> None:
    session = _session()
    try:
        _school(session, 1, name="学校")
        row = _status(
            session,
            1,
            pdf_status="confirmed_target",
            extract_status="parsed",
            blocking_reason="dept_change_review",
            evidence_level="pdf_text",
        )

        action, hint = next_action_for_status(row)

        assert action == "学科変更確認"
        assert "名称変更" in hint
    finally:
        session.close()

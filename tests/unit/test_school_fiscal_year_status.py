from __future__ import annotations

import json

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.models import (
    Base,
    Department,
    DepartmentChange,
    DepartmentYearly,
    Document,
    School,
    SchoolFiscalYearStatus,
    SchoolSite,
)
from eidp.pipeline.school_fiscal_year_status import (
    rebuild_school_fiscal_year_status,
    school_fiscal_year_status_counts,
)


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _school(session: Session, school_id: int, school_type: str = "専門学校") -> School:
    school = School(
        id=school_id,
        school_code=f"S{school_id}",
        prefecture="東京",
        corporation_name=f"法人{school_id}",
        school_name=f"学校{school_id}",
        school_type=school_type,
        status="active",
    )
    session.add(school)
    return school


def test_rebuild_creates_one_target_year_row_per_active_school() -> None:
    session = _session()
    try:
        _school(session, 1)
        _school(session, 2)
        _school(session, 3)
        _school(session, 4, "大学")
        session.add_all(
            [
                SchoolSite(
                    school_id=1,
                    url="https://s1.example/disclosure",
                    discovery_method="prefecture_aggregator",
                    http_status=200,
                ),
                SchoolSite(
                    school_id=2,
                    url="https://s2.example/disclosure",
                    discovery_method="school_site",
                    http_status=200,
                ),
            ]
        )
        current_doc = Document(
            id=1,
            school_id=1,
            source_url="https://s1.example/fy2026.pdf",
            file_hash="a" * 64,
            fiscal_year=2026,
            pdf_type="target",
            ingest_status="ingested",
        )
        stale_doc = Document(
            id=2,
            school_id=2,
            source_url="https://s2.example/fy2025.pdf",
            file_hash="b" * 64,
            fiscal_year=2025,
            pdf_type="target",
            ingest_status="ingested",
        )
        session.add_all([current_doc, stale_doc])
        dept = Department(
            id=1,
            school_id=1,
            canonical_name="情報学科",
        )
        session.add(dept)
        session.add(
            DepartmentYearly(
                department_id=1,
                document_id=1,
                fiscal_year=2026,
                revision=1,
                is_current=True,
                capacity=40,
                enrollment=38,
            )
        )
        session.commit()

        stats = rebuild_school_fiscal_year_status(
            session,
            fiscal_year=2026,
            school_type="専門学校",
        )
        session.commit()

        assert stats.rebuilt == 3
        assert stats.excel_ready == 1
        ready = session.get(SchoolFiscalYearStatus, (1, 2026))
        stale = session.get(SchoolFiscalYearStatus, (2, 2026))
        missing = session.get(SchoolFiscalYearStatus, (3, 2026))
        university = session.get(SchoolFiscalYearStatus, (4, 2026))
        assert ready is not None
        assert ready.url_status == "pref_url"
        assert ready.pdf_status == "confirmed_target"
        assert ready.extract_status == "parsed"
        assert ready.evidence_level == "pdf_text"
        assert ready.excel_ready is True
        assert ready.blocking_reason is None
        assert stale is not None
        assert stale.pdf_status == "rejected_stale"
        assert stale.excel_ready is False
        assert stale.blocking_reason == "stale_pdf_only"
        assert missing is not None
        assert missing.url_status == "no_url"
        assert missing.blocking_reason == "no_url"
        assert university is None

        counts = school_fiscal_year_status_counts(
            session,
            fiscal_year=2026,
            school_type="専門学校",
        )
        assert counts == {
            "total": 3,
            "confirmed_target": 1,
            "stale_or_old": 1,
            "review_or_parse": 0,
            "excel_ready": 1,
        }
    finally:
        session.close()


def test_rebuild_marks_stale_pdf_text_as_conflict_even_with_target_year_url_hint() -> None:
    session = _session()
    try:
        _school(session, 1)
        session.add(
            SchoolSite(
                school_id=1,
                url="https://s1.example/disclosure",
                discovery_method="prefecture_aggregator",
                http_status=200,
            )
        )
        session.add(
            Document(
                id=1,
                school_id=1,
                source_url="https://s1.example/2026/application.pdf",
                file_hash="c" * 64,
                fiscal_year=2025,
                pdf_type="target",
                ingest_status="ingested",
            )
        )
        session.commit()

        rebuild_school_fiscal_year_status(
            session,
            fiscal_year=2026,
            school_type="専門学校",
        )
        session.commit()

        row = session.get(SchoolFiscalYearStatus, (1, 2026))
        assert row is not None
        assert row.pdf_status == "rejected_stale"
        assert row.evidence_level == "conflict"
        assert row.excel_ready is False
        assert row.blocking_reason == "stale_pdf_only"
    finally:
        session.close()


def test_rebuild_accepts_operator_override_as_excel_ready_evidence() -> None:
    session = _session()
    try:
        _school(session, 1)
        doc = Document(
            id=1,
            school_id=1,
            source_url="https://s1.example/r7/application.pdf",
            file_hash="d" * 64,
            fiscal_year=2026,
            fiscal_year_override=2026,
            pdf_type="target",
            ingest_status="ingested",
        )
        session.add(doc)
        dept = Department(id=1, school_id=1, canonical_name="情報学科")
        session.add(dept)
        session.add(
            DepartmentYearly(
                department_id=1,
                document_id=1,
                fiscal_year=2026,
                revision=1,
                is_current=True,
                capacity=40,
                enrollment=38,
            )
        )
        session.commit()

        rebuild_school_fiscal_year_status(
            session,
            fiscal_year=2026,
            school_type="専門学校",
        )
        session.commit()

        row = session.get(SchoolFiscalYearStatus, (1, 2026))
        assert row is not None
        assert row.evidence_level == "operator_override"
        assert row.excel_ready is True
    finally:
        session.close()


def test_rebuild_marks_identical_previous_year_values_not_excel_ready() -> None:
    session = _session()
    try:
        _school(session, 1)
        doc = Document(
            id=1,
            school_id=1,
            source_url="https://s1.example/fy2026.pdf",
            file_hash="e" * 64,
            fiscal_year=2026,
            pdf_type="target",
            ingest_status="ingested",
        )
        session.add(doc)
        dept = Department(id=1, school_id=1, canonical_name="情報学科")
        session.add(dept)
        for row_id, fy in ((1, 2025), (2, 2026)):
            session.add(
                DepartmentYearly(
                    id=row_id,
                    department_id=1,
                    document_id=1 if fy == 2026 else None,
                    fiscal_year=fy,
                    revision=1,
                    is_current=True,
                    capacity=40,
                    enrollment=38,
                    intl_students=3,
                )
            )
        session.commit()

        rebuild_school_fiscal_year_status(
            session,
            fiscal_year=2026,
            school_type="専門学校",
        )
        session.commit()

        row = session.get(SchoolFiscalYearStatus, (1, 2026))
        assert row is not None
        assert row.yoy_diff_status == "identical_to_prev_fy"
        assert row.evidence_level == "pdf_text"
        assert row.excel_ready is False
        assert row.blocking_reason == "review_required"
    finally:
        session.close()


def test_rebuild_marks_previous_year_numeric_diff_as_prev_year_evidence() -> None:
    session = _session()
    try:
        _school(session, 1)
        doc = Document(
            id=1,
            school_id=1,
            source_url="https://s1.example/fy2026.pdf",
            file_hash="f" * 64,
            fiscal_year=2026,
            pdf_type="target",
            ingest_status="ingested",
        )
        session.add(doc)
        dept = Department(id=1, school_id=1, canonical_name="情報学科")
        session.add(dept)
        session.add_all(
            [
                DepartmentYearly(
                    id=1,
                    department_id=1,
                    fiscal_year=2025,
                    revision=1,
                    is_current=True,
                    capacity=40,
                    enrollment=38,
                ),
                DepartmentYearly(
                    id=2,
                    department_id=1,
                    document_id=1,
                    fiscal_year=2026,
                    revision=1,
                    is_current=True,
                    capacity=40,
                    enrollment=41,
                ),
            ]
        )
        session.commit()

        rebuild_school_fiscal_year_status(
            session,
            fiscal_year=2026,
            school_type="専門学校",
        )
        session.commit()

        row = session.get(SchoolFiscalYearStatus, (1, 2026))
        assert row is not None
        assert row.yoy_diff_status == "partial_diff"
        assert row.evidence_level == "prev_year_diff"
        assert row.excel_ready is True
    finally:
        session.close()


def test_rebuild_does_not_upgrade_conflicting_stale_pdf_with_previous_year_diff() -> None:
    session = _session()
    try:
        _school(session, 1)
        session.add(
            Document(
                id=1,
                school_id=1,
                source_url="https://s1.example/2026/application.pdf",
                file_hash="g" * 64,
                fiscal_year=2025,
                pdf_type="target",
                ingest_status="ingested",
            )
        )
        dept = Department(id=1, school_id=1, canonical_name="情報学科")
        session.add(dept)
        session.add_all(
            [
                DepartmentYearly(
                    id=1,
                    department_id=1,
                    fiscal_year=2025,
                    revision=1,
                    is_current=True,
                    capacity=40,
                    enrollment=38,
                ),
                DepartmentYearly(
                    id=2,
                    department_id=1,
                    fiscal_year=2026,
                    revision=1,
                    is_current=True,
                    capacity=40,
                    enrollment=41,
                ),
            ]
        )
        session.commit()

        rebuild_school_fiscal_year_status(
            session,
            fiscal_year=2026,
            school_type="専門学校",
        )
        session.commit()

        row = session.get(SchoolFiscalYearStatus, (1, 2026))
        assert row is not None
        assert row.pdf_status == "rejected_stale"
        assert row.yoy_diff_status == "partial_diff"
        assert row.evidence_level == "conflict"
        assert row.excel_ready is False
    finally:
        session.close()


def test_rebuild_blocks_excel_ready_when_department_change_is_unverified() -> None:
    session = _session()
    try:
        _school(session, 1)
        doc = Document(
            id=1,
            school_id=1,
            source_url="https://s1.example/fy2026.pdf",
            file_hash="h" * 64,
            fiscal_year=2026,
            pdf_type="target",
            ingest_status="ingested",
        )
        session.add(doc)
        dept = Department(id=1, school_id=1, canonical_name="情報学科")
        session.add(dept)
        session.add(
            DepartmentYearly(
                id=1,
                department_id=1,
                document_id=1,
                fiscal_year=2026,
                revision=1,
                is_current=True,
                capacity=40,
                enrollment=38,
            )
        )
        session.add(
            DepartmentChange(
                department_id=1,
                change_type="名称変更",
                fiscal_year=2026,
                old_name="旧情報学科",
                new_name="情報学科",
                verified=False,
            )
        )
        session.commit()

        rebuild_school_fiscal_year_status(
            session,
            fiscal_year=2026,
            school_type="専門学校",
        )
        session.commit()

        row = session.get(SchoolFiscalYearStatus, (1, 2026))
        assert row is not None
        assert row.pdf_status == "confirmed_target"
        assert row.extract_status == "parsed"
        assert row.excel_ready is False
        assert row.blocking_reason == "dept_change_review"
    finally:
        session.close()


def test_rebuild_marks_publication_lag_evidence_as_review_state(tmp_path) -> None:
    session = _session()
    try:
        _school(session, 1)
        session.add(
            SchoolSite(
                school_id=1,
                url="https://s1.example/disclosure",
                discovery_method="prefecture_aggregator",
                http_status=200,
            )
        )
        evidence_path = tmp_path / "discovery.jsonl"
        evidence_path.write_text(
            json.dumps(
                {
                    "school_id": 1,
                    "reason": "fiscal_year_mismatch:2025",
                    "pdf_type": "target",
                    "pdf_url": "https://s1.example/r7/application.pdf",
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        session.commit()

        rebuild_school_fiscal_year_status(
            session,
            fiscal_year=2026,
            school_type="専門学校",
            discovery_evidence_path=evidence_path,
        )
        session.commit()

        row = session.get(SchoolFiscalYearStatus, (1, 2026))
        assert row is not None
        assert row.url_status == "pref_url"
        assert row.pdf_status == "publication_lag"
        assert row.extract_status == "none"
        assert row.evidence_level == "publication_lag"
        assert row.excel_ready is False
        assert row.blocking_reason == "publication_lag_latest_public"

        counts = school_fiscal_year_status_counts(
            session,
            fiscal_year=2026,
            school_type="専門学校",
        )
        assert counts["stale_or_old"] == 1
        assert counts["excel_ready"] == 0
    finally:
        session.close()

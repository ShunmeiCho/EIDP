from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.models import Base, Department, DepartmentYearly, Document, School, SchoolSite

script = Path(__file__).resolve().parents[2] / "scripts" / "run_r8_rediscovery_weekly.py"
spec = importlib.util.spec_from_file_location("run_r8_rediscovery_weekly", script)
assert spec is not None
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["run_r8_rediscovery_weekly"] = module
spec.loader.exec_module(module)

select_stale_school_ids = module.select_stale_school_ids
snapshot_reports = module._snapshot_reports


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _school(session: Session, school_id: int, school_type: str = "専門学校") -> None:
    session.add(
        School(
            id=school_id,
            prefecture="東京",
            corporation_name=f"C{school_id}",
            school_name=f"S{school_id}",
            school_type=school_type,
            status="active",
        )
    )


def _site(session: Session, school_id: int, method: str, http_status: int | None = 200) -> None:
    session.add(
        SchoolSite(
            school_id=school_id,
            url=f"https://example{school_id}.ac.jp/disclosure/",
            discovery_method=method,
            http_status=http_status,
        )
    )


def _doc(
    session: Session,
    doc_id: int,
    school_id: int,
    fy: int,
    *,
    pdf_type: str = "target",
    ingest_status: str = "ingested",
) -> None:
    session.add(
        Document(
            id=doc_id,
            school_id=school_id,
            source_url=f"https://example{school_id}.ac.jp/{doc_id}.pdf",
            fiscal_year=fy,
            pdf_type=pdf_type,
            ingest_status=ingest_status,
        )
    )


def test_select_stale_school_ids_filters_to_current_work_queue() -> None:
    session = _session()
    try:
        _school(session, 1)
        _site(session, 1, "prefecture_aggregator")
        _doc(session, 10, 1, 2025)

        _school(session, 2)
        _site(session, 2, "prefecture_aggregator")
        _doc(session, 20, 2, 2026)

        _school(session, 3)
        _site(session, 3, "prefecture_aggregator")

        _school(session, 4, "大学")
        _site(session, 4, "prefecture_aggregator")
        _doc(session, 40, 4, 2025)

        _school(session, 5)
        _site(session, 5, "web_search")
        _doc(session, 50, 5, 2025)

        _school(session, 6)
        _site(session, 6, "prefecture_aggregator", http_status=404)
        _doc(session, 60, 6, 2025)
        session.flush()

        ids = select_stale_school_ids(
            session,
            current_fy=2026,
            methods=["prefecture_aggregator"],
            school_type="専門学校",
        )

        assert ids == [1]
    finally:
        session.close()


def test_select_stale_school_ids_can_include_all_methods_and_limit() -> None:
    session = _session()
    try:
        for school_id in (1, 2, 3):
            _school(session, school_id)
            _doc(session, school_id, school_id, 2025)
        _site(session, 1, "web_search")
        _site(session, 2, "prefecture_aggregator")
        _site(session, 3, "corporation_pattern")
        session.flush()

        ids = select_stale_school_ids(
            session,
            current_fy=2026,
            methods=None,
            school_type="専門学校",
            limit=2,
        )

        assert ids == [1, 2]
    finally:
        session.close()


def test_snapshot_reports_preserves_target_vs_any_current_fy_distinction() -> None:
    session = _session()
    try:
        _school(session, 1)
        _doc(session, 10, 1, 2026, pdf_type="image_only", ingest_status="ingested")
        session.add(Department(id=100, school_id=1, canonical_name="歯科衛生士科"))
        session.add(
            DepartmentYearly(
                department_id=100,
                document_id=10,
                fiscal_year=2026,
                revision=1,
                is_current=True,
                capacity=80,
                enrollment=70,
            )
        )
        session.flush()

        snapshot = snapshot_reports(session, 2026, "専門学校")

        assert snapshot["coverage"]["schools_with_target_pdf_current_fy"] == 0
        assert snapshot["coverage"]["schools_with_current_fy_doc"] == 1
        assert snapshot["extraction"]["documents_ingested"] == 1
        assert snapshot["extraction"]["yearly_rows_total"] == 1
    finally:
        session.close()

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.models import Base, Document, School, SchoolSite
from eidp.review.target_year_status import target_year_overview


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


def _doc(
    session: Session,
    doc_id: int,
    school_id: int,
    fy: int | None,
    *,
    status: str = "ingested",
    pdf_type: str = "target",
) -> None:
    session.add(
        Document(
            id=doc_id,
            school_id=school_id,
            source_url=f"https://example{school_id}.ac.jp/{doc_id}.pdf",
            fiscal_year=fy,
            ingest_status=status,
            pdf_type=pdf_type,
        )
    )


def test_target_year_overview_surfaces_current_vs_stale_gap() -> None:
    session = _session()
    try:
        _school(session, 1)
        _school(session, 2)
        _school(session, 3)
        _school(session, 4, "大学")
        session.add(SchoolSite(school_id=1, url="https://s1", http_status=200))
        session.add(SchoolSite(school_id=2, url="https://s2", http_status=200))
        session.add(SchoolSite(school_id=3, url="https://s3", http_status=404))
        _doc(session, 10, 1, 2025)
        _doc(session, 11, 1, None, status="ocr_pending", pdf_type="image_only")
        _doc(session, 20, 2, 2026)
        _doc(session, 30, 3, 2024, status="parse_failed")
        _doc(session, 31, 3, 2027)
        _doc(session, 40, 4, 2026)
        session.flush()

        overview = target_year_overview(session, target_fiscal_year=2026, school_type="専門学校")

        assert overview.active_schools == 3
        assert overview.schools_with_site == 2
        assert overview.current_target_schools == 1
        assert overview.current_target_documents == 1
        assert overview.stale_target_documents == 1
        assert overview.stale_target_schools == 1
        assert overview.future_target_documents == 1
        assert overview.future_target_schools == 1
        assert overview.review_queue_documents == 2
        assert overview.missing_current_target_schools == 2

        all_overview = target_year_overview(session, target_fiscal_year=2026, school_type=None)

        assert all_overview.active_schools == 4
        assert all_overview.current_target_schools == 2
        assert all_overview.current_target_documents == 2
        assert all_overview.future_target_schools == 1
        assert all_overview.future_target_documents == 1
        assert all_overview.missing_current_target_schools == 2
    finally:
        session.close()

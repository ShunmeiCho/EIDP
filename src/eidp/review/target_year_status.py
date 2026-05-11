"""Target-fiscal-year status helpers for operator UI.

These helpers make the most important season question explicit:
"How many schools have the target-year PDF already, and how much of the DB is
only old-year fallback?"  They are pure query helpers so Streamlit pages can
render clear guidance without duplicating fragile SQL.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from eidp.db.models import Document, School, SchoolSite

REVIEW_QUEUE_STATUSES: tuple[str, ...] = (
    "ocr_pending",
    "parse_failed",
    "review_pending",
    "school_mismatch",
)


@dataclass(frozen=True)
class TargetYearOverview:
    target_fiscal_year: int
    school_type: str | None
    active_schools: int
    schools_with_site: int
    current_target_schools: int
    current_target_documents: int
    stale_target_schools: int
    stale_target_documents: int
    future_target_schools: int
    future_target_documents: int
    review_queue_documents: int

    @property
    def missing_current_target_schools(self) -> int:
        return max(self.active_schools - self.current_target_schools, 0)


def _active_school_ids(session: Session, school_type: str | None) -> list[int]:
    query = session.query(School.id).filter(School.status == "active")
    if school_type:
        query = query.filter(School.school_type == school_type)
    return [int(school_id) for (school_id,) in query.all()]


def target_year_overview(
    session: Session,
    *,
    target_fiscal_year: int,
    school_type: str | None = "専門学校",
) -> TargetYearOverview:
    """Return current-vs-stale PDF acquisition counters."""
    school_ids = _active_school_ids(session, school_type)
    if not school_ids:
        return TargetYearOverview(
            target_fiscal_year=target_fiscal_year,
            school_type=school_type,
            active_schools=0,
            schools_with_site=0,
            current_target_schools=0,
            current_target_documents=0,
            stale_target_schools=0,
            stale_target_documents=0,
            future_target_schools=0,
            future_target_documents=0,
            review_queue_documents=0,
        )

    schools_with_site = (
        session.query(func.count(func.distinct(SchoolSite.school_id)))
        .filter(
            SchoolSite.school_id.in_(school_ids),
            or_(SchoolSite.http_status == 200, SchoolSite.http_status.is_(None)),
        )
        .scalar()
        or 0
    )

    current_target_query = session.query(Document).filter(
        Document.school_id.in_(school_ids),
        Document.fiscal_year == target_fiscal_year,
        Document.pdf_type == "target",
        Document.ingest_status == "ingested",
    )
    current_target_documents = current_target_query.count()
    current_target_schools = (
        current_target_query.with_entities(func.count(func.distinct(Document.school_id))).scalar()
        or 0
    )

    stale_target_query = session.query(Document).filter(
        Document.school_id.in_(school_ids),
        Document.fiscal_year.is_not(None),
        Document.fiscal_year < target_fiscal_year,
        Document.pdf_type == "target",
        Document.ingest_status == "ingested",
    )
    stale_target_documents = stale_target_query.count()
    stale_target_schools = (
        stale_target_query.with_entities(func.count(func.distinct(Document.school_id))).scalar()
        or 0
    )

    future_target_query = session.query(Document).filter(
        Document.school_id.in_(school_ids),
        Document.fiscal_year.is_not(None),
        Document.fiscal_year > target_fiscal_year,
        Document.pdf_type == "target",
        Document.ingest_status == "ingested",
    )
    future_target_documents = future_target_query.count()
    future_target_schools = (
        future_target_query.with_entities(func.count(func.distinct(Document.school_id))).scalar()
        or 0
    )

    review_queue_documents = (
        session.query(func.count(Document.id))
        .filter(
            Document.school_id.in_(school_ids),
            Document.ingest_status.in_(REVIEW_QUEUE_STATUSES),
        )
        .scalar()
        or 0
    )

    return TargetYearOverview(
        target_fiscal_year=target_fiscal_year,
        school_type=school_type,
        active_schools=len(school_ids),
        schools_with_site=int(schools_with_site),
        current_target_schools=int(current_target_schools),
        current_target_documents=int(current_target_documents),
        stale_target_schools=int(stale_target_schools),
        stale_target_documents=int(stale_target_documents),
        future_target_schools=int(future_target_schools),
        future_target_documents=int(future_target_documents),
        review_queue_documents=int(review_queue_documents),
    )

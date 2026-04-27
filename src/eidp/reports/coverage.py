"""School / URL / PDF coverage report.

Acceptance criterion #1: 専門学校 PDF coverage by prefecture.
"""

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from eidp.db.models import Department, DepartmentYearly, Document, School, SchoolSite


def current_fiscal_year(now: datetime | None = None) -> int:
    """Japanese fiscal year — April-March. Apr 2026 → FY2026."""
    now = now or datetime.now()
    return now.year if now.month >= 4 else now.year - 1


@dataclass(frozen=True)
class PrefectureCoverage:
    prefecture: str
    schools_total: int
    schools_with_url: int
    schools_with_verified_url: int
    schools_with_any_pdf: int
    schools_with_current_fy_doc: int
    schools_with_current_fy_extracted: int

    @property
    def url_rate(self) -> float:
        return self.schools_with_url / self.schools_total if self.schools_total else 0.0

    @property
    def pdf_rate(self) -> float:
        return self.schools_with_any_pdf / self.schools_total if self.schools_total else 0.0

    @property
    def current_fy_rate(self) -> float:
        return (
            self.schools_with_current_fy_extracted / self.schools_total
            if self.schools_total
            else 0.0
        )


@dataclass(frozen=True)
class CoverageReport:
    fiscal_year: int
    school_type: str | None
    by_prefecture: tuple[PrefectureCoverage, ...]
    totals: PrefectureCoverage = field(default=None)  # type: ignore[assignment]


def compute_coverage(
    session: Session,
    school_type: str | None = "専門学校",
    fiscal_year: int | None = None,
) -> CoverageReport:
    """Build coverage report grouped by prefecture, plus an aggregate row."""
    fy = fiscal_year if fiscal_year is not None else current_fiscal_year()

    school_q = session.query(School).filter(School.status == "active")
    if school_type is not None:
        school_q = school_q.filter(School.school_type == school_type)

    schools = school_q.all()
    school_ids_by_pref: dict[str, list[int]] = {}
    for s in schools:
        school_ids_by_pref.setdefault(s.prefecture or "(unknown)", []).append(s.id)

    sites_subq = (
        session.query(SchoolSite.school_id, SchoolSite.verified).all()
    )
    sites_by_school: dict[int, list[bool]] = {}
    for sid, verified in sites_subq:
        sites_by_school.setdefault(sid, []).append(bool(verified))

    docs = (
        session.query(
            Document.school_id,
            Document.fiscal_year,
            Document.ingest_status,
        ).all()
    )
    docs_by_school: dict[int, list[tuple[int | None, str | None]]] = {}
    for sid, dfy, status in docs:
        docs_by_school.setdefault(sid, []).append((dfy, status))

    extracted_school_ids = {
        sid
        for (sid,) in (
            session.query(distinct(Department.school_id))
            .join(DepartmentYearly, DepartmentYearly.department_id == Department.id)
            .filter(
                DepartmentYearly.fiscal_year == fy,
                DepartmentYearly.is_current.is_(True),
                DepartmentYearly.capacity.isnot(None),
            )
            .all()
        )
    }

    rows: list[PrefectureCoverage] = []
    for pref, sids in sorted(school_ids_by_pref.items()):
        with_url = sum(1 for sid in sids if sid in sites_by_school)
        with_verified = sum(
            1 for sid in sids if any(sites_by_school.get(sid, []))
        )
        with_any_pdf = sum(1 for sid in sids if sid in docs_by_school)
        with_current_doc = sum(
            1
            for sid in sids
            if any(
                d_fy == fy and status == "ingested"
                for d_fy, status in docs_by_school.get(sid, [])
            )
        )
        with_extracted = sum(1 for sid in sids if sid in extracted_school_ids)
        rows.append(
            PrefectureCoverage(
                prefecture=pref,
                schools_total=len(sids),
                schools_with_url=with_url,
                schools_with_verified_url=with_verified,
                schools_with_any_pdf=with_any_pdf,
                schools_with_current_fy_doc=with_current_doc,
                schools_with_current_fy_extracted=with_extracted,
            )
        )

    totals = PrefectureCoverage(
        prefecture="__total__",
        schools_total=sum(r.schools_total for r in rows),
        schools_with_url=sum(r.schools_with_url for r in rows),
        schools_with_verified_url=sum(r.schools_with_verified_url for r in rows),
        schools_with_any_pdf=sum(r.schools_with_any_pdf for r in rows),
        schools_with_current_fy_doc=sum(r.schools_with_current_fy_doc for r in rows),
        schools_with_current_fy_extracted=sum(
            r.schools_with_current_fy_extracted for r in rows
        ),
    )

    return CoverageReport(
        fiscal_year=fy,
        school_type=school_type,
        by_prefecture=tuple(rows),
        totals=totals,
    )

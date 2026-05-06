"""School / URL / PDF coverage report.

Acceptance criterion #1: 専門学校 PDF coverage by prefecture.

Coverage uses three distinct denominators so we never confuse "any PDF
exists" with "the target document was successfully ingested":

- any_pdf              — any Document row exists for the school (including
                          stale, non-target, parse_failed, school_mismatch)
- target_pdf_any_fy    — at least one Document with pdf_type='target' AND
                          ingest_status='ingested', any fiscal year. This
                          is a "discovery health" indicator, NOT target-FY coverage.
- target_pdf_current_fy — same but fiscal_year=fy. **This is the target-FY
                           coverage metric.** Use this when reporting business
                           progress against the 70% goal.
- current_fy_doc       — Document with fiscal_year=fy AND ingest_status='ingested'
                          (regardless of pdf_type — useful for diagnosing
                          target-classification gaps).
- current_fy_extracted — DepartmentYearly row exists with capacity not null
                          for fy.
"""

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from eidp.db.models import Department, DepartmentYearly, Document, School, SchoolFiscalYearStatus, SchoolSite


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
    schools_with_target_pdf_any_fy: int
    schools_with_target_pdf_current_fy: int
    schools_with_current_fy_doc: int
    schools_with_current_fy_extracted: int

    @property
    def url_rate(self) -> float:
        return self.schools_with_url / self.schools_total if self.schools_total else 0.0

    @property
    def any_pdf_rate(self) -> float:
        return self.schools_with_any_pdf / self.schools_total if self.schools_total else 0.0

    @property
    def target_pdf_any_fy_rate(self) -> float:
        return (
            self.schools_with_target_pdf_any_fy / self.schools_total
            if self.schools_total
            else 0.0
        )

    @property
    def target_pdf_current_fy_rate(self) -> float:
        """The headline target-FY coverage metric."""
        return (
            self.schools_with_target_pdf_current_fy / self.schools_total
            if self.schools_total
            else 0.0
        )

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


@dataclass(frozen=True)
class ExportGapReport:
    """Target-FY readiness counters shown before any business Excel export."""

    fiscal_year: int
    school_type: str | None
    total_schools: int
    schools_with_url: int
    no_url_schools: int
    target_pdf_schools: int
    stale_fallback_schools: int
    missing_target_pdf_schools: int
    extracted_schools: int
    excel_ready_schools: int
    target_yearly_rows: int

    @property
    def target_pdf_rate(self) -> float:
        return self.target_pdf_schools / self.total_schools if self.total_schools else 0.0

    @property
    def extracted_rate(self) -> float:
        return self.extracted_schools / self.total_schools if self.total_schools else 0.0

    @property
    def excel_ready_rate(self) -> float:
        return self.excel_ready_schools / self.total_schools if self.total_schools else 0.0

    @property
    def has_target_year_data(self) -> bool:
        return self.target_yearly_rows > 0


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
            Document.pdf_type,
        ).all()
    )
    docs_by_school: dict[int, list[tuple[int | None, str | None, str | None]]] = {}
    for sid, dfy, status, pdf_type in docs:
        docs_by_school.setdefault(sid, []).append((dfy, status, pdf_type))

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
        with_target_any_fy = sum(
            1
            for sid in sids
            if any(
                pdf_type == "target" and status == "ingested"
                for _d_fy, status, pdf_type in docs_by_school.get(sid, [])
            )
        )
        with_target_current_fy = sum(
            1
            for sid in sids
            if any(
                pdf_type == "target" and status == "ingested" and d_fy == fy
                for d_fy, status, pdf_type in docs_by_school.get(sid, [])
            )
        )
        with_current_doc = sum(
            1
            for sid in sids
            if any(
                d_fy == fy and status == "ingested"
                for d_fy, status, _pdf_type in docs_by_school.get(sid, [])
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
                schools_with_target_pdf_any_fy=with_target_any_fy,
                schools_with_target_pdf_current_fy=with_target_current_fy,
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
        schools_with_target_pdf_any_fy=sum(
            r.schools_with_target_pdf_any_fy for r in rows
        ),
        schools_with_target_pdf_current_fy=sum(
            r.schools_with_target_pdf_current_fy for r in rows
        ),
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


def _active_school_ids(session: Session, school_type: str | None) -> list[int]:
    query = session.query(School.id).filter(School.status == "active")
    if school_type is not None:
        query = query.filter(School.school_type == school_type)
    return [int(school_id) for (school_id,) in query.all()]


def gap_report_for_export(
    session: Session,
    *,
    fiscal_year: int,
    school_type: str | None = "専門学校",
) -> ExportGapReport:
    """Return target-year readiness for operator-facing Excel export.

    This intentionally uses target fiscal-year rows only. Historical rows may
    stay in the workbook, but they must not make the current-year export look
    ready when the current-year PDFs have not been acquired.
    """
    coverage = compute_coverage(session, school_type=school_type, fiscal_year=fiscal_year).totals
    school_ids = _active_school_ids(session, school_type)
    if not school_ids:
        return ExportGapReport(
            fiscal_year=fiscal_year,
            school_type=school_type,
            total_schools=0,
            schools_with_url=0,
            no_url_schools=0,
            target_pdf_schools=0,
            stale_fallback_schools=0,
            missing_target_pdf_schools=0,
            extracted_schools=0,
            excel_ready_schools=0,
            target_yearly_rows=0,
        )

    current_target_pdf_school_ids = (
        session.query(Document.school_id)
        .filter(
            Document.school_id.in_(school_ids),
            Document.pdf_type == "target",
            Document.ingest_status == "ingested",
            Document.fiscal_year == fiscal_year,
        )
        .subquery()
    )

    stale_fallback_schools = (
        session.query(func.count(func.distinct(Document.school_id)))
        .filter(
            Document.school_id.in_(school_ids),
            Document.pdf_type == "target",
            Document.ingest_status == "ingested",
            Document.fiscal_year.is_not(None),
            Document.fiscal_year < fiscal_year,
            Document.school_id.not_in(session.query(current_target_pdf_school_ids.c.school_id)),
        )
        .scalar()
        or 0
    )

    excel_ready_schools = (
        session.query(func.count(SchoolFiscalYearStatus.school_id))
        .join(School, School.id == SchoolFiscalYearStatus.school_id)
        .filter(
            SchoolFiscalYearStatus.fiscal_year == fiscal_year,
            SchoolFiscalYearStatus.excel_ready.is_(True),
            School.status == "active",
        )
    )
    if school_type is not None:
        excel_ready_schools = excel_ready_schools.filter(School.school_type == school_type)
    excel_ready_count = int(excel_ready_schools.scalar() or 0)

    target_yearly_rows = (
        session.query(func.count(DepartmentYearly.id))
        .join(Department, Department.id == DepartmentYearly.department_id)
        .join(School, School.id == Department.school_id)
        .filter(
            DepartmentYearly.fiscal_year == fiscal_year,
            DepartmentYearly.is_current.is_(True),
            School.status == "active",
        )
    )
    if school_type is not None:
        target_yearly_rows = target_yearly_rows.filter(School.school_type == school_type)
    target_yearly_count = int(target_yearly_rows.scalar() or 0)

    total = int(coverage.schools_total)
    target_pdf = int(coverage.schools_with_target_pdf_current_fy)
    return ExportGapReport(
        fiscal_year=fiscal_year,
        school_type=school_type,
        total_schools=total,
        schools_with_url=int(coverage.schools_with_url),
        no_url_schools=max(total - int(coverage.schools_with_url), 0),
        target_pdf_schools=target_pdf,
        stale_fallback_schools=int(stale_fallback_schools),
        missing_target_pdf_schools=max(total - target_pdf, 0),
        extracted_schools=int(coverage.schools_with_current_fy_extracted),
        excel_ready_schools=excel_ready_count,
        target_yearly_rows=target_yearly_count,
    )

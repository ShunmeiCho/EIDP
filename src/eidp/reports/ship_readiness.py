"""Final-goal ship readiness report.

This report keeps the long-term product target separate from lower-level
package and unit-test gates. Strict target-FY PDF acquisition remains a
diagnostic metric; the release-blocking business line is operator-reviewable
coverage expressed as manual workload, plus Excel-ready target-FY data.
"""

from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Session

from eidp.config import settings
from eidp.db.models import School, SchoolFiscalYearStatus
from eidp.pipeline.school_fiscal_year_status import SHIP_REVIEWABLE_PDF_STATUSES
from eidp.reports.coverage import compute_coverage, gap_report_for_export


@dataclass(frozen=True)
class ShipReadinessCriterion:
    name: str
    value: float
    threshold: float
    passed: bool


@dataclass(frozen=True)
class ShipReadinessReport:
    fiscal_year: int
    school_type: str | None
    total_schools: int
    strict_target_pdf_schools: int
    strict_target_pdf_rate: float
    operator_reviewable_schools: int
    operator_reviewable_rate: float
    estimated_manual_workload_rate: float
    excel_ready_schools: int
    excel_ready_rate: float
    extracted_schools: int
    extracted_rate: float
    strict_auto_target_pdf_min: float
    manual_workload_max: float
    criteria: tuple[ShipReadinessCriterion, ...]

    @property
    def ok(self) -> bool:
        return all(criterion.passed for criterion in self.criteria)


def compute_ship_readiness(
    session: Session,
    *,
    fiscal_year: int | None = None,
    school_type: str | None = "専門学校",
    strict_auto_target_pdf_min: float = 0.60,
    manual_workload_max: float = 0.30,
) -> ShipReadinessReport:
    """Compute the final business ship line from current DB state."""

    fy = fiscal_year if fiscal_year is not None else settings.target_fiscal_year
    coverage = compute_coverage(session, school_type=school_type, fiscal_year=fy).totals
    export_gap = gap_report_for_export(session, fiscal_year=fy, school_type=school_type)

    total = int(coverage.schools_total)
    strict_target_pdf = int(coverage.schools_with_target_pdf_current_fy)
    extracted = int(coverage.schools_with_current_fy_extracted)
    excel_ready = int(export_gap.excel_ready_schools)
    operator_reviewable = _operator_reviewable_school_count(session, fiscal_year=fy, school_type=school_type)

    strict_target_pdf_rate = _rate(strict_target_pdf, total)
    extracted_rate = _rate(extracted, total)
    excel_ready_rate = _rate(excel_ready, total)
    operator_reviewable_rate = _rate(operator_reviewable, total)
    estimated_manual_workload_rate = 1.0 - operator_reviewable_rate if total else 0.0

    criteria = (
        ShipReadinessCriterion(
            name="estimated_manual_workload",
            value=estimated_manual_workload_rate,
            threshold=manual_workload_max,
            passed=estimated_manual_workload_rate <= manual_workload_max + 1e-9,
        ),
        ShipReadinessCriterion(
            name="excel_ready",
            value=excel_ready_rate,
            threshold=strict_auto_target_pdf_min,
            passed=excel_ready_rate >= strict_auto_target_pdf_min,
        ),
    )

    return ShipReadinessReport(
        fiscal_year=fy,
        school_type=school_type,
        total_schools=total,
        strict_target_pdf_schools=strict_target_pdf,
        strict_target_pdf_rate=strict_target_pdf_rate,
        operator_reviewable_schools=operator_reviewable,
        operator_reviewable_rate=operator_reviewable_rate,
        estimated_manual_workload_rate=estimated_manual_workload_rate,
        excel_ready_schools=excel_ready,
        excel_ready_rate=excel_ready_rate,
        extracted_schools=extracted,
        extracted_rate=extracted_rate,
        strict_auto_target_pdf_min=strict_auto_target_pdf_min,
        manual_workload_max=manual_workload_max,
        criteria=criteria,
    )


def _operator_reviewable_school_count(
    session: Session,
    *,
    fiscal_year: int,
    school_type: str | None,
) -> int:
    query = (
        session.query(func.count(SchoolFiscalYearStatus.school_id))
        .join(School, School.id == SchoolFiscalYearStatus.school_id)
        .filter(
            SchoolFiscalYearStatus.fiscal_year == fiscal_year,
            SchoolFiscalYearStatus.pdf_status.in_(SHIP_REVIEWABLE_PDF_STATUSES),
            School.status == "active",
        )
    )
    if school_type is not None:
        query = query.filter(School.school_type == school_type)
    return int(query.scalar() or 0)


def _rate(count: int, total: int) -> float:
    return count / total if total else 0.0

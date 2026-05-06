"""Fiscal-year extraction rate + prev-year delta outliers.

Acceptance criterion #2: target-fiscal-year 数値抽出率 ≥ 95% **of ingested PDFs**.

This is intentionally narrower than "of discovered PDFs": a PDF that is
discovered but not yet ingested (parse_failed / pending / transient) is
not counted in the denominator. PDF discovery vs ingestion gap is tracked
separately in `compute_gaps(kind="pdf")` (parse_failed_only / mismatch_only).
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from eidp.db.models import Department, DepartmentYearly, Document


@dataclass(frozen=True)
class DeltaOutlier:
    school_id: int
    department_id: int
    department_name: str
    prev_value: int
    curr_value: int
    delta_pct: float


@dataclass(frozen=True)
class ExtractionReport:
    fiscal_year: int
    documents_ingested: int
    documents_with_yearly_rows: int
    yearly_rows_total: int
    yearly_rows_with_capacity: int
    yearly_rows_with_enrollment: int
    delta_outliers: tuple[DeltaOutlier, ...]
    delta_threshold_pct: float

    @property
    def extraction_rate(self) -> float:
        if not self.documents_ingested:
            return 0.0
        return self.documents_with_yearly_rows / self.documents_ingested

    @property
    def capacity_fill_rate(self) -> float:
        if not self.yearly_rows_total:
            return 0.0
        return self.yearly_rows_with_capacity / self.yearly_rows_total


def compute_extraction(
    session: Session,
    fiscal_year: int,
    delta_threshold_pct: float = 50.0,
) -> ExtractionReport:
    """Compute extraction stats for a fiscal year and prev-year delta outliers."""

    docs = (
        session.query(Document.id)
        .filter(
            Document.fiscal_year == fiscal_year,
            Document.ingest_status == "ingested",
        )
        .all()
    )
    doc_ids = [d.id for d in docs]
    documents_ingested = len(doc_ids)

    documents_with_yearly_rows = 0
    if doc_ids:
        documents_with_yearly_rows = (
            session.query(DepartmentYearly.document_id)
            .filter(DepartmentYearly.document_id.in_(doc_ids))
            .distinct()
            .count()
        )

    yearly_rows = (
        session.query(
            DepartmentYearly.department_id,
            DepartmentYearly.capacity,
            DepartmentYearly.enrollment,
        )
        .filter(
            DepartmentYearly.fiscal_year == fiscal_year,
            DepartmentYearly.is_current.is_(True),
        )
        .all()
    )
    yearly_rows_total = len(yearly_rows)
    yearly_rows_with_capacity = sum(1 for r in yearly_rows if r.capacity is not None)
    yearly_rows_with_enrollment = sum(
        1 for r in yearly_rows if r.enrollment is not None
    )

    prev = {
        r.department_id: r.enrollment
        for r in session.query(
            DepartmentYearly.department_id, DepartmentYearly.enrollment
        )
        .filter(
            DepartmentYearly.fiscal_year == fiscal_year - 1,
            DepartmentYearly.is_current.is_(True),
            DepartmentYearly.enrollment.isnot(None),
        )
        .all()
    }

    outliers: list[DeltaOutlier] = []
    if prev:
        dept_meta = {
            d.id: (d.school_id, d.canonical_name)
            for d in session.query(Department).filter(Department.id.in_(prev.keys())).all()
        }
        for r in yearly_rows:
            if r.enrollment is None:
                continue
            p = prev.get(r.department_id)
            if not p:
                continue
            delta = (r.enrollment - p) / p * 100.0
            if abs(delta) >= delta_threshold_pct:
                school_id, name = dept_meta.get(r.department_id, (0, ""))
                outliers.append(
                    DeltaOutlier(
                        school_id=school_id,
                        department_id=r.department_id,
                        department_name=name,
                        prev_value=int(p),
                        curr_value=int(r.enrollment),
                        delta_pct=round(delta, 1),
                    )
                )
    outliers.sort(key=lambda o: abs(o.delta_pct), reverse=True)

    return ExtractionReport(
        fiscal_year=fiscal_year,
        documents_ingested=documents_ingested,
        documents_with_yearly_rows=documents_with_yearly_rows,
        yearly_rows_total=yearly_rows_total,
        yearly_rows_with_capacity=yearly_rows_with_capacity,
        yearly_rows_with_enrollment=yearly_rows_with_enrollment,
        delta_outliers=tuple(outliers),
        delta_threshold_pct=delta_threshold_pct,
    )

"""Rebuild denormalized School x fiscal-year operator status rows."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from eidp.db.models import (
    Department,
    DepartmentChange,
    DepartmentYearly,
    Document,
    School,
    SchoolFiscalYearStatus,
    SchoolSite,
)
from eidp.extraction_confidence import thresholds_from_env
from eidp.fiscal_year_evidence import fiscal_year_evidence_for_document

REVIEW_STATUSES: tuple[str, ...] = (
    "ocr_pending",
    "parse_failed",
    "review_pending",
    "school_mismatch",
)
CONFIRMED_TARGET_INGEST_STATUSES: tuple[str, ...] = (
    "ingested",
    "parse_failed",
    "review_pending",
    "support_only",
)
CONFIRMED_IMAGE_ONLY_INGEST_STATUSES: tuple[str, ...] = (
    "ingested",
    "review_pending",
    "support_only",
)
OPERATOR_REVIEWABLE_PDF_STATUSES: tuple[str, ...] = (
    "discovered",
    "publication_lag",
    "target_year_unverified",
    "image_pending",
)
SHIP_REVIEWABLE_PDF_STATUSES: tuple[str, ...] = (
    "confirmed_target",
    *OPERATOR_REVIEWABLE_PDF_STATUSES,
)
YOY_COMPARE_FIELDS: tuple[str, ...] = (
    "capacity",
    "enrollment",
    "intl_students",
    "graduates",
    "advanced",
    "employed",
    "other",
    "prev_enrollment",
    "dropouts",
    "dropout_rate",
)


@dataclass(frozen=True)
class SchoolFiscalYearStatusStats:
    fiscal_year: int
    school_type: str | None
    rebuilt: int
    excel_ready: int


def operator_reviewable_status_count(status_counts: Mapping[str, int]) -> int:
    """Return unresolved PDF-status rows that are directly reviewable by the operator."""
    return sum(max(int(status_counts.get(status) or 0), 0) for status in OPERATOR_REVIEWABLE_PDF_STATUSES)


def _url_status(sites: list[SchoolSite]) -> str:
    crawlable = [s for s in sites if s.http_status == 200 or s.http_status is None]
    if not crawlable:
        return "no_url"
    if any(s.discovery_method == "prefecture_aggregator" for s in crawlable):
        return "pref_url"
    if any(s.discovery_method == "operator_manual" for s in crawlable):
        return "operator_url"
    return "unknown"


def _pdf_status(docs: list[Document], fiscal_year: int) -> str:
    if any(
        d.fiscal_year == fiscal_year
        and (
            (
                d.pdf_type == "target"
                and d.ingest_status in CONFIRMED_TARGET_INGEST_STATUSES
            )
            or (
                d.pdf_type == "image_only"
                and d.ingest_status in CONFIRMED_IMAGE_ONLY_INGEST_STATUSES
            )
        )
        for d in docs
    ):
        return "confirmed_target"
    if any(
        d.fiscal_year == fiscal_year
        and d.pdf_type == "image_only"
        and d.ingest_status in {"ocr_pending", "parse_failed"}
        for d in docs
    ):
        return "image_pending"
    if any(d.ingest_status == "ocr_pending" for d in docs):
        return "image_pending"
    if any(
        d.pdf_type == "target"
        and d.fiscal_year is not None
        and d.fiscal_year < fiscal_year
        and d.ingest_status == "ingested"
        for d in docs
    ):
        return "rejected_stale"
    if docs:
        return "discovered"
    return "none"


def _extract_status(docs: list[Document], has_current_rows: bool) -> str:
    if has_current_rows:
        return "parsed"
    if any(d.ingest_status == "ocr_pending" for d in docs):
        return "ocr_pending"
    if any(d.ingest_status == "parse_failed" for d in docs):
        return "parse_failed"
    return "none"


def _evidence_level(docs: list[Document], fiscal_year: int, pdf_status: str) -> str:
    evidences = [
        fiscal_year_evidence_for_document(doc, target_fiscal_year=fiscal_year)
        for doc in docs
        if doc.pdf_type == "target"
    ]
    if not evidences:
        return "none"

    # Parsed/operator mismatch outranks URL hints in product behavior: a stale
    # PDF must not become target-FY evidence just because the URL path contains
    # the target year.
    if pdf_status == "rejected_stale" and any(e.level == "conflict" for e in evidences):
        return "conflict"

    return max(evidences, key=lambda e: e.rank).level


def _current_yearly_by_school(
    session: Session,
    *,
    school_ids: list[int],
    fiscal_year: int,
) -> dict[tuple[int, int], list[tuple[Department, DepartmentYearly]]]:
    rows = (
        session.query(Department, DepartmentYearly)
        .join(DepartmentYearly, DepartmentYearly.department_id == Department.id)
        .filter(
            Department.school_id.in_(school_ids),
            DepartmentYearly.fiscal_year.in_((fiscal_year, fiscal_year - 1)),
            DepartmentYearly.is_current.is_(True),
        )
        .all()
    )
    by_school_year: dict[tuple[int, int], list[tuple[Department, DepartmentYearly]]] = {}
    for dept, yearly in rows:
        by_school_year.setdefault((dept.school_id, yearly.fiscal_year), []).append((dept, yearly))
    return by_school_year


def _unverified_department_change_school_ids(
    session: Session,
    *,
    school_ids: list[int],
    fiscal_year: int,
) -> set[int]:
    return {
        int(school_id)
        for (school_id,) in (
            session.query(Department.school_id)
            .join(DepartmentChange, DepartmentChange.department_id == Department.id)
            .filter(
                Department.school_id.in_(school_ids),
                DepartmentChange.fiscal_year == fiscal_year,
                DepartmentChange.verified.is_(False),
                DepartmentChange.voided.is_(False),
            )
            .distinct()
            .all()
        )
    }


def _yearly_snapshot(row: DepartmentYearly) -> tuple[object, ...]:
    return tuple(getattr(row, field) for field in YOY_COMPARE_FIELDS)


def _yoy_diff_status(
    *,
    current_rows: list[tuple[Department, DepartmentYearly]],
    previous_rows: list[tuple[Department, DepartmentYearly]],
) -> str:
    """Classify target-year rows against the prior fiscal year.

    A perfect match is suspicious during the target-year acquisition season:
    it may mean the school has not updated the disclosure PDF yet. Any numeric
    value change or department set change is enough to mark the school as
    having a previous-year difference.
    """
    if not current_rows:
        return "unchecked"
    if not previous_rows:
        return "new_school"

    current = {dept.id: _yearly_snapshot(yearly) for dept, yearly in current_rows}
    previous = {dept.id: _yearly_snapshot(yearly) for dept, yearly in previous_rows}
    if set(current) != set(previous):
        return "partial_diff"
    if any(current[dept_id] != previous[dept_id] for dept_id in current):
        return "partial_diff"
    return "identical_to_prev_fy"


def _blocking_reason(
    *,
    url_status: str,
    pdf_status: str,
    extract_status: str,
    excel_ready: bool,
) -> str | None:
    if excel_ready:
        return None
    if pdf_status == "none":
        if url_status == "no_url":
            return "no_url"
        return "no_target_pdf"
    if pdf_status == "publication_lag":
        return "publication_lag_latest_public"
    if pdf_status == "target_year_unverified":
        return "target_year_unverified"
    if pdf_status == "site_error":
        return "tls_certificate_verify_failed"
    if pdf_status == "rejected_stale":
        return "stale_pdf_only"
    if pdf_status == "image_pending":
        return "ocr_pending"
    if extract_status == "parse_failed":
        return "parse_failed"
    if extract_status == "none":
        return "not_extracted"
    return "review_required"


def _discovery_evidence_school_buckets(discovery_evidence_path: Path | None) -> dict[int, str]:
    if discovery_evidence_path is None or not discovery_evidence_path.is_file():
        return {}

    from eidp.scraper.discovery_evidence_summary import (
        load_pdf_discovery_evidence,
        summarize_pdf_discovery_evidence,
    )

    summary = summarize_pdf_discovery_evidence(load_pdf_discovery_evidence(discovery_evidence_path))
    return {
        school_summary.school_id: school_summary.bucket
        for school_summary in summary.school_summaries
        if school_summary.bucket != "no_evidence"
    }


def rebuild_school_fiscal_year_status(
    session: Session,
    *,
    fiscal_year: int,
    school_type: str | None = "専門学校",
    discovery_evidence_path: Path | None = None,
) -> SchoolFiscalYearStatusStats:
    """Rebuild one ``SchoolFiscalYearStatus`` row per active school.

    Source-of-truth rows remain ``SchoolSite``, ``Document``, and
    ``DepartmentYearly``. This table is a denormalized operator task surface so
    UI pages can answer "what should happen next for this school?" without
    re-implementing fragile ad hoc joins.
    """
    school_q = session.query(School).filter(School.status == "active")
    if school_type is not None:
        school_q = school_q.filter(School.school_type == school_type)
    schools = school_q.order_by(School.id).all()
    school_ids = [s.id for s in schools]
    if not school_ids:
        return SchoolFiscalYearStatusStats(
            fiscal_year=fiscal_year,
            school_type=school_type,
            rebuilt=0,
            excel_ready=0,
        )

    sites_by_school: dict[int, list[SchoolSite]] = {sid: [] for sid in school_ids}
    for site in session.query(SchoolSite).filter(SchoolSite.school_id.in_(school_ids)).all():
        sites_by_school.setdefault(site.school_id, []).append(site)

    docs_by_school: dict[int, list[Document]] = {sid: [] for sid in school_ids}
    for doc in session.query(Document).filter(Document.school_id.in_(school_ids)).all():
        docs_by_school.setdefault(doc.school_id, []).append(doc)

    yearly_by_school = _current_yearly_by_school(
        session,
        school_ids=school_ids,
        fiscal_year=fiscal_year,
    )
    dept_change_review_school_ids = _unverified_department_change_school_ids(
        session,
        school_ids=school_ids,
        fiscal_year=fiscal_year,
    )
    discovery_evidence_buckets = _discovery_evidence_school_buckets(discovery_evidence_path)

    exportable_confidence_min = thresholds_from_env().review
    extracted_school_ids = {
        int(sid)
        for (sid,) in (
            session.query(Department.school_id)
            .join(DepartmentYearly, DepartmentYearly.department_id == Department.id)
            .filter(
                Department.school_id.in_(school_ids),
                DepartmentYearly.fiscal_year == fiscal_year,
                DepartmentYearly.is_current.is_(True),
                DepartmentYearly.capacity.is_not(None),
                (
                    DepartmentYearly.extraction_confidence.is_(None)
                    | (DepartmentYearly.extraction_confidence >= exportable_confidence_min)
                ),
            )
            .distinct()
            .all()
        )
    }

    ready_count = 0
    for school in schools:
        docs = docs_by_school.get(school.id, [])
        url_status = _url_status(sites_by_school.get(school.id, []))
        pdf_status = _pdf_status(docs, fiscal_year)
        evidence_bucket = discovery_evidence_buckets.get(school.id)
        if pdf_status == "none":
            if evidence_bucket == "publication_lag_or_old_target_pdf":
                pdf_status = "publication_lag"
            elif evidence_bucket == "target_form_without_year_evidence":
                pdf_status = "target_year_unverified"
            elif evidence_bucket == "tls_certificate_verify_failed":
                pdf_status = "site_error"
        extract_status = _extract_status(docs, school.id in extracted_school_ids)
        yoy_diff_status = _yoy_diff_status(
            current_rows=yearly_by_school.get((school.id, fiscal_year), []),
            previous_rows=yearly_by_school.get((school.id, fiscal_year - 1), []),
        )
        evidence_level = _evidence_level(docs, fiscal_year, pdf_status)
        if pdf_status == "publication_lag":
            evidence_level = "publication_lag"
        if pdf_status == "target_year_unverified":
            evidence_level = "target_year_unverified"
        if pdf_status == "site_error":
            evidence_level = "tls_certificate_verify_failed"
        if yoy_diff_status == "partial_diff" and evidence_level not in {"conflict", "operator_override"}:
            evidence_level = "prev_year_diff"
        has_dept_change_review = school.id in dept_change_review_school_ids
        excel_ready = (
            pdf_status == "confirmed_target"
            and extract_status == "parsed"
            and evidence_level in {"pdf_text", "prev_year_diff", "operator_override"}
            and yoy_diff_status != "identical_to_prev_fy"
            and not has_dept_change_review
        )
        if excel_ready:
            ready_count += 1

        row = session.get(SchoolFiscalYearStatus, (school.id, fiscal_year))
        if row is None:
            row = SchoolFiscalYearStatus(school_id=school.id, fiscal_year=fiscal_year)
            session.add(row)
        row.url_status = url_status
        row.pdf_status = pdf_status
        row.extract_status = extract_status
        row.yoy_diff_status = yoy_diff_status
        row.evidence_level = evidence_level
        row.excel_ready = excel_ready
        blocking_reason = _blocking_reason(
            url_status=url_status,
            pdf_status=pdf_status,
            extract_status=extract_status,
            excel_ready=excel_ready,
        )
        if has_dept_change_review and pdf_status == "confirmed_target" and extract_status == "parsed":
            blocking_reason = "dept_change_review"
        row.blocking_reason = blocking_reason

    session.flush()
    return SchoolFiscalYearStatusStats(
        fiscal_year=fiscal_year,
        school_type=school_type,
        rebuilt=len(schools),
        excel_ready=ready_count,
    )


def _empty_status_counts() -> dict[str, int]:
    return {
        "total": 0,
        "confirmed_target": 0,
        "confirmed_target_parsed": 0,
        "confirmed_target_excel_ready": 0,
        "publication_lag": 0,
        "target_year_unverified": 0,
        "image_pending": 0,
        "stale_or_old": 0,
        "review_or_parse": 0,
        "excel_ready": 0,
    }


def school_fiscal_year_status_counts(
    session: Session,
    *,
    fiscal_year: int,
    school_type: str | None = "専門学校",
    school_ids: Iterable[int] | None = None,
) -> dict[str, int]:
    """Return compact counts for dashboard / Excel-readiness surfaces."""
    selected_school_ids = set(school_ids or ())
    if school_ids is not None and not selected_school_ids:
        return _empty_status_counts()

    q = (
        session.query(
            SchoolFiscalYearStatus.pdf_status,
            SchoolFiscalYearStatus.extract_status,
            SchoolFiscalYearStatus.excel_ready,
            func.count(SchoolFiscalYearStatus.school_id),
        )
        .join(School, School.id == SchoolFiscalYearStatus.school_id)
        .filter(SchoolFiscalYearStatus.fiscal_year == fiscal_year)
    )
    if school_type is not None:
        q = q.filter(School.school_type == school_type)
    if school_ids is not None:
        q = q.filter(SchoolFiscalYearStatus.school_id.in_(selected_school_ids))

    counts = _empty_status_counts()
    for pdf_status, extract_status, excel_ready, n in q.group_by(
        SchoolFiscalYearStatus.pdf_status,
        SchoolFiscalYearStatus.extract_status,
        SchoolFiscalYearStatus.excel_ready,
    ):
        count = int(n or 0)
        counts["total"] += count
        if pdf_status == "confirmed_target":
            counts["confirmed_target"] += count
            if extract_status == "parsed":
                counts["confirmed_target_parsed"] += count
            if excel_ready:
                counts["confirmed_target_excel_ready"] += count
        if pdf_status == "publication_lag":
            counts["publication_lag"] += count
        if pdf_status == "target_year_unverified":
            counts["target_year_unverified"] += count
        if pdf_status == "image_pending":
            counts["image_pending"] += count
        if pdf_status in {"publication_lag", "rejected_stale"}:
            counts["stale_or_old"] += count
        if extract_status in REVIEW_STATUSES or pdf_status in {
            "image_pending",
            "discovered",
            "target_year_unverified",
        }:
            counts["review_or_parse"] += count
        if excel_ready:
            counts["excel_ready"] += count
    return counts

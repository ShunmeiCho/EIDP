"""PDF-to-DB ingestion pipeline — connects Step 9 parser to database.

Takes Document rows, runs parse_pdf, writes department + department_yearly,
updates school_year_status.
"""

import unicodedata
from pathlib import Path

import structlog
from sqlalchemy.orm import Session

from eidp.db.models import Department, DepartmentYearly, Document, SchoolYearStatus
from eidp.pdf.extractor import parse_pdf
from eidp.pdf.schema import SchoolAnnotation

log = structlog.get_logger()


def _norm(s: str) -> str:
    if not s:
        return ""
    return unicodedata.normalize("NFKC", s).strip()


def ingest_document(session: Session, doc: Document) -> dict[str, int]:
    """Parse a downloaded PDF and write extracted data to DB."""
    stats = {"departments_created": 0, "yearly_upserted": 0, "skipped": 0}

    if not doc.file_path:
        stats["skipped"] = 1
        return stats

    pdf_path = Path(doc.file_path)
    if not pdf_path.exists():
        log.warning("pdf_not_found", path=str(pdf_path), doc_id=doc.id)
        stats["skipped"] = 1
        return stats

    # Parse PDF
    annotation = parse_pdf(pdf_path)

    if not annotation.departments:
        log.warning("no_departments_parsed", path=str(pdf_path), doc_id=doc.id)
        stats["skipped"] = 1
        return stats

    # Determine fiscal year
    fiscal_year = _parse_fiscal_year_from_annotation(annotation.fiscal_year)

    for dept_record in annotation.departments:
        # Find or create department
        dept = (
            session.query(Department)
            .filter(
                Department.school_id == doc.school_id,
                Department.canonical_name == _norm(dept_record.name),
            )
            .first()
        )

        if not dept:
            dept = Department(
                school_id=doc.school_id,
                canonical_name=_norm(dept_record.name),
                course_name=dept_record.course_name,
                course_type=dept_record.day_or_evening,
                duration_years=dept_record.duration_years,
            )
            session.add(dept)
            session.flush()
            stats["departments_created"] += 1

        if fiscal_year:
            # Upsert department_yearly
            existing = (
                session.query(DepartmentYearly)
                .filter(
                    DepartmentYearly.department_id == dept.id,
                    DepartmentYearly.fiscal_year == fiscal_year,
                    DepartmentYearly.revision == 1,
                )
                .first()
            )

            if existing:
                # Update existing
                existing.capacity = dept_record.capacity
                existing.enrollment = dept_record.enrollment
                existing.intl_students = dept_record.intl_students
                existing.graduates = dept_record.graduates
                existing.advanced = dept_record.advanced
                existing.employed = dept_record.employed
                existing.other = dept_record.other
                existing.prev_enrollment = dept_record.prev_enrollment
                existing.dropouts = dept_record.dropouts
                existing.dropout_rate = dept_record.dropout_rate
                existing.document_id = doc.id
                existing.extraction_method = "pdf_parse"
            else:
                dy = DepartmentYearly(
                    department_id=dept.id,
                    document_id=doc.id,
                    fiscal_year=fiscal_year,
                    revision=1,
                    is_current=True,
                    capacity=dept_record.capacity,
                    enrollment=dept_record.enrollment,
                    intl_students=dept_record.intl_students,
                    graduates=dept_record.graduates,
                    advanced=dept_record.advanced,
                    employed=dept_record.employed,
                    other=dept_record.other,
                    prev_enrollment=dept_record.prev_enrollment,
                    dropouts=dept_record.dropouts,
                    dropout_rate=dept_record.dropout_rate,
                    extraction_method="pdf_parse",
                )
                session.add(dy)

            stats["yearly_upserted"] += 1

    # Update school_year_status
    if fiscal_year:
        sys = (
            session.query(SchoolYearStatus)
            .filter(
                SchoolYearStatus.school_id == doc.school_id,
                SchoolYearStatus.fiscal_year == fiscal_year,
            )
            .first()
        )
        if sys:
            sys.status = "collected"
            sys.document_id = doc.id
        else:
            from datetime import datetime, timezone
            new_sys = SchoolYearStatus(
                school_id=doc.school_id,
                fiscal_year=fiscal_year,
                status="collected",
                document_id=doc.id,
                collected_at=datetime.now(timezone.utc),
            )
            session.add(new_sys)

    session.flush()
    log.info("document_ingested", doc_id=doc.id, **stats)
    return stats


def _parse_fiscal_year_from_annotation(year_str: str) -> int | None:
    """Convert '令和7年度' to western year 2025."""
    import re
    if not year_str:
        return None
    m = re.search(r"令和(\d+)", year_str)
    if m:
        return 2018 + int(m.group(1))
    m = re.search(r"(20\d{2})", year_str)
    if m:
        return int(m.group(1))
    return None


def run_ingestion(session: Session, batch_size: int = 50) -> dict[str, int]:
    """Ingest all un-ingested documents."""
    total_stats = {"processed": 0, "departments_created": 0, "yearly_upserted": 0, "skipped": 0}

    # Find documents not yet ingested (no department_yearly with their document_id)
    from sqlalchemy import func
    ingested_doc_ids = (
        session.query(DepartmentYearly.document_id)
        .filter(DepartmentYearly.document_id.isnot(None))
        .distinct()
    )
    docs = (
        session.query(Document)
        .filter(
            Document.file_path.isnot(None),
            ~Document.id.in_(ingested_doc_ids),
        )
        .limit(batch_size)
        .all()
    )

    log.info("ingestion_start", documents=len(docs))

    for doc in docs:
        stats = ingest_document(session, doc)
        total_stats["processed"] += 1
        for k in ("departments_created", "yearly_upserted", "skipped"):
            total_stats[k] += stats[k]

    log.info("ingestion_complete", **total_stats)
    return total_stats

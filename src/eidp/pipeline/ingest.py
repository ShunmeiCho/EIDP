"""PDF-to-DB ingestion pipeline — connects Step 9 parser to database.

Takes Document rows, runs parse_pdf, writes department + department_yearly,
updates school_year_status.
"""

import unicodedata
from pathlib import Path

import structlog
from sqlalchemy.orm import Session

from eidp.db.models import Department, DepartmentYearly, Document, SchoolYearStatus, SupportRecipient
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

    # Skip image-only PDFs (need OCR fallback, not yet implemented)
    if doc.content_type == "image":
        log.info("image_pdf_skipped", doc_id=doc.id, path=str(pdf_path))
        stats["skipped"] = 1
        return stats

    # Skip non-target documents
    if doc.pdf_type == "non_target":
        log.info("non_target_skipped", doc_id=doc.id, path=str(pdf_path))
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
        # Find or create department — match full natural key to avoid collapsing
        # same-name departments with different course_type/duration
        dept = (
            session.query(Department)
            .filter(
                Department.school_id == doc.school_id,
                Department.canonical_name == _norm(dept_record.name),
                Department.course_type == (dept_record.day_or_evening if dept_record.day_or_evening else None),
                Department.course_name == (dept_record.course_name if dept_record.course_name else None),
                Department.duration_years == dept_record.duration_years,
            )
            .first()
        )

        if not dept:
            # Try relaxed match (name-only) if strict match fails
            # This handles cases where PDF parser couldn't extract all disambiguators
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
                course_name=dept_record.course_name if dept_record.course_name else None,
                course_type=dept_record.day_or_evening if dept_record.day_or_evening else None,
                duration_years=dept_record.duration_years,
            )
            session.add(dept)
            session.flush()
            stats["departments_created"] += 1

        if fiscal_year:
            # Append-only: find current max revision, mark old as non-current, insert new revision
            from sqlalchemy import func as sqlfunc

            max_rev_row = (
                session.query(sqlfunc.max(DepartmentYearly.revision))
                .filter(
                    DepartmentYearly.department_id == dept.id,
                    DepartmentYearly.fiscal_year == fiscal_year,
                )
                .scalar()
            )
            next_revision = (max_rev_row or 0) + 1

            # Mark all existing rows for this dept+year as non-current
            session.query(DepartmentYearly).filter(
                DepartmentYearly.department_id == dept.id,
                DepartmentYearly.fiscal_year == fiscal_year,
                DepartmentYearly.is_current == True,  # noqa: E712
            ).update({"is_current": False})

            dy = DepartmentYearly(
                department_id=dept.id,
                document_id=doc.id,
                fiscal_year=fiscal_year,
                revision=next_revision,
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

    # Ingest support recipient data (対象比率)
    # Non-destructive: only overwrite fields where PDF value is not None,
    # preserving existing Excel-imported data for fields the parser couldn't extract.
    if fiscal_year and annotation.support_recipient:
        sr_data = annotation.support_recipient
        existing_sr = (
            session.query(SupportRecipient)
            .filter(
                SupportRecipient.school_id == doc.school_id,
                SupportRecipient.fiscal_year == fiscal_year,
            )
            .first()
        )

        sr_fields = {
            "first_half_total": sr_data.first_half_total,
            "first_half_cat1": sr_data.first_half_cat1,
            "first_half_cat2": sr_data.first_half_cat2,
            "first_half_cat3": sr_data.first_half_cat3,
            "first_half_cat4": sr_data.first_half_cat4,
            "second_half_total": sr_data.second_half_total,
            "second_half_cat1": sr_data.second_half_cat1,
            "second_half_cat2": sr_data.second_half_cat2,
            "second_half_cat3": sr_data.second_half_cat3,
            "second_half_cat4": sr_data.second_half_cat4,
            "annual_total": sr_data.annual_total,
            "household_change": sr_data.household_change,
            "grand_total": sr_data.grand_total,
        }

        if existing_sr:
            existing_sr.document_id = doc.id
            # Only overwrite fields that have non-None PDF values
            for field_name, pdf_value in sr_fields.items():
                if pdf_value is not None:
                    setattr(existing_sr, field_name, pdf_value)
            existing_sr.extraction_confidence = 0.85
        else:
            sr = SupportRecipient(
                school_id=doc.school_id,
                document_id=doc.id,
                fiscal_year=fiscal_year,
                extraction_confidence=0.85,
                **{k: v for k, v in sr_fields.items()},
            )
            session.add(sr)
        stats["support_recipient"] = 1

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
        try:
            # Use a savepoint so one bad doc doesn't abort the whole batch
            nested = session.begin_nested()
            stats = ingest_document(session, doc)
            nested.commit()
            total_stats["processed"] += 1
            for k in ("departments_created", "yearly_upserted", "skipped"):
                total_stats[k] += stats[k]
        except Exception:
            nested.rollback()
            total_stats["skipped"] += 1
            log.exception("document_ingest_failed", doc_id=doc.id, path=doc.file_path)

    log.info("ingestion_complete", **total_stats)
    return total_stats

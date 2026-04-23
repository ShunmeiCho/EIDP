"""PDF-to-DB ingestion pipeline — connects Step 9 parser to database.

Takes Document rows, runs parse_pdf, writes department + department_yearly,
updates school_year_status.
"""

import re
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

import structlog
from sqlalchemy.orm import Session

from eidp.db.models import Department, DepartmentYearly, Document, SchoolYearStatus, SupportRecipient
from eidp.pdf.extractor import parse_pdf
from eidp.pdf.schema import SchoolAnnotation

log = structlog.get_logger()

JST = timezone(timedelta(hours=9))


def _norm(s: str) -> str:
    if not s:
        return ""
    return unicodedata.normalize("NFKC", s).strip()


def ingest_document(session: Session, doc: Document) -> dict[str, int]:
    """Parse a downloaded PDF and write extracted data to DB.

    Quality gate: only commit department data when the parser extracts
    at least enrollment for every department. Support-recipient data
    is always committed when available (school-level, not dept-level).
    """
    stats = {"departments_created": 0, "yearly_upserted": 0, "skipped": 0, "support_recipient": 0,
             "skip_reason": None}

    if not doc.file_path:
        doc.ingest_status = "no_file"
        stats["skipped"] = 1
        stats["skip_reason"] = "no_file"
        return stats

    pdf_path = Path(doc.file_path)
    if not pdf_path.exists():
        log.warning("pdf_not_found", path=str(pdf_path), doc_id=doc.id)
        doc.ingest_status = "no_file"
        stats["skipped"] = 1
        stats["skip_reason"] = "no_file"
        return stats

    # OCR fallback for image-only PDFs
    if doc.content_type == "image":
        # Content-hash deduplication: if another doc with same file_hash is
        # already terminally processed (ingested/non_target/school_mismatch/
        # permanent_error), this one inherits the same outcome without re-OCR
        if doc.file_hash:
            terminal_statuses = ["ingested", "non_target", "school_mismatch",
                                 "permanent_error", "support_only"]
            existing = (
                session.query(Document)
                .filter(
                    Document.file_hash == doc.file_hash,
                    Document.id != doc.id,
                    Document.ingest_status.in_(terminal_statuses),
                )
                .first()
            )
            if existing is not None:
                # Propagate the twin's actual status, not a hardcoded one.
                # If twin was 'ingested', this doc is still a mismatch (same PDF
                # can't belong to two schools), but if twin was 'non_target' or
                # 'permanent_error', we inherit that reason directly.
                twin_status = existing.ingest_status
                inherited_status = {
                    "ingested": "school_mismatch",       # dup ingest to another school is a mismatch
                    "support_only": "school_mismatch",   # dup support data to another school
                    "school_mismatch": "school_mismatch",
                    "non_target": "non_target",          # inherit: same PDF isn't a target form
                    "permanent_error": "permanent_error",  # inherit: same PDF is malformed
                }.get(twin_status, "school_mismatch")

                log.info("hash_dedup_skip", doc_id=doc.id,
                         twin_id=existing.id, twin_status=twin_status,
                         inherited_status=inherited_status,
                         file_hash=doc.file_hash[:16])
                doc.ingest_status = inherited_status
                stats["skipped"] = 1
                stats["skip_reason"] = f"hash_dedup:{twin_status}"
                return stats

        from eidp.pdf.ocr import extract_text_ocr
        ocr_pages = extract_text_ocr(pdf_path)
        if not ocr_pages or not any(t.strip() for t in ocr_pages):
            log.info("image_pdf_no_ocr", doc_id=doc.id, path=str(pdf_path))
            # Use ocr_pending instead of image_only so it can be retried
            # after OCR dependencies are installed or improved
            doc.ingest_status = "ocr_pending"
            stats["skipped"] = 1
            stats["skip_reason"] = "ocr_pending"
            return stats
        # Use OCR text for parsing
        from eidp.pdf.extractor import parse_pdf_ocr
        annotation = parse_pdf_ocr(pdf_path, ocr_pages)
        # Continue to school-identity check and ingestion below
    else:
        annotation = None  # will be set after this block

    # Skip non-target documents
    if doc.pdf_type == "non_target":
        log.info("non_target_skipped", doc_id=doc.id, path=str(pdf_path))
        doc.ingest_status = "non_target"
        stats["skipped"] = 1
        stats["skip_reason"] = "non_target"
        return stats

    # Parse PDF (skip if already parsed via OCR above)
    if annotation is None:
        annotation = parse_pdf(pdf_path)

    # School-identity verification: check parsed school_name against target school
    # Prevents wrong-school PDF data from silently entering the DB
    if annotation.school_name:
        from eidp.db.models import School
        target_school = session.query(School).filter(School.id == doc.school_id).first()
        if target_school:
            parsed_name = _norm(annotation.school_name)
            target_name = _norm(target_school.school_name)
            # Check if parsed name matches target (substring match for flexibility)
            if parsed_name and target_name and parsed_name not in target_name and target_name not in parsed_name:
                log.warning("school_name_mismatch",
                            doc_id=doc.id,
                            parsed=annotation.school_name,
                            target=target_school.school_name,
                            school_id=doc.school_id)
                doc.ingest_status = "school_mismatch"
                stats["skipped"] = 1
                stats["skip_reason"] = "school_mismatch"
                return stats

    # Determine fiscal year early — needed for both dept and support_recipient paths
    fiscal_year = _parse_fiscal_year_from_annotation(
        annotation.fiscal_year,
        source_url=doc.source_url,
    )

    # Fallback: if OCR couldn't extract fiscal_year (happens on scanned PDFs
    # where 令和 date is rendered as image), infer from download timestamp.
    # This is a best-effort inference, marked as such in the log.
    if (
        fiscal_year is None
        and annotation.fiscal_year
        and _has_fiscal_year_candidate(annotation.fiscal_year)
    ):
        log.warning(
            "invalid_fiscal_year_parsed",
            path=str(pdf_path),
            doc_id=doc.id,
            fiscal_year=annotation.fiscal_year,
            source_url=doc.source_url,
        )
    elif fiscal_year is None:
        fiscal_year = _infer_fiscal_year_from_download(doc.downloaded_at)
        if fiscal_year is not None:
            log.info("fiscal_year_inferred_from_download",
                     doc_id=doc.id, fiscal_year=fiscal_year,
                     downloaded_at=str(doc.downloaded_at))

    # Quality gate: partial ingest — accept valid depts, skip invalid ones
    # Requirements per dept:
    # 1. Fiscal year must be extracted (otherwise data goes to wrong year)
    # 2. Dept must have enrollment (minimum viable data)
    # 3. Dept must have a non-empty name >= 2 chars (identity integrity)
    valid_depts: list = []
    if annotation.departments and fiscal_year:
        valid_depts = [
            d for d in annotation.departments
            if d.enrollment is not None and d.name and len(d.name) >= 2
        ]
        skipped_depts = len(annotation.departments) - len(valid_depts)
        if skipped_depts > 0:
            log.warning("partial_parse",
                        path=str(pdf_path), doc_id=doc.id,
                        total_depts=len(annotation.departments),
                        valid_depts=len(valid_depts),
                        skipped_depts=skipped_depts,
                        fiscal_year=fiscal_year)
    elif annotation.departments and not fiscal_year:
        log.warning("no_fiscal_year_parsed",
                    path=str(pdf_path), doc_id=doc.id,
                    depts=len(annotation.departments))

    # Guard: if we have data but no fiscal year, we can't write anything usable
    if not fiscal_year and (annotation.departments or annotation.support_recipient):
        log.warning("data_without_fiscal_year", path=str(pdf_path), doc_id=doc.id,
                    depts=len(annotation.departments),
                    has_support=annotation.support_recipient is not None)
        doc.ingest_status = "parse_failed"
        stats["skipped"] = 1
        stats["skip_reason"] = "no_fiscal_year"
        return stats

    if not valid_depts and not annotation.support_recipient:
        log.warning("no_usable_data_parsed", path=str(pdf_path), doc_id=doc.id)
        doc.ingest_status = "parse_failed"
        stats["skipped"] = 1
        stats["skip_reason"] = "no_data"
        return stats

    for dept_record in valid_depts:
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

        # No name-only fallback: if the full natural key doesn't match,
        # create a new department rather than risking cross-linking data
        # to the wrong department (Codex P1-2 fix).
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

            # Lock existing rows first, then compute max revision
            # (FOR UPDATE cannot be combined with aggregate functions in PostgreSQL)
            existing_rows = (
                session.query(DepartmentYearly)
                .filter(
                    DepartmentYearly.department_id == dept.id,
                    DepartmentYearly.fiscal_year == fiscal_year,
                )
                .with_for_update()
                .all()
            )
            max_rev_row = max((r.revision for r in existing_rows), default=0) if existing_rows else 0
            next_revision = max_rev_row + 1

            # Mark all existing rows for this dept+year as non-current
            session.query(DepartmentYearly).filter(
                DepartmentYearly.department_id == dept.id,
                DepartmentYearly.fiscal_year == fiscal_year,
                DepartmentYearly.is_current == True,  # noqa: E712
            ).update({"is_current": False}, synchronize_session="fetch")

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
    # Distinguish full vs partial vs support-only collection
    if valid_depts and annotation.departments and len(valid_depts) < len(annotation.departments):
        collection_status = "partial"
    elif valid_depts:
        collection_status = "collected"
    else:
        collection_status = "support_only"

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
            # Don't downgrade from "collected" to "partial"
            if sys.status != "collected":
                sys.status = collection_status
            sys.document_id = doc.id
        else:
            from datetime import datetime, timezone
            new_sys = SchoolYearStatus(
                school_id=doc.school_id,
                fiscal_year=fiscal_year,
                status=collection_status,
                document_id=doc.id,
                collected_at=datetime.now(timezone.utc),
            )
            session.add(new_sys)

    # Write fiscal year back to Document so crawler can filter already-collected schools
    if fiscal_year:
        doc.fiscal_year = fiscal_year
        # Compute current fiscal year dynamically (April-March boundary)
        from datetime import datetime
        now = datetime.now()
        current_fy = now.year if now.month >= 4 else now.year - 1
        doc.is_current_year = (fiscal_year >= current_fy)

    session.flush()
    log.info("document_ingested", doc_id=doc.id, **stats)
    return stats


def _current_jst_fiscal_year() -> int:
    now = datetime.now(JST)
    return now.year if now.month >= 4 else now.year - 1


def _source_url_year_cap(source_url: str | None) -> int | None:
    if not source_url:
        return None
    years = [int(y) for y in re.findall(r"20\d{2}", source_url)]
    return max(years) if years else None


def _has_fiscal_year_candidate(year_str: str) -> bool:
    return bool(re.search(r"令和\d+|20\d{2}", year_str))


def _parse_fiscal_year_from_annotation(
    year_str: str,
    *,
    source_url: str | None = None,
    max_fiscal_year: int | None = None,
) -> int | None:
    """Convert '令和7年度' to western year 2025."""
    if not year_str:
        return None

    cap = _current_jst_fiscal_year() if max_fiscal_year is None else max_fiscal_year
    url_cap = _source_url_year_cap(source_url)
    if url_cap is not None:
        cap = min(cap, url_cap)

    m = re.search(r"令和(\d+)", year_str)
    if m:
        fiscal_year = 2018 + int(m.group(1))
        return fiscal_year if fiscal_year <= cap else None
    m = re.search(r"(20\d{2})", year_str)
    if m:
        fiscal_year = int(m.group(1))
        return fiscal_year if fiscal_year <= cap else None
    return None


def _infer_fiscal_year_from_download(downloaded_at) -> int | None:
    """Fallback: infer fiscal year from document download timestamp.

    Japanese fiscal year: April N to March N+1. Schools publish the
    annual disclosure PDF (the one we're parsing) typically Jun-Aug,
    reporting data FROM the fiscal year that just ended.

    downloaded_at is stored as UTC (timezone-aware); convert to JST
    (UTC+9) before computing the April boundary, otherwise a JST Apr 1
    download that was Mar 31 UTC would wrongly infer FY (Y-2).

    Download timestamp logic (in JST):
    - Downloaded Jan-Mar of year Y:  likely reports FY (Y-2) data
      (FY Y-1 hasn't ended yet; schools publish in summer)
    - Downloaded Apr-Dec of year Y:  likely reports FY (Y-1) data
      (FY Y-1 just ended; schools published in summer)

    Example: downloaded 2026-04 JST => FY 2025 (令和7年度).
             downloaded 2026-02 JST => FY 2024 (令和6年度).

    Plausibility bound: refuse to infer for downloads older than 3
    years (likely stale data, should be re-downloaded).
    """
    if downloaded_at is None:
        return None

    # Normalize to JST (handles both naive and aware datetimes)
    if downloaded_at.tzinfo is None:
        # Assume naive datetimes are UTC (matches upstream default)
        dt_utc = downloaded_at.replace(tzinfo=timezone.utc)
    else:
        dt_utc = downloaded_at
    dt_jst = dt_utc.astimezone(JST)

    # Plausibility bound: downloads >3 years old are stale, don't infer
    now_jst = datetime.now(JST)
    if (now_jst - dt_jst).days > 3 * 365:
        return None

    if dt_jst.month >= 4:
        return dt_jst.year - 1
    return dt_jst.year - 2


def run_ingestion(session: Session, batch_size: int = 50) -> dict[str, int]:
    """Ingest all un-ingested documents.

    Uses ingest_status to track processing state:
    - None or 'pending': eligible for ingestion
    - 'ingested': successfully processed
    - 'school_mismatch': parsed school_name didn't match target
    - 'parse_failed': parser returned no usable data
    - 'no_file': file_path missing or file not on disk
    - 'image_only': image-only PDF, needs OCR
    - 'non_target': not a target disclosure document
    - 'transient_error': network/IO error, can be retried
    """
    total_stats = {"processed": 0, "departments_created": 0, "yearly_upserted": 0, "skipped": 0}

    # Find documents eligible for ingestion with row-level locking.
    # FOR UPDATE SKIP LOCKED lets multiple parallel ingest workers pick
    # disjoint sets of documents without double-processing.
    # Skip: ingested, school_mismatch, parse_failed, no_file, image_only,
    # non_target, permanent_error (terminal states).
    from sqlalchemy import or_
    docs = (
        session.query(Document)
        .filter(
            Document.file_path.isnot(None),
            or_(
                Document.ingest_status.is_(None),
                Document.ingest_status.in_([
                    "pending", "transient_error", "ocr_pending",
                    # Recover stuck 'in_progress' from crashed prior runs.
                    # FOR UPDATE SKIP LOCKED ensures we don't grab rows
                    # another live worker is currently holding.
                    "in_progress",
                ]),
            ),
            or_(
                Document.pdf_type.is_(None),
                Document.pdf_type.notin_(["non_target"]),
            ),
        )
        .limit(batch_size)
        .with_for_update(skip_locked=True)
        .all()
    )

    # Mark claimed docs as 'in_progress' to make claim visible across workers
    # and commit immediately so row locks release.
    for doc in docs:
        doc.ingest_status = "in_progress"
    try:
        session.commit()
    except Exception:
        session.rollback()
        log.exception("claim_commit_failed", claimed=len(docs))
        return total_stats

    log.info("ingestion_start", documents=len(docs))

    for doc in docs:
        try:
            nested = session.begin_nested()
            stats = ingest_document(session, doc)
            nested.commit()

            # Mark ingest_status based on result
            # ingest_document may have already set a specific status (school_mismatch,
            # no_file, image_only, non_target, parse_failed). Only override if not set.
            if stats.get("yearly_upserted", 0) > 0:
                doc.ingest_status = "ingested"
            elif stats.get("support_recipient", 0) > 0 and stats.get("yearly_upserted", 0) == 0:
                doc.ingest_status = "support_only"
            elif stats.get("skipped", 0) > 0 and not doc.ingest_status:
                doc.ingest_status = "parse_failed"

            total_stats["processed"] += 1
            for k in ("departments_created", "yearly_upserted", "skipped"):
                total_stats[k] += stats.get(k, 0)
        except (OSError, IOError):
            try:
                nested.rollback()
            except Exception:
                log.exception("rollback_failed_after_io_error", doc_id=doc.id)
            doc.ingest_status = "transient_error"
            total_stats["skipped"] += 1
            log.exception("document_ingest_io_error", doc_id=doc.id, path=doc.file_path)
        except Exception:
            try:
                nested.rollback()
            except Exception:
                log.exception("rollback_failed_after_perm_error", doc_id=doc.id)
            doc.ingest_status = "permanent_error"
            total_stats["skipped"] += 1
            log.exception("document_ingest_failed", doc_id=doc.id, path=doc.file_path)

        # Per-document commit — guarded so a commit failure on one doc does not
        # kill the batch. On commit failure, rollback the session and continue.
        try:
            session.commit()
        except Exception:
            log.exception("per_doc_commit_failed", doc_id=doc.id, path=doc.file_path)
            try:
                session.rollback()
            except Exception:
                log.exception("rollback_failed_after_commit_error", doc_id=doc.id)

    log.info("ingestion_complete", **total_stats)
    return total_stats

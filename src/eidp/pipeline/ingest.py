"""PDF-to-DB ingestion pipeline — connects Step 9 parser to database.

Takes Document rows, runs parse_pdf, writes department + department_yearly,
updates school_year_status.
"""

import re
import unicodedata
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

import structlog
from sqlalchemy.orm import Session

from eidp.config import settings
from eidp.db.models import Department, DepartmentYearly, Document, SchoolYearStatus, SupportRecipient
from eidp.department_normalization import normalize_course_name
from eidp.extraction_confidence import (
    breakdown_to_json,
    classify,
    compute_ocr_tesseract_breakdown,
    compute_pdf_parse_breakdown,
    thresholds_from_env,
)
from eidp.fiscal_year import fiscal_year_from_japanese_era_text, has_fiscal_year_text
from eidp.pdf.extractor import parse_pdf, parse_pdf_ocr
from eidp.pdf.ocr import extract_text_ocr_result
from eidp.pdf.schema import DepartmentRecord
from eidp.pipeline.ingest_evidence import IngestEvidenceRecorder, IngestRejection

log = structlog.get_logger()


class IngestDocumentStats(TypedDict):
    departments_created: int
    yearly_upserted: int
    yearly_current: int
    yearly_review_pending: int
    support_recipient: int
    support_recipient_current: int
    support_recipient_review_pending: int
    skipped: int
    skip_reason: str | None
    invalid_fiscal_year: int


def _norm(s: str) -> str:
    if not s:
        return ""
    return unicodedata.normalize("NFKC", s).strip()


def _normalize_pdf_course_name(course_name: str | None) -> str | None:
    """Normalize PDF-side 課程名 to the field labels used by the Excel master."""

    return normalize_course_name(course_name)


def _ocr_extraction_method(provider: str) -> str:
    return {
        "tesseract": "ocr_tesseract",
        "paddleocr": "ocr_paddleocr",
        "pymupdf": "ocr_pymupdf",
    }.get(provider, "pdf_parse")


def _collapse_ws(s: str) -> str:
    """Same as _norm but also strips ALL internal whitespace.

    Used in school-name matching only — extracted school names sometimes
    insert ASCII spaces around inserted Latin segments (e.g.
    '岩谷学園よこはま IT ビジネス専門学校' vs DB
    '岩谷学園よこはまITビジネス専門学校'). Table parsing must NOT use
    this — it relies on whitespace to detect column boundaries.
    """
    if not s:
        return ""
    import re as _re
    return _re.sub(r"\s+", "", unicodedata.normalize("NFKC", s)).strip()


def _collapse_school_name_variant(s: str) -> str:
    """Normalize low-risk school-name orthographic variants for identity matching."""

    return _collapse_ws(s).lower().replace("アンド", "&").replace("&", "").replace("ー", "")


_NON_IDENTITY_SCHOOL_NAME_LABELS = frozenset({
    "設置認可年月日",
    "学校名",
    "法人名",
    "設置者名",
})


def _is_non_identity_school_name_label(value: str) -> bool:
    """Return whether parser output is a form/table label, not school identity evidence."""

    return _collapse_ws(value) in _NON_IDENTITY_SCHOOL_NAME_LABELS


def _record_rejection(
    recorder: IngestEvidenceRecorder | None,
    doc: Document,
    reason: str,
    **detail: object,
) -> None:
    if recorder is None:
        return
    recorder.record(IngestRejection(
        doc_id=doc.id,
        school_id=doc.school_id,
        file_path=doc.file_path,
        source_url=doc.source_url,
        pdf_type=doc.pdf_type,
        reason=reason,
        detail={k: str(v) for k, v in detail.items() if v is not None},
    ))


def ingest_document(
    session: Session,
    doc: Document,
    recorder: IngestEvidenceRecorder | None = None,
    target_fiscal_year: int | None = None,
) -> IngestDocumentStats:
    """Parse a downloaded PDF and write extracted data to DB.

    Quality gate: only commit department data when the parser extracts
    at least enrollment for every department. Support-recipient data
    is always committed when available (school-level, not dept-level).
    """
    stats: IngestDocumentStats = {
        "departments_created": 0,
        "yearly_upserted": 0,
        "yearly_current": 0,
        "yearly_review_pending": 0,
        "support_recipient": 0,
        "support_recipient_current": 0,
        "support_recipient_review_pending": 0,
        "skipped": 0,
        "skip_reason": None,
        "invalid_fiscal_year": 0,
    }

    if not doc.file_path:
        doc.ingest_status = "no_file"
        stats["skipped"] = 1
        stats["skip_reason"] = "no_file"
        _record_rejection(recorder, doc, "no_file")
        return stats

    pdf_path = Path(doc.file_path)
    if not pdf_path.exists():
        log.warning("pdf_not_found", path=str(pdf_path), doc_id=doc.id)
        _record_rejection(recorder, doc, "no_file", path=str(pdf_path))
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
                twin_status = existing.ingest_status or "unknown"
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
                _record_rejection(
                    recorder, doc, "hash_dedup",
                    twin_doc_id=existing.id,
                    twin_status=twin_status,
                    inherited_status=inherited_status,
                )
                doc.ingest_status = inherited_status
                stats["skipped"] = 1
                stats["skip_reason"] = f"hash_dedup:{twin_status}"
                return stats

        ocr_result = extract_text_ocr_result(pdf_path)
        ocr_pages = ocr_result.page_texts
        if not ocr_pages or not any(t.strip() for t in ocr_pages):
            log.info("image_pdf_no_ocr", doc_id=doc.id, path=str(pdf_path))
            _record_rejection(recorder, doc, "ocr_pending")
            # Use ocr_pending instead of image_only so it can be retried
            # after OCR dependencies are installed or improved
            doc.ingest_status = "ocr_pending"
            stats["skipped"] = 1
            stats["skip_reason"] = "ocr_pending"
            return stats
        # Use OCR text for parsing
        annotation = parse_pdf_ocr(pdf_path, ocr_pages)
        extraction_method = _ocr_extraction_method(ocr_result.provider)
        ocr_conf_values = ocr_result.conf_values
        # Continue to school-identity check and ingestion below
    else:
        annotation = None  # will be set after this block
        extraction_method = "pdf_parse"
        ocr_conf_values = []

    # Skip non-target documents
    if doc.pdf_type == "non_target":
        log.info("non_target_skipped", doc_id=doc.id, path=str(pdf_path))
        _record_rejection(recorder, doc, "non_target_pdf")
        doc.ingest_status = "non_target"
        stats["skipped"] = 1
        stats["skip_reason"] = "non_target"
        return stats

    # Parse PDF (skip if already parsed via OCR above)
    if annotation is None:
        annotation = parse_pdf(pdf_path)

    # School-identity verification: check parsed school_name against target school
    # Prevents wrong-school PDF data from silently entering the DB.
    # Consults SchoolAlias so historical/alternate names also count as a match
    # (e.g. 滋慶グループ 2024 renames: 東京ダンス&アクターズ → 東京ダンス・俳優
    # ＆舞台芸術).
    if annotation.school_name:
        from eidp.db.models import School, SchoolAlias
        target_school = session.query(School).filter(School.id == doc.school_id).first()
        if target_school:
            parsed_name = _norm(annotation.school_name)
            if _is_non_identity_school_name_label(parsed_name):
                parsed_name = ""
            target_name = _norm(target_school.school_name)
            candidate_names: list[str] = [target_name] if target_name else []
            aliases = (
                session.query(SchoolAlias)
                .filter(SchoolAlias.school_id == doc.school_id)
                .all()
            )
            for a in aliases:
                alias_norm = _norm(a.alias_name)
                if alias_norm:
                    candidate_names.append(alias_norm)

            # Substring match is only trusted for candidates long enough that
            # accidental containment is unlikely. Short aliases (e.g. 'TCA',
            # 'HAL') must match exactly to avoid bleeding into other schools.
            min_substr_len = 6

            def _match_any(parsed: str, candidates: list[str]) -> str | None:
                # Collapsed forms ignore internal whitespace; rescues common
                # parser variants like '専門学校 ちば愛犬' vs DB
                # '専門学校ちば愛犬' without requiring a SchoolAlias row.
                parsed_c = _collapse_ws(parsed)
                parsed_v = _collapse_school_name_variant(parsed)
                for c in candidates:
                    if not c:
                        continue
                    c_collapsed = _collapse_ws(c)
                    if parsed == c or parsed_c == c_collapsed or parsed_v == _collapse_school_name_variant(c):
                        return c
                    if len(c) >= min_substr_len and len(parsed) >= min_substr_len:
                        if (
                            parsed in c
                            or c in parsed
                            or parsed_c in c_collapsed
                            or c_collapsed in parsed_c
                        ):
                            return c
                return None

            matched_name = _match_any(parsed_name, candidate_names) if parsed_name else None
            if parsed_name and not matched_name:
                log.warning("school_name_mismatch",
                            doc_id=doc.id,
                            parsed=annotation.school_name,
                            target=target_school.school_name,
                            tried_aliases=[a.alias_name for a in aliases],
                            school_id=doc.school_id)
                _record_rejection(
                    recorder, doc, "school_mismatch",
                    parsed_school_name=annotation.school_name,
                    target_school_name=target_school.school_name,
                    alias_count=len(aliases),
                )
                doc.ingest_status = "school_mismatch"
                stats["skipped"] = 1
                stats["skip_reason"] = "school_mismatch"
                return stats

    # Determine fiscal year early — needed for both dept and support_recipient paths
    fiscal_year_cap = target_fiscal_year if target_fiscal_year is not None else settings.target_fiscal_year
    parsed_fiscal_year_candidate = _parse_fiscal_year_candidate_from_annotation(annotation.fiscal_year)
    parsed_fiscal_year = _parse_fiscal_year_from_annotation(
        annotation.fiscal_year,
        source_url=doc.source_url,
        max_fiscal_year=fiscal_year_cap,
    )
    invalid_fiscal_year = (
        parsed_fiscal_year_candidate is not None
        and parsed_fiscal_year_candidate > fiscal_year_cap
        and parsed_fiscal_year is None
    )
    fiscal_year = doc.fiscal_year or parsed_fiscal_year
    if doc.fiscal_year is not None and parsed_fiscal_year is not None and doc.fiscal_year != parsed_fiscal_year:
        log.info(
            "prevalidated_fiscal_year_preserved",
            doc_id=doc.id,
            document_fiscal_year=doc.fiscal_year,
            parsed_fiscal_year=parsed_fiscal_year,
            source_url=doc.source_url,
        )

    # Do not infer fiscal year from download time. Download timestamps prove
    # when the file was fetched, not which fiscal-year form the school
    # published. Missing fiscal-year evidence must remain operator-visible
    # instead of silently writing data to a guessed year.
    if (
        parsed_fiscal_year is None
        and annotation.fiscal_year
        and _has_fiscal_year_candidate(annotation.fiscal_year)
    ):
        if invalid_fiscal_year:
            log.warning(
                "fiscal_year_exceeds_target_cap",
                path=str(pdf_path),
                doc_id=doc.id,
                fiscal_year=annotation.fiscal_year,
                parsed_fiscal_year=parsed_fiscal_year_candidate,
                target_fiscal_year=fiscal_year_cap,
                source_url=doc.source_url,
            )
        else:
            log.warning(
                "invalid_fiscal_year_parsed",
                path=str(pdf_path),
                doc_id=doc.id,
                fiscal_year=annotation.fiscal_year,
                source_url=doc.source_url,
            )

    # Quality gate: partial ingest — accept valid depts, skip invalid ones
    # Requirements per dept:
    # 1. Fiscal year must be extracted (otherwise data goes to wrong year)
    # 2. Dept must have enrollment (minimum viable data)
    # 3. Dept must have a non-empty name >= 2 chars (identity integrity)
    valid_depts: list[DepartmentRecord] = []
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
        if invalid_fiscal_year:
            log.warning("invalid_fiscal_year_blocked",
                        path=str(pdf_path), doc_id=doc.id,
                        depts=len(annotation.departments),
                        parsed_fiscal_year=parsed_fiscal_year_candidate,
                        target_fiscal_year=fiscal_year_cap)
        else:
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
        if invalid_fiscal_year:
            stats["invalid_fiscal_year"] = 1
            stats["skip_reason"] = "invalid_fiscal_year"
            _record_rejection(
                recorder,
                doc,
                "invalid_fiscal_year",
                fiscal_year=annotation.fiscal_year,
                parsed_fiscal_year=parsed_fiscal_year_candidate,
                target_fiscal_year=fiscal_year_cap,
            )
        else:
            stats["skip_reason"] = "no_fiscal_year"
            _record_rejection(
                recorder,
                doc,
                "no_fiscal_year",
                fiscal_year=annotation.fiscal_year or None,
            )
        return stats

    if not valid_depts and not annotation.support_recipient:
        log.warning("no_usable_data_parsed", path=str(pdf_path), doc_id=doc.id)
        doc.ingest_status = "parse_failed"
        stats["skipped"] = 1
        stats["skip_reason"] = "no_data"
        return stats

    for dept_record in valid_depts:
        course_name = _normalize_pdf_course_name(dept_record.course_name)
        # Find or create department — match full natural key to avoid collapsing
        # same-name departments with different course_type/duration
        dept = (
            session.query(Department)
            .filter(
                Department.school_id == doc.school_id,
                Department.canonical_name == _norm(dept_record.name),
                Department.course_type == (dept_record.day_or_evening if dept_record.day_or_evening else None),
                Department.course_name == course_name,
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
                course_name=course_name,
                course_type=dept_record.day_or_evening if dept_record.day_or_evening else None,
                duration_years=dept_record.duration_years,
            )
            session.add(dept)
            session.flush()
            stats["departments_created"] += 1

        if fiscal_year:
            # Append-only: find current max revision, mark old as non-current, insert new revision
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

            # Sprint 8.6.b — confidence + gating. Look up the prior current
            # row's enrollment (if any) to feed F3 YoY sanity. Use the
            # already-loaded ``existing_rows`` so we don't re-query.
            prior_current = next((r for r in existing_rows if r.is_current), None)
            prior_enrollment = (
                prior_current.enrollment if prior_current is not None else None
            )
            dept_record_dict = {
                "name": dept_record.name,
                "capacity": dept_record.capacity,
                "enrollment": dept_record.enrollment,
                "graduates": dept_record.graduates,
            }
            if extraction_method == "ocr_tesseract":
                breakdown = compute_ocr_tesseract_breakdown(
                    dept_record_dict,
                    prior_enrollment=prior_enrollment,
                    per_word_confidences=ocr_conf_values,
                )
            else:
                breakdown = compute_pdf_parse_breakdown(
                    dept_record_dict,
                    prior_enrollment=prior_enrollment,
                    method=extraction_method,
                )
            verdict = classify(breakdown.composite, thresholds_from_env())
            is_current_row = verdict in ("auto", "auto_flag")

            if is_current_row:
                session.query(DepartmentYearly).filter(
                    DepartmentYearly.department_id == dept.id,
                    DepartmentYearly.fiscal_year == fiscal_year,
                    DepartmentYearly.is_current == True,  # noqa: E712
                ).update({"is_current": False}, synchronize_session="fetch")

            if is_current_row:
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
                    extraction_method=extraction_method,
                    extraction_confidence=breakdown.composite,
                    confidence_breakdown=breakdown_to_json(breakdown),
                )
                session.add(dy)
                stats["yearly_upserted"] += 1
                stats["yearly_current"] += 1
            else:
                stats["yearly_review_pending"] += 1

    # Ingest support recipient data (対象比率)
    # Sprint 8.2.b: append-only with revision support for rows that pass
    # the confidence gate. Low-confidence SR parses route to review_pending
    # without writing business-table rows.
    if fiscal_year and annotation.support_recipient:
        sr_data = annotation.support_recipient
        existing_sr_rows = (
            session.query(SupportRecipient)
            .filter(
                SupportRecipient.school_id == doc.school_id,
                SupportRecipient.fiscal_year == fiscal_year,
            )
            .with_for_update()
            .all()
        )
        current_sr = next((r for r in existing_sr_rows if r.is_current), None)
        max_sr_rev = max((r.revision for r in existing_sr_rows), default=0)

        sr_field_names = (
            "first_half_total",
            "first_half_cat1",
            "first_half_cat2",
            "first_half_cat3",
            "first_half_cat4",
            "second_half_total",
            "second_half_cat1",
            "second_half_cat2",
            "second_half_cat3",
            "second_half_cat4",
            "annual_total",
            "household_change",
            "grand_total",
        )
        # Start from current row's values (preserve Excel fallback) then
        # overlay any non-None PDF values.
        merged_sr_fields = {name: getattr(current_sr, name, None) for name in sr_field_names}
        for name in sr_field_names:
            pdf_value = getattr(sr_data, name, None)
            if pdf_value is not None:
                merged_sr_fields[name] = pdf_value

        # Sprint 8.6.b — confidence + gating for the SR row. Required
        # set is the two top-line totals; F3 compares annual_total YoY.
        sr_required = ("annual_total", "grand_total")
        sr_record_dict = {name: merged_sr_fields.get(name) for name in sr_required}
        sr_prior_total = current_sr.annual_total if current_sr is not None else None
        sr_breakdown_record = {**sr_record_dict, "enrollment": merged_sr_fields.get("annual_total")}
        if extraction_method == "ocr_tesseract":
            sr_breakdown = compute_ocr_tesseract_breakdown(
                sr_breakdown_record,
                prior_enrollment=sr_prior_total,
                per_word_confidences=ocr_conf_values,
                required_fields=sr_required,
            )
        else:
            sr_breakdown = compute_pdf_parse_breakdown(
                sr_breakdown_record,
                prior_enrollment=sr_prior_total,
                required_fields=sr_required,
                method=extraction_method,
            )
        sr_verdict = classify(sr_breakdown.composite, thresholds_from_env())
        sr_is_current = sr_verdict in ("auto", "auto_flag")

        if sr_is_current and current_sr is not None:
            session.query(SupportRecipient).filter(
                SupportRecipient.school_id == doc.school_id,
                SupportRecipient.fiscal_year == fiscal_year,
                SupportRecipient.is_current == True,  # noqa: E712
            ).update({"is_current": False}, synchronize_session="fetch")

        if sr_is_current:
            sr = SupportRecipient(
                school_id=doc.school_id,
                document_id=doc.id,
                fiscal_year=fiscal_year,
                revision=max_sr_rev + 1,
                is_current=True,
                extraction_confidence=sr_breakdown.composite,
                confidence_breakdown=breakdown_to_json(sr_breakdown),
                **merged_sr_fields,
            )
            session.add(sr)
            stats["support_recipient"] = 1
            stats["support_recipient_current"] = 1
        else:
            stats["support_recipient_review_pending"] = 1

    # Update school_year_status
    # Distinguish full vs partial vs support-only collection.
    # Sprint 8.6.b.1: "collected" requires at least one DepartmentYearly
    # row that ACTUALLY landed at is_current=True. If every dept fell
    # below the review threshold, we cannot claim the year is collected
    # — mark it partial so the operator queue treats this PDF as needing
    # attention. The legacy "any valid dept" rule masked low-confidence
    # rows that never reached Excel.
    full_recognition = (
        valid_depts and annotation.departments
        and len(valid_depts) >= len(annotation.departments)
    )
    no_review_pending = (
        stats["yearly_review_pending"] == 0
        and stats["support_recipient_review_pending"] == 0
    )
    # Sprint 8.6.b.2 — owner P1: even one low-confidence parsed row means
    # the year is not "collected" yet, regardless of how many rows landed
    # at is_current=True. Operator must finish review first.
    if stats["yearly_current"] > 0 and full_recognition and no_review_pending:
        collection_status = "collected"
    elif stats["yearly_current"] > 0:
        collection_status = "partial"
    elif valid_depts:
        # Departments parsed but every row was gated to review — treat
        # the same as the prior "partial" surface so the operator sees
        # this fiscal year is incomplete.
        collection_status = "partial"
    else:
        collection_status = "support_only"

    if fiscal_year:
        # Sprint 8.2.b: append-only with revision support. Same pattern as
        # SupportRecipient: demote current row, insert new revision. The
        # "don't downgrade from collected to partial" rule is preserved by
        # merging the prior current row's status into the new revision.
        existing_sys_rows = (
            session.query(SchoolYearStatus)
            .filter(
                SchoolYearStatus.school_id == doc.school_id,
                SchoolYearStatus.fiscal_year == fiscal_year,
            )
            .with_for_update()
            .all()
        )
        current_sys = next((r for r in existing_sys_rows if r.is_current), None)
        max_sys_rev = max((r.revision for r in existing_sys_rows), default=0)

        # Don't downgrade collected → partial — UNLESS the current
        # ingest produced review-pending rows. Sprint 8.6.b.3 owner P1:
        # the legacy inheritance rule was masking mixed-confidence
        # downgrades, leaving SYS at 'collected' even when the latest
        # data has low-confidence rows that need operator review.
        effective_status = collection_status
        has_review_pending = (
            stats["yearly_review_pending"] > 0
            or stats["support_recipient_review_pending"] > 0
        )
        if (current_sys is not None
                and current_sys.status == "collected"
                and not has_review_pending):
            effective_status = "collected"
        # Carry forward fields the new PDF doesn't override
        legacy_status = current_sys.legacy_status if current_sys is not None else None
        excluded_reason = current_sys.excluded_reason if current_sys is not None else None
        last_checked = current_sys.last_checked if current_sys is not None else None

        if current_sys is not None:
            session.query(SchoolYearStatus).filter(
                SchoolYearStatus.school_id == doc.school_id,
                SchoolYearStatus.fiscal_year == fiscal_year,
                SchoolYearStatus.is_current == True,  # noqa: E712
            ).update({"is_current": False}, synchronize_session="fetch")

        new_sys = SchoolYearStatus(
            school_id=doc.school_id,
            fiscal_year=fiscal_year,
            status=effective_status,
            legacy_status=legacy_status,
            excluded_reason=excluded_reason,
            last_checked=last_checked,
            collected_at=datetime.now(UTC),
            document_id=doc.id,
            revision=max_sys_rev + 1,
            is_current=True,
        )
        session.add(new_sys)

    # Write fiscal year back to Document so crawler can filter already-collected schools
    if fiscal_year:
        doc.fiscal_year = fiscal_year
        doc.is_current_year = fiscal_year >= fiscal_year_cap

    session.flush()
    log.info("document_ingested", doc_id=doc.id, **stats)
    return stats


def _has_fiscal_year_candidate(year_str: str) -> bool:
    return has_fiscal_year_text(year_str)


def _parse_fiscal_year_candidate_from_annotation(year_str: str) -> int | None:
    if not year_str:
        return None
    fiscal_year = fiscal_year_from_japanese_era_text(year_str)
    if fiscal_year is not None:
        return fiscal_year
    m = re.search(r"(20\d{2})", year_str)
    if m:
        return int(m.group(1))
    return None


def _parse_fiscal_year_from_annotation(
    year_str: str,
    *,
    source_url: str | None = None,
    max_fiscal_year: int,
) -> int | None:
    """Convert fiscal-year annotations to a western year."""
    if not year_str:
        return None

    fiscal_year = _parse_fiscal_year_candidate_from_annotation(year_str)
    if fiscal_year is not None:
        return fiscal_year if fiscal_year <= max_fiscal_year else None
    return None


def run_ingestion(
    session: Session,
    batch_size: int = 50,
    document_ids: Sequence[int] | None = None,
    evidence_path: Path | None = None,
    target_fiscal_year: int | None = None,
) -> dict[str, int]:
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
    total_stats = {
        "processed": 0,
        "departments_created": 0,
        "yearly_upserted": 0,
        "skipped": 0,
        "invalid_fiscal_year": 0,
    }

    # Find documents eligible for ingestion with row-level locking.
    # FOR UPDATE SKIP LOCKED lets multiple parallel ingest workers pick
    # disjoint sets of documents without double-processing.
    # Skip: ingested, school_mismatch, parse_failed, no_file, image_only,
    # non_target, permanent_error (terminal states).
    from sqlalchemy import or_

    query = session.query(Document).filter(
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
    if document_ids:
        query = query.filter(Document.id.in_(document_ids))

    docs = (
        query
        .order_by(Document.id)
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

    with IngestEvidenceRecorder(evidence_path) as recorder:
        for doc in docs:
            try:
                nested = session.begin_nested()
                stats = ingest_document(
                    session,
                    doc,
                    recorder=recorder,
                    target_fiscal_year=target_fiscal_year,
                )
                nested.commit()

                # Mark ingest_status based on result.
                # ingest_document may have already set a specific status (school_mismatch,
                # no_file, image_only, non_target, parse_failed). Only override if not set.
                #
                # Sprint 8.6.b.1: "ingested" requires at least one row to have
                # actually reached is_current=True. If every dept and SR row
                # was gated below the review threshold, the doc must surface
                # in the manual-entry queue as ``review_pending`` — otherwise
                # it disappears between Excel and the queue.
                yearly_current = stats.get("yearly_current", 0)
                sr_current = stats.get("support_recipient_current", 0)
                yearly_review = stats.get("yearly_review_pending", 0)
                sr_review = stats.get("support_recipient_review_pending", 0)

                # Sprint 8.6.b.2 — mixed-confidence routing. Owner P1: if a
                # PDF carries one high-conf dept and one low-conf dept, the
                # low-conf row was rejected from business tables but the document was being marked
                # ``ingested`` because yearly_current > 0. The operator
                # would never see this PDF in PDF確認・手入力 even though
                # part of the data needs verification. Reverse the priority:
                # any review-pending row routes the document to review_pending,
                # regardless of how many rows landed at is_current=True.
                if yearly_review > 0 or sr_review > 0:
                    doc.ingest_status = "review_pending"
                elif yearly_current > 0:
                    doc.ingest_status = "ingested"
                elif sr_current > 0:
                    doc.ingest_status = "support_only"
                elif stats.get("skipped", 0) > 0 and not doc.ingest_status:
                    doc.ingest_status = "parse_failed"

                total_stats["processed"] += 1
                total_stats["departments_created"] += stats["departments_created"]
                total_stats["yearly_upserted"] += stats["yearly_upserted"]
                total_stats["skipped"] += stats["skipped"]
                total_stats["invalid_fiscal_year"] += stats["invalid_fiscal_year"]
            except OSError as e:
                try:
                    nested.rollback()
                except Exception:
                    log.exception("rollback_failed_after_io_error", doc_id=doc.id)
                doc.ingest_status = "transient_error"
                total_stats["skipped"] += 1
                log.exception("document_ingest_io_error", doc_id=doc.id, path=doc.file_path)
                _record_rejection(recorder, doc, "transient_error", error_type=type(e).__name__)
            except Exception as e:
                try:
                    nested.rollback()
                except Exception:
                    log.exception("rollback_failed_after_perm_error", doc_id=doc.id)
                doc.ingest_status = "permanent_error"
                total_stats["skipped"] += 1
                log.exception("document_ingest_failed", doc_id=doc.id, path=doc.file_path)
                _record_rejection(recorder, doc, "permanent_error", error_type=type(e).__name__)

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

"""Review state and report generation for extracted Linux/Web rows.

This module consumes extraction queue output and records operator review
decisions locally. It does not write final Excel output and does not import
external Copilot/NotebookLM results.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from uuid import uuid4

from eidp.pipeline.extraction_queue import (
    ExtractedMetricRow,
    ExtractionQueueItem,
    ExtractionQueueType,
    NextAction,
    ensure_extraction_queue,
    load_extracted_rows,
)


class ReviewValidationError(ValueError):
    """Raised when an invalid review action is requested."""


class ReviewTaskType(StrEnum):
    EXTRACTED_METRIC = "extracted_metric"
    EXCEPTION_MANUAL_OCR = "exception_manual_ocr"


class ReviewStatus(StrEnum):
    UNREVIEWED = "unreviewed"
    ACCEPTED = "accepted"
    CORRECTED = "corrected"
    NEEDS_REVIEW = "needs_review"
    EXCLUDED = "excluded"


REVIEW_REPORT_COLUMNS: tuple[str, ...] = (
    "school_name",
    "school_id",
    "fiscal_year",
    "department_name",
    "metric",
    "extracted_value",
    "corrected_value",
    "review_status",
    "confidence",
    "source_pdf",
    "page_no",
    "table_index",
    "row_index",
    "col_index",
    "raw_label",
    "raw_value",
    "canonical_metric",
    "review_note",
    "reviewed_by",
    "reviewed_at",
    "final_ready",
)


@dataclass(frozen=True)
class ExtractionReviewRecord:
    review_id: str
    task_type: ReviewTaskType
    intake_record_id: str
    school_name: str
    school_id: str | None
    fiscal_year: int
    source_page_url: str
    source_pdf: str | None
    department_name: str | None
    metric: str | None
    extracted_value: int | None
    corrected_value: int | None
    confidence: float
    page_no: int | None
    table_index: int | None
    row_index: int | None
    col_index: int | None
    raw_label: str | None
    raw_value: str | None
    canonical_metric: str | None
    review_status: ReviewStatus
    review_note: str | None
    reviewed_by: str | None
    reviewed_at: str | None
    next_action: NextAction | None
    created_at_utc: str
    updated_at_utc: str


def ensure_review_records(
    intake_root: Path,
    *,
    default_confidence: float = 1.0,
) -> list[ExtractionReviewRecord]:
    """Create missing review records for extracted rows and image exceptions."""
    root = Path(intake_root)
    existing = {record.review_id: record for record in load_review_records(root)}
    for item in ensure_extraction_queue(root):
        if item.queue_type == ExtractionQueueType.TEXT_EXTRACTION:
            for extracted_row in load_extracted_rows(root, item.intake_record_id):
                review = _review_record_from_extracted_row(
                    extracted_row,
                    default_confidence=default_confidence,
                )
                if review.review_id not in existing:
                    _write_review_record(root, review)
                    existing[review.review_id] = review
            continue
        if item.queue_type == ExtractionQueueType.MANUAL_OCR_EXCEPTION:
            review = _review_record_from_exception_item(item)
            if review.review_id not in existing:
                _write_review_record(root, review)
                existing[review.review_id] = review
    records = list(existing.values())
    records.sort(key=lambda record: record.created_at_utc, reverse=True)
    return records


def load_review_records(intake_root: Path) -> list[ExtractionReviewRecord]:
    records_dir = _reviews_dir(Path(intake_root))
    if not records_dir.exists():
        return []
    records: list[ExtractionReviewRecord] = []
    for path in records_dir.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            records.append(_review_record_from_mapping(payload))
        except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
            continue
    records.sort(key=lambda record: record.created_at_utc, reverse=True)
    return records


def accept_review_record(
    *,
    intake_root: Path,
    review_id: str,
    reviewed_by: str,
    review_note: str | None = None,
) -> ExtractionReviewRecord:
    record = _load_one_review_record(intake_root, review_id)
    _require_extracted_metric(record)
    updated = _review_update(
        record,
        status=ReviewStatus.ACCEPTED,
        corrected_value=None,
        reviewed_by=reviewed_by,
        review_note=review_note,
    )
    _write_review_record(Path(intake_root), updated)
    return updated


def correct_review_record(
    *,
    intake_root: Path,
    review_id: str,
    corrected_value: int,
    reviewed_by: str,
    review_note: str | None = None,
) -> ExtractionReviewRecord:
    record = _load_one_review_record(intake_root, review_id)
    _require_extracted_metric(record)
    updated = _review_update(
        record,
        status=ReviewStatus.CORRECTED,
        corrected_value=corrected_value,
        reviewed_by=reviewed_by,
        review_note=review_note,
    )
    _write_review_record(Path(intake_root), updated)
    return updated


def mark_review_needs_review(
    *,
    intake_root: Path,
    review_id: str,
    reviewed_by: str,
    review_note: str | None = None,
) -> ExtractionReviewRecord:
    record = _load_one_review_record(intake_root, review_id)
    updated = _review_update(
        record,
        status=ReviewStatus.NEEDS_REVIEW,
        corrected_value=record.corrected_value,
        reviewed_by=reviewed_by,
        review_note=review_note,
    )
    _write_review_record(Path(intake_root), updated)
    return updated


def exclude_review_record(
    *,
    intake_root: Path,
    review_id: str,
    reviewed_by: str,
    review_note: str | None = None,
) -> ExtractionReviewRecord:
    record = _load_one_review_record(intake_root, review_id)
    updated = _review_update(
        record,
        status=ReviewStatus.EXCLUDED,
        corrected_value=record.corrected_value,
        reviewed_by=reviewed_by,
        review_note=review_note,
    )
    _write_review_record(Path(intake_root), updated)
    return updated


def is_final_ready(record: ExtractionReviewRecord, *, min_confidence: float = 0.85) -> bool:
    if record.task_type != ReviewTaskType.EXTRACTED_METRIC:
        return False
    if record.review_status not in {ReviewStatus.ACCEPTED, ReviewStatus.CORRECTED}:
        return False
    return record.review_status == ReviewStatus.CORRECTED or record.confidence >= min_confidence


def review_report_rows(intake_root: Path) -> list[dict[str, object]]:
    return [_review_report_row(record) for record in load_review_records(intake_root)]


def review_report_csv(intake_root: Path) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=REVIEW_REPORT_COLUMNS)
    writer.writeheader()
    writer.writerows(review_report_rows(intake_root))
    return output.getvalue()


def _review_record_from_extracted_row(
    row: ExtractedMetricRow,
    *,
    default_confidence: float,
) -> ExtractionReviewRecord:
    now = _utc_now_iso()
    return ExtractionReviewRecord(
        review_id=_review_id_for_extracted_row(row),
        task_type=ReviewTaskType.EXTRACTED_METRIC,
        intake_record_id=row.intake_record_id,
        school_name=row.school_name,
        school_id=row.school_id,
        fiscal_year=row.fiscal_year,
        source_page_url=row.source_page_url,
        source_pdf=row.pdf_path,
        department_name=row.department_name,
        metric=row.metric,
        extracted_value=row.value,
        corrected_value=None,
        confidence=default_confidence,
        page_no=row.page_no,
        table_index=row.table_index,
        row_index=row.row_index,
        col_index=row.col_index,
        raw_label=row.raw_label,
        raw_value=row.raw_value,
        canonical_metric=row.metric,
        review_status=ReviewStatus.UNREVIEWED,
        review_note=None,
        reviewed_by=None,
        reviewed_at=None,
        next_action=None,
        created_at_utc=now,
        updated_at_utc=now,
    )


def _review_record_from_exception_item(item: ExtractionQueueItem) -> ExtractionReviewRecord:
    now = _utc_now_iso()
    return ExtractionReviewRecord(
        review_id=f"exception-{item.intake_record_id}",
        task_type=ReviewTaskType.EXCEPTION_MANUAL_OCR,
        intake_record_id=item.intake_record_id,
        school_name=item.school_name,
        school_id=item.school_id,
        fiscal_year=item.fiscal_year,
        source_page_url=item.source_page_url,
        source_pdf=item.pdf_path,
        department_name=None,
        metric=None,
        extracted_value=None,
        corrected_value=None,
        confidence=0.0,
        page_no=None,
        table_index=None,
        row_index=None,
        col_index=None,
        raw_label=None,
        raw_value=None,
        canonical_metric=None,
        review_status=ReviewStatus.NEEDS_REVIEW,
        review_note=None,
        reviewed_by=None,
        reviewed_at=None,
        next_action=item.next_action,
        created_at_utc=now,
        updated_at_utc=now,
    )


def _review_id_for_extracted_row(row: ExtractedMetricRow) -> str:
    payload = {
        "intake_record_id": row.intake_record_id,
        "department_name": row.department_name,
        "metric": row.metric,
        "page_no": row.page_no,
        "table_index": row.table_index,
        "row_index": row.row_index,
        "col_index": row.col_index,
        "raw_value": row.raw_value,
    }
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return f"metric-{digest[:24]}"


def _review_update(
    record: ExtractionReviewRecord,
    *,
    status: ReviewStatus,
    corrected_value: int | None,
    reviewed_by: str,
    review_note: str | None,
) -> ExtractionReviewRecord:
    actor = reviewed_by.strip()
    if not actor:
        raise ReviewValidationError("reviewed_by is required")
    now = _utc_now_iso()
    return replace(
        record,
        review_status=status,
        corrected_value=corrected_value,
        review_note=_clean_optional_text(review_note),
        reviewed_by=actor,
        reviewed_at=now,
        updated_at_utc=now,
    )


def _require_extracted_metric(record: ExtractionReviewRecord) -> None:
    if record.task_type != ReviewTaskType.EXTRACTED_METRIC:
        raise ReviewValidationError("manual/OCR exception tasks cannot be accepted as extracted data")


def _load_one_review_record(intake_root: Path, review_id: str) -> ExtractionReviewRecord:
    path = _reviews_dir(Path(intake_root)) / f"{review_id}.json"
    if not path.exists():
        raise KeyError(f"review record {review_id!r} not found")
    return _review_record_from_mapping(json.loads(path.read_text(encoding="utf-8")))


def _write_review_record(intake_root: Path, record: ExtractionReviewRecord) -> None:
    reviews_dir = _reviews_dir(intake_root)
    reviews_dir.mkdir(parents=True, exist_ok=True)
    target = reviews_dir / f"{record.review_id}.json"
    tmp = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
    tmp.write_text(
        json.dumps(_review_record_to_dict(record), ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp.replace(target)


def _reviews_dir(intake_root: Path) -> Path:
    return intake_root / "extraction" / "reviews"


def _review_report_row(record: ExtractionReviewRecord) -> dict[str, object]:
    return {
        "school_name": record.school_name,
        "school_id": record.school_id or "",
        "fiscal_year": record.fiscal_year,
        "department_name": record.department_name or "",
        "metric": record.metric or "",
        "extracted_value": record.extracted_value if record.extracted_value is not None else "",
        "corrected_value": record.corrected_value if record.corrected_value is not None else "",
        "review_status": record.review_status.value,
        "confidence": record.confidence,
        "source_pdf": record.source_pdf or "",
        "page_no": record.page_no if record.page_no is not None else "",
        "table_index": record.table_index if record.table_index is not None else "",
        "row_index": record.row_index if record.row_index is not None else "",
        "col_index": record.col_index if record.col_index is not None else "",
        "raw_label": record.raw_label or "",
        "raw_value": record.raw_value or "",
        "canonical_metric": record.canonical_metric or "",
        "review_note": record.review_note or "",
        "reviewed_by": record.reviewed_by or "",
        "reviewed_at": record.reviewed_at or "",
        "final_ready": is_final_ready(record),
    }


def _review_record_to_dict(record: ExtractionReviewRecord) -> dict[str, object]:
    return {
        "review_id": record.review_id,
        "task_type": record.task_type.value,
        "intake_record_id": record.intake_record_id,
        "school_name": record.school_name,
        "school_id": record.school_id,
        "fiscal_year": record.fiscal_year,
        "source_page_url": record.source_page_url,
        "source_pdf": record.source_pdf,
        "department_name": record.department_name,
        "metric": record.metric,
        "extracted_value": record.extracted_value,
        "corrected_value": record.corrected_value,
        "confidence": record.confidence,
        "page_no": record.page_no,
        "table_index": record.table_index,
        "row_index": record.row_index,
        "col_index": record.col_index,
        "raw_label": record.raw_label,
        "raw_value": record.raw_value,
        "canonical_metric": record.canonical_metric,
        "review_status": record.review_status.value,
        "review_note": record.review_note,
        "reviewed_by": record.reviewed_by,
        "reviewed_at": record.reviewed_at,
        "next_action": record.next_action.value if record.next_action is not None else None,
        "created_at_utc": record.created_at_utc,
        "updated_at_utc": record.updated_at_utc,
    }


def _review_record_from_mapping(payload: dict[str, object]) -> ExtractionReviewRecord:
    next_action = _optional_str(payload.get("next_action"))
    return ExtractionReviewRecord(
        review_id=_required_str(payload, "review_id"),
        task_type=ReviewTaskType(_required_str(payload, "task_type")),
        intake_record_id=_required_str(payload, "intake_record_id"),
        school_name=_required_str(payload, "school_name"),
        school_id=_optional_str(payload.get("school_id")),
        fiscal_year=_required_int(payload, "fiscal_year"),
        source_page_url=_required_str(payload, "source_page_url"),
        source_pdf=_optional_str(payload.get("source_pdf")),
        department_name=_optional_str(payload.get("department_name")),
        metric=_optional_str(payload.get("metric")),
        extracted_value=_optional_int(payload.get("extracted_value")),
        corrected_value=_optional_int(payload.get("corrected_value")),
        confidence=_required_float(payload, "confidence"),
        page_no=_optional_int(payload.get("page_no")),
        table_index=_optional_int(payload.get("table_index")),
        row_index=_optional_int(payload.get("row_index")),
        col_index=_optional_int(payload.get("col_index")),
        raw_label=_optional_str(payload.get("raw_label")),
        raw_value=_optional_str(payload.get("raw_value")),
        canonical_metric=_optional_str(payload.get("canonical_metric")),
        review_status=ReviewStatus(_required_str(payload, "review_status")),
        review_note=_optional_str(payload.get("review_note")),
        reviewed_by=_optional_str(payload.get("reviewed_by")),
        reviewed_at=_optional_str(payload.get("reviewed_at")),
        next_action=NextAction(next_action) if next_action is not None else None,
        created_at_utc=_required_str(payload, "created_at_utc"),
        updated_at_utc=_required_str(payload, "updated_at_utc"),
    )


def _clean_optional_text(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _required_str(payload: dict[str, object], key: str) -> str:
    value = payload[key]
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("value must be a string or null")
    return value


def _required_int(payload: dict[str, object], key: str) -> int:
    value = payload[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    return value


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("value must be an integer or null")
    return value


def _required_float(payload: dict[str, object], key: str) -> float:
    value = payload[key]
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{key} must be a number")
    return float(value)

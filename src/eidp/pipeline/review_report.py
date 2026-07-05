"""Normalized reviewed-row report for Linux/Web extraction review.

This module projects Goal 3B review records into stable rows for downstream
diffing. It does not write final Excel output.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path

from eidp.pipeline.extraction_review import (
    ExtractionReviewRecord,
    ReviewStatus,
    ReviewTaskType,
    load_review_records,
)

__all__ = [
    "NORMALIZED_REVIEW_REPORT_COLUMNS",
    "ReviewedExtractionRow",
    "final_review_value",
    "normalized_review_report_csv",
    "normalized_review_report_csv_from_records",
    "normalized_review_report_csv_from_rows",
    "normalized_review_report_rows",
    "normalized_review_report_rows_from_records",
    "reviewed_rows_from_records",
]


NORMALIZED_REVIEW_REPORT_COLUMNS: tuple[str, ...] = (
    "school_name",
    "school_id",
    "fiscal_year",
    "department_name",
    "metric",
    "original_value",
    "corrected_value",
    "final_review_value",
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
)


@dataclass(frozen=True)
class ReviewedExtractionRow:
    review_id: str
    intake_record_id: str
    task_type: ReviewTaskType
    school_name: str
    school_id: str | None
    fiscal_year: int
    department_name: str | None
    metric: str | None
    original_value: int | None
    corrected_value: int | None
    final_review_value: int | None
    review_status: ReviewStatus
    confidence: float
    source_pdf: str | None
    page_no: int | None
    table_index: int | None
    row_index: int | None
    col_index: int | None
    raw_label: str | None
    raw_value: str | None
    canonical_metric: str | None
    review_note: str | None
    reviewed_by: str | None
    reviewed_at: str | None


def final_review_value(record: ExtractionReviewRecord) -> int | None:
    """Resolve the comparable value after human review.

    Accepted rows use the original extracted value. Corrected rows use the
    corrected value. Needs-review, excluded, unreviewed, and manual/OCR tasks
    deliberately produce no final comparable value.
    """
    if record.task_type != ReviewTaskType.EXTRACTED_METRIC:
        return None
    if record.review_status == ReviewStatus.ACCEPTED:
        return record.extracted_value
    if record.review_status == ReviewStatus.CORRECTED:
        return record.corrected_value
    return None


def reviewed_rows_from_records(records: list[ExtractionReviewRecord]) -> list[ReviewedExtractionRow]:
    return [
        ReviewedExtractionRow(
            review_id=record.review_id,
            intake_record_id=record.intake_record_id,
            task_type=record.task_type,
            school_name=record.school_name,
            school_id=record.school_id,
            fiscal_year=record.fiscal_year,
            department_name=record.department_name,
            metric=record.metric,
            original_value=record.extracted_value,
            corrected_value=record.corrected_value,
            final_review_value=final_review_value(record),
            review_status=record.review_status,
            confidence=record.confidence,
            source_pdf=record.source_pdf,
            page_no=record.page_no,
            table_index=record.table_index,
            row_index=record.row_index,
            col_index=record.col_index,
            raw_label=record.raw_label,
            raw_value=record.raw_value,
            canonical_metric=record.canonical_metric,
            review_note=record.review_note,
            reviewed_by=record.reviewed_by,
            reviewed_at=record.reviewed_at,
        )
        for record in records
    ]


def normalized_review_report_rows(intake_root: Path) -> list[dict[str, object]]:
    return normalized_review_report_rows_from_records(load_review_records(intake_root))


def normalized_review_report_rows_from_records(records: list[ExtractionReviewRecord]) -> list[dict[str, object]]:
    return [_report_row(row) for row in reviewed_rows_from_records(records)]


def normalized_review_report_csv(intake_root: Path) -> str:
    return normalized_review_report_csv_from_records(load_review_records(intake_root))


def normalized_review_report_csv_from_records(records: list[ExtractionReviewRecord]) -> str:
    return normalized_review_report_csv_from_rows(reviewed_rows_from_records(records))


def normalized_review_report_csv_from_rows(rows: list[ReviewedExtractionRow]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=NORMALIZED_REVIEW_REPORT_COLUMNS)
    writer.writeheader()
    writer.writerows(_report_row(row) for row in rows)
    return output.getvalue()


def _report_row(row: ReviewedExtractionRow) -> dict[str, object]:
    return {
        "school_name": row.school_name,
        "school_id": row.school_id or "",
        "fiscal_year": row.fiscal_year,
        "department_name": row.department_name or "",
        "metric": row.metric or "",
        "original_value": row.original_value if row.original_value is not None else "",
        "corrected_value": row.corrected_value if row.corrected_value is not None else "",
        "final_review_value": row.final_review_value if row.final_review_value is not None else "",
        "review_status": row.review_status.value,
        "confidence": row.confidence,
        "source_pdf": row.source_pdf or "",
        "page_no": row.page_no if row.page_no is not None else "",
        "table_index": row.table_index if row.table_index is not None else "",
        "row_index": row.row_index if row.row_index is not None else "",
        "col_index": row.col_index if row.col_index is not None else "",
        "raw_label": row.raw_label or "",
        "raw_value": row.raw_value or "",
        "canonical_metric": row.canonical_metric or "",
        "review_note": row.review_note or "",
        "reviewed_by": row.reviewed_by or "",
        "reviewed_at": row.reviewed_at or "",
    }

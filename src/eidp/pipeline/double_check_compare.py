"""Compare reviewed EIDP rows against external second-opinion extraction rows.

This layer implements the Goal 4 double-check lane. It compares only unique
comparable reviewed rows and keeps ambiguous, needs-review, and excluded rows
out of any Excel-ready path.
"""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum

from eidp.pipeline.department_join import (
    COURSE_GRANULARITY_COLLISION_REASON,
    is_course_granularity_collision,
    join_key_label,
    make_join_key,
    values_equal,
)
from eidp.pipeline.external_extraction_import import ExternalExtractionRow, ExternalSourceSystem
from eidp.pipeline.extraction_review import ReviewStatus, ReviewTaskType
from eidp.pipeline.review_report import ReviewedExtractionRow

__all__ = [
    "DOUBLE_CHECK_REPORT_COLUMNS",
    "DoubleCheckResultRow",
    "DoubleCheckStatus",
    "compare_external_to_reviewed",
    "double_check_report_csv",
    "double_check_summary",
]


class DoubleCheckStatus(StrEnum):
    MATCH = "match"
    VALUE_MISMATCH = "value_mismatch"
    MISSING_IN_EIDP = "missing_in_eidp"
    MISSING_IN_EXTERNAL = "missing_in_external"
    AMBIGUOUS_KEY_NOT_COMPARABLE = "ambiguous_key_not_comparable"
    NEEDS_REVIEW_NOT_COMPARABLE = "needs_review_not_comparable"
    EXCLUDED_NOT_COMPARABLE = "excluded_not_comparable"


DOUBLE_CHECK_REPORT_COLUMNS: tuple[str, ...] = (
    "key",
    "review_id",
    "comparison_result",
    "comparison_status",
    "mismatch_reason",
    "excel_ready",
    "school_name",
    "school_id",
    "fiscal_year",
    "department_name",
    "field_category",
    "course_name",
    "metric",
    "eidp_value",
    "external_value",
    "review_status",
    "original_value",
    "corrected_value",
    "confidence",
    "source_system",
    "source_file",
    "source_row_number",
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

_DoubleCheckKey = tuple[str, str, str, int, str]


@dataclass(frozen=True)
class DoubleCheckResultRow:
    key: str
    review_id: str | None
    school_name: str
    school_id: str | None
    fiscal_year: int
    department_name: str
    field_category: str | None
    course_name: str | None
    metric: str
    eidp_value: int | float | str | None
    external_value: int | float | str | None
    comparison_status: DoubleCheckStatus
    comparison_result: str
    mismatch_reason: str
    excel_ready: bool
    review_status: ReviewStatus | None
    original_value: int | None
    corrected_value: int | None
    confidence: float | None
    source_system: ExternalSourceSystem | None
    source_file: str | None
    source_row_number: int | None
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


def compare_external_to_reviewed(
    reviewed_rows: list[ReviewedExtractionRow],
    external_rows: list[ExternalExtractionRow],
) -> list[DoubleCheckResultRow]:
    reviewed_by_key: dict[_DoubleCheckKey, list[ReviewedExtractionRow]] = defaultdict(list)
    external_by_key: dict[_DoubleCheckKey, list[ExternalExtractionRow]] = defaultdict(list)
    for reviewed_row in reviewed_rows:
        if reviewed_row.metric and reviewed_row.department_name:
            reviewed_by_key[_reviewed_key(reviewed_row)].append(reviewed_row)
    for external_row in external_rows:
        external_by_key[_external_key(external_row)].append(external_row)

    results: list[DoubleCheckResultRow] = []
    for key in sorted(set(reviewed_by_key) | set(external_by_key), key=repr):
        reviewed_group = reviewed_by_key.get(key, [])
        external_group = external_by_key.get(key, [])
        if len(reviewed_group) > 1 or len(external_group) > 1:
            results.extend(_ambiguous_rows(key, reviewed_group, external_group))
            continue

        maybe_reviewed_row = reviewed_group[0] if reviewed_group else None
        maybe_external_row = external_group[0] if external_group else None
        if maybe_reviewed_row is None and maybe_external_row is not None:
            results.append(
                _external_only_row(
                    maybe_external_row,
                    DoubleCheckStatus.MISSING_IN_EIDP,
                    "stable key absent from reviewed EIDP rows",
                )
            )
            continue
        if maybe_reviewed_row is None:
            continue
        if maybe_reviewed_row.review_status == ReviewStatus.EXCLUDED:
            results.append(
                _result_row(
                    maybe_reviewed_row,
                    maybe_external_row,
                    DoubleCheckStatus.EXCLUDED_NOT_COMPARABLE,
                    "review_status=excluded",
                )
            )
            continue
        if (
            maybe_reviewed_row.task_type != ReviewTaskType.EXTRACTED_METRIC
            or maybe_reviewed_row.final_review_value is None
        ):
            results.append(
                _result_row(
                    maybe_reviewed_row,
                    maybe_external_row,
                    DoubleCheckStatus.NEEDS_REVIEW_NOT_COMPARABLE,
                    "no final reviewed value",
                )
            )
            continue
        if maybe_external_row is None:
            results.append(
                _result_row(
                    maybe_reviewed_row,
                    None,
                    DoubleCheckStatus.MISSING_IN_EXTERNAL,
                    "stable key absent from external extraction rows",
                )
            )
            continue
        if is_course_granularity_collision(
            maybe_reviewed_row.department_name, maybe_external_row.department_name
        ):
            # The loose department_key joined these two rows, but the strict key (which never
            # collapses a bare trailing コース) says they are DISTINCT granularities. A TRUE here
            # would false-certify a course track against its parent 科, so mark it not-comparable
            # (never Excel-ready) and surface the pair for human disambiguation instead.
            results.append(
                _result_row(
                    maybe_reviewed_row,
                    maybe_external_row,
                    DoubleCheckStatus.AMBIGUOUS_KEY_NOT_COMPARABLE,
                    COURSE_GRANULARITY_COLLISION_REASON,
                )
            )
            continue
        if values_equal(maybe_reviewed_row.final_review_value, maybe_external_row.value):
            results.append(
                _result_row(
                    maybe_reviewed_row,
                    maybe_external_row,
                    DoubleCheckStatus.MATCH,
                    "EIDP value matches external value",
                )
            )
            continue
        results.append(
            _result_row(
                maybe_reviewed_row,
                maybe_external_row,
                DoubleCheckStatus.VALUE_MISMATCH,
                "EIDP value differs from external value",
            )
        )

    return results


def double_check_summary(rows: list[DoubleCheckResultRow]) -> dict[str, int]:
    counts = {status.value: 0 for status in DoubleCheckStatus}
    for row in rows:
        counts[row.comparison_status.value] += 1
    return counts


def double_check_report_csv(rows: list[DoubleCheckResultRow]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=DOUBLE_CHECK_REPORT_COLUMNS)
    writer.writeheader()
    writer.writerows(_report_row(row) for row in rows)
    return output.getvalue()


def _reviewed_key(row: ReviewedExtractionRow) -> _DoubleCheckKey:
    return make_join_key(
        row.school_name,
        row.field_category,
        row.department_name or "",
        row.fiscal_year,
        row.metric or "",
    )


def _external_key(row: ExternalExtractionRow) -> _DoubleCheckKey:
    return make_join_key(row.school_name, row.field_category, row.department_name, row.fiscal_year, row.metric)


def _result_row(
    reviewed_row: ReviewedExtractionRow,
    external_row: ExternalExtractionRow | None,
    status: DoubleCheckStatus,
    reason: str,
) -> DoubleCheckResultRow:
    key = _reviewed_key(reviewed_row)
    return DoubleCheckResultRow(
        key=join_key_label(key),
        review_id=reviewed_row.review_id,
        school_name=reviewed_row.school_name,
        school_id=reviewed_row.school_id,
        fiscal_year=reviewed_row.fiscal_year,
        department_name=reviewed_row.department_name or "",
        field_category=reviewed_row.field_category,
        course_name=reviewed_row.course_name,
        metric=reviewed_row.metric or "",
        eidp_value=reviewed_row.final_review_value,
        external_value=external_row.value if external_row is not None else None,
        comparison_status=status,
        comparison_result=_truth_label(status),
        mismatch_reason=reason,
        excel_ready=False,
        review_status=reviewed_row.review_status,
        original_value=reviewed_row.original_value,
        corrected_value=reviewed_row.corrected_value,
        confidence=reviewed_row.confidence,
        source_system=external_row.source_system if external_row is not None else None,
        source_file=external_row.source_file if external_row is not None else None,
        source_row_number=external_row.source_row_number if external_row is not None else None,
        source_pdf=reviewed_row.source_pdf,
        page_no=reviewed_row.page_no,
        table_index=reviewed_row.table_index,
        row_index=reviewed_row.row_index,
        col_index=reviewed_row.col_index,
        raw_label=reviewed_row.raw_label,
        raw_value=reviewed_row.raw_value,
        canonical_metric=reviewed_row.canonical_metric,
        review_note=reviewed_row.review_note,
        reviewed_by=reviewed_row.reviewed_by,
        reviewed_at=reviewed_row.reviewed_at,
    )


def _external_only_row(
    external_row: ExternalExtractionRow,
    status: DoubleCheckStatus,
    reason: str,
) -> DoubleCheckResultRow:
    key = _external_key(external_row)
    return DoubleCheckResultRow(
        key=join_key_label(key),
        review_id=None,
        school_name=external_row.school_name,
        school_id=external_row.school_id,
        fiscal_year=external_row.fiscal_year,
        department_name=external_row.department_name,
        field_category=external_row.field_category,
        course_name=external_row.course_name,
        metric=external_row.metric,
        eidp_value=None,
        external_value=external_row.value,
        comparison_status=status,
        comparison_result=_truth_label(status),
        mismatch_reason=reason,
        excel_ready=False,
        review_status=None,
        original_value=None,
        corrected_value=None,
        confidence=None,
        source_system=external_row.source_system,
        source_file=external_row.source_file,
        source_row_number=external_row.source_row_number,
        source_pdf=None,
        page_no=None,
        table_index=None,
        row_index=None,
        col_index=None,
        raw_label=None,
        raw_value=None,
        canonical_metric=None,
        review_note=None,
        reviewed_by=None,
        reviewed_at=None,
    )


def _ambiguous_rows(
    key: _DoubleCheckKey,
    reviewed_rows: list[ReviewedExtractionRow],
    external_rows: list[ExternalExtractionRow],
) -> list[DoubleCheckResultRow]:
    reason_parts: list[str] = []
    if len(reviewed_rows) > 1:
        reason_parts.append(f"duplicate reviewed rows={len(reviewed_rows)}")
    if len(external_rows) > 1:
        reason_parts.append(f"duplicate external rows={len(external_rows)}")
    reason = "; ".join(reason_parts)
    reviewed_candidates = [
        _result_row(row, None, DoubleCheckStatus.AMBIGUOUS_KEY_NOT_COMPARABLE, reason)
        for row in sorted(reviewed_rows, key=lambda row: row.review_id)
    ]
    external_candidates = [
        _external_only_row(row, DoubleCheckStatus.AMBIGUOUS_KEY_NOT_COMPARABLE, reason)
        for row in sorted(
            external_rows,
            key=lambda row: (row.source_file, row.source_row_number, repr(row.value)),
        )
    ]
    return [*reviewed_candidates, *external_candidates]


def _truth_label(status: DoubleCheckStatus) -> str:
    if status == DoubleCheckStatus.MATCH:
        return "TRUE"
    if status in {
        DoubleCheckStatus.VALUE_MISMATCH,
        DoubleCheckStatus.MISSING_IN_EIDP,
        DoubleCheckStatus.MISSING_IN_EXTERNAL,
    }:
        return "FALSE"
    return ""


def _report_row(row: DoubleCheckResultRow) -> dict[str, object]:
    return {
        "key": row.key,
        "review_id": row.review_id or "",
        "comparison_result": row.comparison_result,
        "comparison_status": row.comparison_status.value,
        "mismatch_reason": row.mismatch_reason,
        "excel_ready": row.excel_ready,
        "school_name": row.school_name,
        "school_id": row.school_id or "",
        "fiscal_year": row.fiscal_year,
        "department_name": row.department_name,
        "field_category": row.field_category or "",
        "course_name": row.course_name or "",
        "metric": row.metric,
        "eidp_value": row.eidp_value if row.eidp_value is not None else "",
        "external_value": row.external_value if row.external_value is not None else "",
        "review_status": row.review_status.value if row.review_status is not None else "",
        "original_value": row.original_value if row.original_value is not None else "",
        "corrected_value": row.corrected_value if row.corrected_value is not None else "",
        "confidence": row.confidence if row.confidence is not None else "",
        "source_system": row.source_system.value if row.source_system is not None else "",
        "source_file": row.source_file or "",
        "source_row_number": row.source_row_number if row.source_row_number is not None else "",
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

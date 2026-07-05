"""Diff reviewed extraction rows against a read-only master expected subset.

This is a Linux/Web review hardening layer. It produces mismatch reports for
reviewed rows and never writes final Excel output.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from eidp.excel.master_loader import load_master_metric_rows
from eidp.pdf.master_ground_truth import department_key, normalize_text
from eidp.pipeline.extraction_review import ReviewStatus
from eidp.pipeline.review_report import ReviewedExtractionRow

__all__ = [
    "DIFF_REPORT_COLUMNS",
    "DiffResultRow",
    "MatchStatus",
    "MasterExpectedRow",
    "diff_report_csv",
    "diff_reviewed_against_master",
    "diff_summary",
    "load_master_expected_subset",
]


class MatchStatus(StrEnum):
    MATCH = "match"
    MISSING_IN_EXTRACTION = "missing_in_extraction"
    MISSING_IN_MASTER = "missing_in_master"
    VALUE_MISMATCH = "value_mismatch"
    NEEDS_REVIEW_NOT_COMPARABLE = "needs_review_not_comparable"
    EXCLUDED_NOT_COMPARABLE = "excluded_not_comparable"


DIFF_REPORT_COLUMNS: tuple[str, ...] = (
    "key",
    "school_name",
    "school_id",
    "fiscal_year",
    "department_name",
    "metric",
    "extracted_value",
    "expected_value",
    "match_status",
    "mismatch_reason",
    "review_status",
    "original_value",
    "corrected_value",
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

_DiffKey = tuple[str, str, int, str]


@dataclass(frozen=True)
class MasterExpectedRow:
    school_name: str
    school_id: str | None
    fiscal_year: int
    department_name: str
    metric: str
    expected_value: int | float | str | None
    source_sheet: str | None = None
    source_cell: str | None = None


@dataclass(frozen=True)
class DiffResultRow:
    key: str
    school_name: str
    school_id: str | None
    fiscal_year: int
    department_name: str
    metric: str
    extracted_value: int | float | str | None
    expected_value: int | float | str | None
    match_status: MatchStatus
    mismatch_reason: str
    review_status: ReviewStatus | None
    original_value: int | None
    corrected_value: int | None
    confidence: float | None
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


def load_master_expected_subset(
    master_path: Path | str,
    *,
    corporation_name: str,
    school_name: str,
    fiscal_year: int,
    school_id: str | None = None,
    prefecture: str | None = None,
) -> list[MasterExpectedRow]:
    """Load one school/FY expected subset from data/master.xlsx read-only."""
    rows = load_master_metric_rows(
        master_path,
        corporation_name=corporation_name,
        school_name=school_name,
        fiscal_year=fiscal_year,
        prefecture=prefecture,
    )
    expected: list[MasterExpectedRow] = []
    for row in rows:
        expected.append(
            MasterExpectedRow(
                school_name=school_name,
                school_id=school_id,
                fiscal_year=row.fiscal_year,
                department_name=_department_name_from_master_key(row.department_key),
                metric=row.metric,
                expected_value=row.value,
                source_sheet=row.source_sheet,
                source_cell=row.source_cell,
            )
        )
    return expected


def diff_reviewed_against_master(
    reviewed_rows: list[ReviewedExtractionRow],
    expected_rows: list[MasterExpectedRow],
) -> list[DiffResultRow]:
    expected_by_key = {_expected_key(row): row for row in expected_rows}
    seen_keys: set[_DiffKey] = set()
    results: list[DiffResultRow] = []

    for row in reviewed_rows:
        if not row.metric or not row.department_name:
            continue
        key = _reviewed_key(row)
        seen_keys.add(key)
        expected = expected_by_key.get(key)
        if row.review_status == ReviewStatus.EXCLUDED:
            results.append(_diff_row(row, expected, MatchStatus.EXCLUDED_NOT_COMPARABLE, "review_status=excluded"))
            continue
        if row.final_review_value is None:
            results.append(
                _diff_row(row, expected, MatchStatus.NEEDS_REVIEW_NOT_COMPARABLE, "no final reviewed value")
            )
            continue
        if expected is None:
            results.append(_diff_row(row, None, MatchStatus.MISSING_IN_MASTER, "stable key absent from master subset"))
            continue
        if _values_equal(row.final_review_value, expected.expected_value):
            results.append(_diff_row(row, expected, MatchStatus.MATCH, "reviewed value matches master"))
            continue
        results.append(_diff_row(row, expected, MatchStatus.VALUE_MISMATCH, "reviewed value differs from master"))

    for key, expected in sorted(expected_by_key.items(), key=lambda item: item[0]):
        if key in seen_keys:
            continue
        results.append(_missing_extraction_row(expected))

    return results


def diff_summary(rows: list[DiffResultRow]) -> dict[str, int]:
    counts = {status.value: 0 for status in MatchStatus}
    for row in rows:
        counts[row.match_status.value] += 1
    return counts


def diff_report_csv(rows: list[DiffResultRow]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=DIFF_REPORT_COLUMNS)
    writer.writeheader()
    writer.writerows(_diff_report_row(row) for row in rows)
    return output.getvalue()


def _reviewed_key(row: ReviewedExtractionRow) -> _DiffKey:
    return _make_key(row.school_name, row.department_name or "", row.fiscal_year, row.metric or "")


def _expected_key(row: MasterExpectedRow) -> _DiffKey:
    return _make_key(row.school_name, row.department_name, row.fiscal_year, row.metric)


def _make_key(school_name: str, department_name: str, fiscal_year: int, metric: str) -> _DiffKey:
    return (
        normalize_text(school_name),
        department_key(department_name),
        fiscal_year,
        normalize_text(metric),
    )


def _key_label(key: _DiffKey) -> str:
    return f"{key[0]}|{key[1]}|{key[2]}|{key[3]}"


def _values_equal(left: object, right: object) -> bool:
    return _comparable_value(left) == _comparable_value(right)


def _comparable_value(value: object) -> object:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if text in {"", "-", "‐", "―"}:
        return None
    try:
        return int(float(text))
    except ValueError:
        return normalize_text(str(value))


def _diff_row(
    row: ReviewedExtractionRow,
    expected: MasterExpectedRow | None,
    status: MatchStatus,
    reason: str,
) -> DiffResultRow:
    key = _reviewed_key(row)
    return DiffResultRow(
        key=_key_label(key),
        school_name=row.school_name,
        school_id=row.school_id,
        fiscal_year=row.fiscal_year,
        department_name=row.department_name or "",
        metric=row.metric or "",
        extracted_value=row.final_review_value,
        expected_value=expected.expected_value if expected is not None else None,
        match_status=status,
        mismatch_reason=reason,
        review_status=row.review_status,
        original_value=row.original_value,
        corrected_value=row.corrected_value,
        confidence=row.confidence,
        source_pdf=row.source_pdf,
        page_no=row.page_no,
        table_index=row.table_index,
        row_index=row.row_index,
        col_index=row.col_index,
        raw_label=row.raw_label,
        raw_value=row.raw_value,
        canonical_metric=row.canonical_metric,
        review_note=row.review_note,
        reviewed_by=row.reviewed_by,
        reviewed_at=row.reviewed_at,
    )


def _missing_extraction_row(expected: MasterExpectedRow) -> DiffResultRow:
    key = _expected_key(expected)
    return DiffResultRow(
        key=_key_label(key),
        school_name=expected.school_name,
        school_id=expected.school_id,
        fiscal_year=expected.fiscal_year,
        department_name=expected.department_name,
        metric=expected.metric,
        extracted_value=None,
        expected_value=expected.expected_value,
        match_status=MatchStatus.MISSING_IN_EXTRACTION,
        mismatch_reason="stable key absent from reviewed extraction rows",
        review_status=None,
        original_value=None,
        corrected_value=None,
        confidence=None,
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


def _diff_report_row(row: DiffResultRow) -> dict[str, object]:
    return {
        "key": row.key,
        "school_name": row.school_name,
        "school_id": row.school_id or "",
        "fiscal_year": row.fiscal_year,
        "department_name": row.department_name,
        "metric": row.metric,
        "extracted_value": row.extracted_value if row.extracted_value is not None else "",
        "expected_value": row.expected_value if row.expected_value is not None else "",
        "match_status": row.match_status.value,
        "mismatch_reason": row.mismatch_reason,
        "review_status": row.review_status.value if row.review_status is not None else "",
        "original_value": row.original_value if row.original_value is not None else "",
        "corrected_value": row.corrected_value if row.corrected_value is not None else "",
        "confidence": row.confidence if row.confidence is not None else "",
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


def _department_name_from_master_key(value: str) -> str:
    if "|" not in value:
        return value
    return value.split("|", 1)[1]

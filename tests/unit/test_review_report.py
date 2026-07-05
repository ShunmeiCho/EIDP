from __future__ import annotations

import csv
import io

from eidp.pipeline.extraction_review import ExtractionReviewRecord, ReviewStatus, ReviewTaskType
from eidp.pipeline.review_report import (
    normalized_review_report_csv_from_records,
    reviewed_rows_from_records,
)


def _record(
    status: ReviewStatus,
    *,
    metric: str = "capacity",
    extracted_value: int | None = 40,
    corrected_value: int | None = None,
    department_name: str | None = "テスト学科",
) -> ExtractionReviewRecord:
    return ExtractionReviewRecord(
        review_id=f"review-{status.value}-{metric}",
        task_type=ReviewTaskType.EXTRACTED_METRIC,
        intake_record_id="intake-001",
        school_name="東京テスト専門学校",
        school_id="S-001",
        fiscal_year=2025,
        source_page_url="https://example.ac.jp/disclosure/",
        source_pdf="pdfs/intake-001.pdf",
        department_name=department_name,
        field_category="商業実務",
        course_name="専門課程",
        metric=metric,
        extracted_value=extracted_value,
        corrected_value=corrected_value,
        confidence=0.91,
        page_no=2,
        table_index=1,
        row_index=3,
        col_index=4,
        raw_label="収容定員",
        raw_value=str(extracted_value) if extracted_value is not None else None,
        canonical_metric=metric,
        review_status=status,
        review_note="checked",
        reviewed_by="operator-a",
        reviewed_at="2026-07-05T00:00:00+00:00",
        next_action=None,
        created_at_utc="2026-07-05T00:00:00+00:00",
        updated_at_utc="2026-07-05T00:00:00+00:00",
    )


def test_accepted_rows_use_original_value() -> None:
    row = reviewed_rows_from_records([_record(ReviewStatus.ACCEPTED, extracted_value=40)])[0]

    assert row.original_value == 40
    assert row.corrected_value is None
    assert row.final_review_value == 40


def test_corrected_rows_use_corrected_value_and_preserve_original() -> None:
    row = reviewed_rows_from_records(
        [_record(ReviewStatus.CORRECTED, extracted_value=40, corrected_value=42)]
    )[0]

    assert row.original_value == 40
    assert row.corrected_value == 42
    assert row.final_review_value == 42


def test_needs_review_and_excluded_rows_do_not_produce_final_values() -> None:
    rows = reviewed_rows_from_records(
        [
            _record(ReviewStatus.NEEDS_REVIEW, extracted_value=40),
            _record(ReviewStatus.EXCLUDED, extracted_value=41),
        ]
    )

    assert [row.final_review_value for row in rows] == [None, None]


def test_normalized_review_report_includes_final_value_and_evidence_columns() -> None:
    report = normalized_review_report_csv_from_records(
        [_record(ReviewStatus.CORRECTED, extracted_value=40, corrected_value=42)]
    )
    rows = list(csv.DictReader(io.StringIO(report)))

    assert rows[0]["school_name"] == "東京テスト専門学校"
    assert rows[0]["department_name"] == "テスト学科"
    assert rows[0]["field_category"] == "商業実務"
    assert rows[0]["course_name"] == "専門課程"
    assert rows[0]["metric"] == "capacity"
    assert rows[0]["original_value"] == "40"
    assert rows[0]["corrected_value"] == "42"
    assert rows[0]["final_review_value"] == "42"
    assert rows[0]["review_status"] == "corrected"
    assert rows[0]["source_pdf"] == "pdfs/intake-001.pdf"
    assert rows[0]["page_no"] == "2"
    assert rows[0]["table_index"] == "1"
    assert rows[0]["row_index"] == "3"
    assert rows[0]["col_index"] == "4"
    assert rows[0]["review_note"] == "checked"
    assert rows[0]["reviewed_by"] == "operator-a"

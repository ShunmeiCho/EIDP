from __future__ import annotations

import csv
import io

from eidp.pipeline.double_check_compare import (
    DoubleCheckStatus,
    compare_external_to_reviewed,
    double_check_report_csv,
)
from eidp.pipeline.external_extraction_import import ExternalExtractionRow, ExternalSourceSystem
from eidp.pipeline.extraction_review import ExtractionReviewRecord, ReviewStatus, ReviewTaskType
from eidp.pipeline.review_report import reviewed_rows_from_records


def _record(
    status: ReviewStatus,
    *,
    review_id: str = "review-001",
    school_name: str = "東京テスト専門学校",
    department_name: str = "テスト学科",
    metric: str = "enrollment",
    extracted_value: int | None = 37,
    corrected_value: int | None = None,
) -> ExtractionReviewRecord:
    return ExtractionReviewRecord(
        review_id=review_id,
        task_type=ReviewTaskType.EXTRACTED_METRIC,
        intake_record_id="intake-001",
        school_name=school_name,
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
        confidence=0.92,
        page_no=1,
        table_index=2,
        row_index=3,
        col_index=4,
        raw_label="在学者数",
        raw_value=str(extracted_value) if extracted_value is not None else None,
        canonical_metric=metric,
        review_status=status,
        review_note="reviewed",
        reviewed_by="operator-a",
        reviewed_at="2026-07-05T00:00:00+00:00",
        next_action=None,
        created_at_utc="2026-07-05T00:00:00+00:00",
        updated_at_utc="2026-07-05T00:00:00+00:00",
    )


def _external(
    *,
    school_name: str = "東京テスト専門学校",
    department_name: str = "テスト学科",
    metric: str = "enrollment",
    value: int | float | str | None = 37,
    source_system: ExternalSourceSystem = ExternalSourceSystem.COPILOT,
    source_row_number: int = 2,
) -> ExternalExtractionRow:
    return ExternalExtractionRow(
        school_name=school_name,
        school_id="S-001",
        corporation_name="学校法人テスト",
        prefecture="東京都",
        field_category="商業実務",
        course_name="専門課程",
        department_name=department_name,
        fiscal_year=2025,
        metric=metric,
        value=value,
        source_system=source_system,
        source_file="copilot.csv",
        source_row_number=source_row_number,
        notes="checked",
    )


def _reviewed(*records: ExtractionReviewRecord):
    return reviewed_rows_from_records(list(records))


def test_exact_matches_return_true_match() -> None:
    result = compare_external_to_reviewed(
        _reviewed(_record(ReviewStatus.ACCEPTED, extracted_value=37)),
        [_external(value=37)],
    )

    assert len(result) == 1
    assert result[0].comparison_status == DoubleCheckStatus.MATCH
    assert result[0].comparison_result == "TRUE"
    assert result[0].eidp_value == 37
    assert result[0].external_value == 37
    assert not result[0].excel_ready


def test_value_mismatches_return_false_and_preserve_both_values() -> None:
    result = compare_external_to_reviewed(
        _reviewed(_record(ReviewStatus.CORRECTED, extracted_value=37, corrected_value=41)),
        [_external(value=40)],
    )

    assert result[0].comparison_status == DoubleCheckStatus.VALUE_MISMATCH
    assert result[0].comparison_result == "FALSE"
    assert result[0].original_value == 37
    assert result[0].corrected_value == 41
    assert result[0].eidp_value == 41
    assert result[0].external_value == 40
    assert not result[0].excel_ready


def test_missing_rows_are_categorized() -> None:
    result = compare_external_to_reviewed(
        _reviewed(_record(ReviewStatus.ACCEPTED, department_name="EIDPのみ学科", extracted_value=10)),
        [_external(department_name="外部のみ学科", value=20)],
    )

    assert {row.comparison_status for row in result} == {
        DoubleCheckStatus.MISSING_IN_EIDP,
        DoubleCheckStatus.MISSING_IN_EXTERNAL,
    }
    assert all(row.comparison_result == "FALSE" for row in result)


def test_ambiguous_reviewed_keys_are_not_comparable() -> None:
    result = compare_external_to_reviewed(
        _reviewed(
            _record(ReviewStatus.ACCEPTED, review_id="review-a", extracted_value=37),
            _record(ReviewStatus.CORRECTED, review_id="review-b", extracted_value=38, corrected_value=39),
        ),
        [_external(value=37)],
    )

    assert [row.comparison_status for row in result] == [
        DoubleCheckStatus.AMBIGUOUS_KEY_NOT_COMPARABLE,
        DoubleCheckStatus.AMBIGUOUS_KEY_NOT_COMPARABLE,
    ]
    assert all(row.comparison_result == "" for row in result)
    assert all(not row.excel_ready for row in result)


def test_duplicate_external_keys_are_not_comparable() -> None:
    result = compare_external_to_reviewed(
        _reviewed(_record(ReviewStatus.ACCEPTED, extracted_value=37)),
        [_external(value=37, source_row_number=2), _external(value=38, source_row_number=3)],
    )

    assert len(result) == 1
    assert result[0].comparison_status == DoubleCheckStatus.AMBIGUOUS_KEY_NOT_COMPARABLE
    assert result[0].comparison_result == ""
    assert result[0].mismatch_reason == "duplicate external rows=2"


def test_needs_review_and_excluded_rows_are_not_comparable() -> None:
    result = compare_external_to_reviewed(
        _reviewed(
            _record(ReviewStatus.NEEDS_REVIEW, review_id="needs", department_name="要確認学科", extracted_value=37),
            _record(ReviewStatus.EXCLUDED, review_id="excluded", department_name="除外学科", extracted_value=12),
        ),
        [
            _external(department_name="要確認学科", value=37),
            _external(department_name="除外学科", value=12),
        ],
    )

    assert {row.comparison_status for row in result} == {
        DoubleCheckStatus.NEEDS_REVIEW_NOT_COMPARABLE,
        DoubleCheckStatus.EXCLUDED_NOT_COMPARABLE,
    }
    assert all(row.comparison_result == "" for row in result)
    assert all(not row.excel_ready for row in result)


def test_comparison_report_includes_eidp_external_and_evidence_columns() -> None:
    result = compare_external_to_reviewed(
        _reviewed(_record(ReviewStatus.CORRECTED, extracted_value=37, corrected_value=41)),
        [_external(value=40, source_system=ExternalSourceSystem.NOTEBOOKLM)],
    )
    report = double_check_report_csv(result)
    rows = list(csv.DictReader(io.StringIO(report)))

    assert rows[0]["comparison_result"] == "FALSE"
    assert rows[0]["comparison_status"] == "value_mismatch"
    assert rows[0]["excel_ready"] == "False"
    assert rows[0]["eidp_value"] == "41"
    assert rows[0]["external_value"] == "40"
    assert rows[0]["source_system"] == "notebooklm"
    assert rows[0]["source_file"] == "copilot.csv"
    assert rows[0]["source_row_number"] == "2"
    assert rows[0]["source_pdf"] == "pdfs/intake-001.pdf"
    assert rows[0]["page_no"] == "1"
    assert rows[0]["table_index"] == "2"
    assert rows[0]["row_index"] == "3"
    assert rows[0]["col_index"] == "4"
    assert rows[0]["raw_label"] == "在学者数"
    assert rows[0]["raw_value"] == "37"
    assert rows[0]["canonical_metric"] == "enrollment"

from __future__ import annotations

import csv
import io
from pathlib import Path

from eidp.pipeline.extraction_review import ExtractionReviewRecord, ReviewStatus, ReviewTaskType
from eidp.pipeline.review_master_diff import (
    MasterExpectedRow,
    MatchStatus,
    diff_report_csv,
    diff_reviewed_against_master,
    load_master_expected_subset,
)
from eidp.pipeline.review_report import reviewed_rows_from_records


def _record(
    status: ReviewStatus,
    *,
    school_name: str = "東京テスト専門学校",
    department_name: str = "テスト学科",
    metric: str = "enrollment",
    extracted_value: int | None = 37,
    corrected_value: int | None = None,
) -> ExtractionReviewRecord:
    return ExtractionReviewRecord(
        review_id=f"review-{status.value}-{department_name}-{metric}",
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


def _expected(
    *,
    school_name: str = "東京テスト専門学校",
    department_name: str = "テスト学科",
    metric: str = "enrollment",
    expected_value: int | None = 37,
) -> MasterExpectedRow:
    return MasterExpectedRow(
        school_name=school_name,
        school_id="S-001",
        fiscal_year=2025,
        department_name=department_name,
        metric=metric,
        expected_value=expected_value,
        field_category="商業実務",
        course_name=None,
        day_or_evening="昼",
        duration_years="2",
        master_row_id="学科別!3",
        operator_mapping_id=None,
        source_sheet="学科別",
        source_cell="H3",
    )


def _reviewed(*records: ExtractionReviewRecord):
    return reviewed_rows_from_records(list(records))


def test_exact_matches_are_detected() -> None:
    diff = diff_reviewed_against_master(
        _reviewed(_record(ReviewStatus.ACCEPTED, extracted_value=37)),
        [_expected(expected_value=37)],
    )

    assert len(diff) == 1
    assert diff[0].match_status == MatchStatus.MATCH
    assert diff[0].extracted_value == 37
    assert diff[0].expected_value == 37


def test_value_mismatches_use_corrected_value() -> None:
    diff = diff_reviewed_against_master(
        _reviewed(_record(ReviewStatus.CORRECTED, extracted_value=37, corrected_value=41)),
        [_expected(expected_value=40)],
    )

    assert diff[0].match_status == MatchStatus.VALUE_MISMATCH
    assert diff[0].original_value == 37
    assert diff[0].corrected_value == 41
    assert diff[0].extracted_value == 41
    assert diff[0].expected_value == 40


def test_missing_rows_on_either_side_are_detected() -> None:
    diff = diff_reviewed_against_master(
        _reviewed(_record(ReviewStatus.ACCEPTED, department_name="抽出のみ学科", extracted_value=10)),
        [_expected(department_name="masterのみ学科", expected_value=20)],
    )

    assert {row.match_status for row in diff} == {
        MatchStatus.MISSING_IN_MASTER,
        MatchStatus.MISSING_IN_EXTRACTION,
    }


def test_needs_review_and_excluded_rows_are_not_comparable() -> None:
    diff = diff_reviewed_against_master(
        _reviewed(
            _record(ReviewStatus.NEEDS_REVIEW, department_name="要確認学科", extracted_value=37),
            _record(ReviewStatus.EXCLUDED, department_name="除外学科", extracted_value=12),
        ),
        [
            _expected(department_name="要確認学科", expected_value=37),
            _expected(department_name="除外学科", expected_value=12),
        ],
    )

    assert [row.match_status for row in diff] == [
        MatchStatus.NEEDS_REVIEW_NOT_COMPARABLE,
        MatchStatus.EXCLUDED_NOT_COMPARABLE,
    ]
    assert all(row.extracted_value is None for row in diff)


def test_diff_report_includes_evidence_columns() -> None:
    diff = diff_reviewed_against_master(
        _reviewed(_record(ReviewStatus.CORRECTED, extracted_value=37, corrected_value=41)),
        [_expected(expected_value=40)],
    )
    report = diff_report_csv(diff)
    rows = list(csv.DictReader(io.StringIO(report)))

    assert rows[0]["match_status"] == "value_mismatch"
    assert rows[0]["field_category"] == "商業実務"
    assert rows[0]["course_name"] == "専門課程"
    assert rows[0]["source_pdf"] == "pdfs/intake-001.pdf"
    assert rows[0]["page_no"] == "1"
    assert rows[0]["table_index"] == "2"
    assert rows[0]["row_index"] == "3"
    assert rows[0]["col_index"] == "4"
    assert rows[0]["raw_label"] == "在学者数"
    assert rows[0]["raw_value"] == "37"
    assert rows[0]["canonical_metric"] == "enrollment"
    assert rows[0]["reviewed_by"] == "operator-a"
    assert rows[0]["master_row_id"] == "学科別!3"


def test_duplicate_master_keys_are_ambiguous_not_silently_overwritten() -> None:
    diff = diff_reviewed_against_master(
        _reviewed(_record(ReviewStatus.ACCEPTED, extracted_value=37)),
        [
            _expected(expected_value=37),
            _expected(expected_value=40),
        ],
    )

    assert len(diff) == 1
    assert diff[0].match_status == MatchStatus.AMBIGUOUS_KEY
    assert diff[0].expected_value is None
    assert diff[0].mismatch_reason == "duplicate master rows=2"


def test_duplicate_reviewed_keys_are_ambiguous() -> None:
    diff = diff_reviewed_against_master(
        _reviewed(
            _record(ReviewStatus.ACCEPTED, extracted_value=37),
            _record(ReviewStatus.CORRECTED, extracted_value=38, corrected_value=39),
        ),
        [_expected(expected_value=37)],
    )

    assert [row.match_status for row in diff] == [MatchStatus.AMBIGUOUS_KEY, MatchStatus.AMBIGUOUS_KEY]
    assert all(row.mismatch_reason == "duplicate reviewed rows=2" for row in diff)


def test_cross_side_course_granularity_collision_is_ambiguous_not_false_match() -> None:
    # A reviewed 'ビジネスコース' (a course track) and a master 'ビジネス' (its parent 科) collapse to
    # the same loose department_key, so the diff joins them 1:1. With equal values that produced a
    # false MATCH before the strict-key guard. It MUST now be AMBIGUOUS_KEY -- two distinct
    # granularities are not the same department and cannot be certified as matching.
    diff = diff_reviewed_against_master(
        _reviewed(_record(ReviewStatus.ACCEPTED, department_name="ビジネスコース", extracted_value=100)),
        [_expected(department_name="ビジネス", expected_value=100)],
    )
    assert [row.match_status for row in diff] == [MatchStatus.AMBIGUOUS_KEY]
    assert "granularity collision" in diff[0].mismatch_reason


def test_identity_preserving_suffix_variant_still_matches() -> None:
    # The guard must NOT over-flag the designed master(学科-suffixed)/PDF(bare) spelling variation:
    # master '情報システム学科' vs reviewed '情報システム' share the strict key, so equal values stay
    # a clean MATCH.
    diff = diff_reviewed_against_master(
        _reviewed(_record(ReviewStatus.ACCEPTED, department_name="情報システム", extracted_value=42)),
        [_expected(department_name="情報システム学科", expected_value=42)],
    )
    assert [row.match_status for row in diff] == [MatchStatus.MATCH]


def test_load_master_expected_subset_reads_xlsx_without_writing(tmp_path: Path) -> None:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "学科別"
    ws.append([None] * 7 + ["2019年度", None, None])
    ws.append(["都道府県", "法人名", "学校名", "課程名", "学科名", "昼夜", "年限", "収定", "在籍", "留学生"])
    ws.append(["東京都", "学校法人テスト", "東京テスト専門学校", "商業実務", "テスト学科", "昼", "2", 40, 37, 3])
    path = tmp_path / "master.xlsx"
    wb.save(path)
    wb.close()
    before = path.read_bytes()

    expected = load_master_expected_subset(
        path,
        corporation_name="学校法人テスト",
        school_name="東京テスト専門学校",
        fiscal_year=2019,
        school_id="S-001",
    )

    assert path.read_bytes() == before
    assert {row.metric: row.expected_value for row in expected} == {
        "capacity": 40,
        "enrollment": 37,
        "intl_students": 3,
    }
    assert {row.department_name for row in expected} == {"テスト学科"}
    assert {row.field_category for row in expected} == {"商業実務"}
    assert {row.master_row_id for row in expected} == {"学科別!3"}
    assert {row.source_cell for row in expected} == {"H3", "I3", "J3"}
    assert all(row.school_name == "東京テスト専門学校" for row in expected)

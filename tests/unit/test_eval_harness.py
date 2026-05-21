"""Tests for the PDF parser evaluation harness.

Tests the gold set loading, matching logic, and scoring
without requiring pdfplumber (no actual PDF parsing).
"""

from __future__ import annotations

from pathlib import Path

from eidp.pdf.eval_harness import (
    EvalResult,
    FieldScore,
    _compare_numeric,
    _match_department_name,
    _normalize_text,
    evaluate_parser,
    load_all_gold_annotations,
    load_gold_annotation,
    run_full_evaluation,
)
from eidp.pdf.schema import SchoolAnnotation

GOLD_DIR = Path(__file__).resolve().parents[2] / "data" / "gold-set"
PDF_DIR = Path(__file__).resolve().parents[2] / "data" / "sample-pdfs"


class TestNormalizeText:
    def test_strips_whitespace(self) -> None:
        assert _normalize_text("  hello  world  ") == "helloworld"

    def test_nfkc_fullwidth(self) -> None:
        # Full-width A -> half-width A
        assert _normalize_text("\uff21\uff29") == "AI"

    def test_japanese_unchanged(self) -> None:
        assert _normalize_text("情報処理科") == "情報処理科"

    def test_mixed_whitespace(self) -> None:
        assert _normalize_text("A I システム科") == "AIシステム科"


class TestMatchDepartmentName:
    def test_exact_match(self) -> None:
        assert _match_department_name("情報処理科", "情報処理科")

    def test_whitespace_variations(self) -> None:
        assert _match_department_name("AIシステム科", "A I システム科")

    def test_substring_match(self) -> None:
        assert _match_department_name("電気工学科", "電気工学科（昼間部）")

    def test_no_match(self) -> None:
        assert not _match_department_name("情報処理科", "電気工学科")


class TestCompareNumeric:
    def test_exact_int(self) -> None:
        assert _compare_numeric(100, 100)

    def test_different_int(self) -> None:
        assert not _compare_numeric(100, 101)

    def test_float_tolerance(self) -> None:
        assert _compare_numeric(8.2, 8.2)
        assert _compare_numeric(8.2, 8.205, tolerance=0.01)
        assert not _compare_numeric(8.2, 8.3, tolerance=0.01)


class TestLoadGoldAnnotations:
    def test_load_single(self) -> None:
        annotation = load_gold_annotation(GOLD_DIR / "tohogakuen.json")
        assert annotation.school_name == "東放学園専門学校"
        assert annotation.school_type == "専門学校"
        assert len(annotation.departments) == 5

    def test_load_jec(self) -> None:
        annotation = load_gold_annotation(GOLD_DIR / "jec.json")
        assert annotation.school_name == "日本電子専門学校"
        assert len(annotation.departments) == 24

    def test_load_tca(self) -> None:
        annotation = load_gold_annotation(GOLD_DIR / "tca.json")
        assert annotation.school_name == "東京コミュニケーションアート専門学校"
        assert len(annotation.departments) >= 5

    def test_load_nkz(self) -> None:
        annotation = load_gold_annotation(GOLD_DIR / "nkz.json")
        assert annotation.school_name == "HAL東京"
        assert len(annotation.departments) >= 3

    def test_load_all(self) -> None:
        annotations = load_all_gold_annotations(GOLD_DIR)
        assert len(annotations) == 4
        assert "jec" in annotations
        assert "tohogakuen" in annotations
        assert "tca" in annotations
        assert "nkz" in annotations

    def test_department_fields_present(self) -> None:
        annotation = load_gold_annotation(GOLD_DIR / "tohogakuen.json")
        dept = annotation.departments[0]
        assert dept.name == "放送芸術科"
        assert dept.capacity == 240
        assert dept.enrollment == 187
        assert dept.intl_students == 9
        assert dept.graduates == 118
        assert dept.advanced == 3
        assert dept.employed == 101
        assert dept.other == 14
        assert dept.prev_enrollment == 237
        assert dept.dropouts == 13
        assert dept.dropout_rate == 5.5


class TestFieldScore:
    def test_accuracy_zero_total(self) -> None:
        score = FieldScore(field_name="test", total=0, correct=0)
        assert score.accuracy == 0.0

    def test_accuracy_perfect(self) -> None:
        score = FieldScore(field_name="test", total=10, correct=10)
        assert score.accuracy == 1.0

    def test_accuracy_partial(self) -> None:
        score = FieldScore(field_name="test", total=10, correct=7)
        assert abs(score.accuracy - 0.7) < 0.001

    def test_to_dict(self) -> None:
        score = FieldScore(field_name="capacity", total=5, correct=4)
        d = score.to_dict()
        assert d["field"] == "capacity"
        assert d["total"] == 5
        assert d["correct"] == 4
        assert d["accuracy"] == 0.8


class TestEvalResult:
    def test_dept_recall(self) -> None:
        result = EvalResult(
            school_name="Test",
            source_pdf="test.pdf",
            gold_dept_count=10,
            matched_dept_count=8,
        )
        assert abs(result.dept_recall - 0.8) < 0.001

    def test_dept_precision(self) -> None:
        result = EvalResult(
            school_name="Test",
            source_pdf="test.pdf",
            parsed_dept_count=12,
            matched_dept_count=8,
        )
        assert abs(result.dept_precision - 8.0 / 12.0) < 0.001

    def test_zero_counts(self) -> None:
        result = EvalResult(school_name="Test", source_pdf="test.pdf")
        assert result.dept_recall == 0.0
        assert result.dept_precision == 0.0


def _make_perfect_parser(
    gold_dir: Path,
) -> callable:
    """Create a parser that returns the gold annotation itself (perfect score)."""

    def parse_fn(pdf_path: Path) -> SchoolAnnotation:
        stem = pdf_path.stem
        return load_gold_annotation(gold_dir / f"{stem}.json")

    return parse_fn


class TestEvaluateParser:
    def test_perfect_parser(self) -> None:
        """A parser that returns exactly the gold data should score 100%."""
        parse_fn = _make_perfect_parser(GOLD_DIR)
        result = evaluate_parser(parse_fn, "tohogakuen", GOLD_DIR, PDF_DIR)

        assert result.school_name_correct
        assert result.fiscal_year_correct
        assert result.dept_recall == 1.0
        assert result.dept_precision == 1.0
        assert result.matched_dept_count == 5

        for f_name, score in result.field_scores.items():
            assert score.accuracy == 1.0, f"Field {f_name} not perfect"

    def test_empty_parser(self) -> None:
        """A parser that returns nothing should score 0%."""

        def empty_parser(pdf_path: Path) -> SchoolAnnotation:
            return SchoolAnnotation(
                school_name="",
                fiscal_year="",
                source_pdf=pdf_path.name,
                departments=[],
            )

        result = evaluate_parser(empty_parser, "tohogakuen", GOLD_DIR, PDF_DIR)
        assert not result.school_name_correct
        assert not result.fiscal_year_correct
        assert result.dept_recall == 0.0
        assert result.matched_dept_count == 0

    def test_partial_parser(self) -> None:
        """A parser that finds some departments should have partial recall."""

        def partial_parser(pdf_path: Path) -> SchoolAnnotation:
            gold = load_gold_annotation(GOLD_DIR / f"{pdf_path.stem}.json")
            return SchoolAnnotation(
                school_name=gold.school_name,
                fiscal_year=gold.fiscal_year,
                source_pdf=gold.source_pdf,
                departments=gold.departments[:2],
            )

        result = evaluate_parser(partial_parser, "tohogakuen", GOLD_DIR, PDF_DIR)
        assert result.school_name_correct
        assert result.matched_dept_count == 2
        assert result.gold_dept_count == 5
        assert abs(result.dept_recall - 0.4) < 0.001


class TestRunFullEvaluation:
    def test_perfect_across_all(self) -> None:
        """Perfect parser should score 100% across all PDFs."""
        parse_fn = _make_perfect_parser(GOLD_DIR)
        results = run_full_evaluation(parse_fn, GOLD_DIR, PDF_DIR)

        assert len(results) == 4
        for result in results:
            assert result.dept_recall == 1.0
            assert result.school_name_correct

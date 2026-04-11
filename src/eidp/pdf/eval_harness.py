"""Evaluation harness for PDF parser accuracy.

Loads gold annotations from data/gold-set/, runs a parser function
against the corresponding PDF, and reports precision/recall per field.

Usage:
    from eidp.pdf.eval_harness import evaluate_parser, run_full_evaluation

    # Evaluate a single PDF
    result = evaluate_parser(parse_fn, "jec", gold_dir, pdf_dir)

    # Evaluate all gold set PDFs
    results = run_full_evaluation(parse_fn, gold_dir, pdf_dir)
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from eidp.pdf.schema import DepartmentRecord, SchoolAnnotation


# Fields to evaluate on each DepartmentRecord
NUMERIC_FIELDS: tuple[str, ...] = (
    "capacity",
    "enrollment",
    "intl_students",
    "graduates",
    "advanced",
    "employed",
    "other",
    "prev_enrollment",
    "dropouts",
    "dropout_rate",
)

TEXT_FIELDS: tuple[str, ...] = (
    "name",
    "course_name",
    "day_or_evening",
)

INT_FIELDS: tuple[str, ...] = (
    "duration_years",
)

ALL_FIELDS: tuple[str, ...] = TEXT_FIELDS + INT_FIELDS + NUMERIC_FIELDS


@dataclass(frozen=True)
class FieldScore:
    """Evaluation score for a single field across all departments."""

    field_name: str
    total: int = 0
    correct: int = 0
    errors: list[dict] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        if self.total == 0:
            return 0.0
        return self.correct / self.total

    def to_dict(self) -> dict:
        return {
            "field": self.field_name,
            "total": self.total,
            "correct": self.correct,
            "accuracy": round(self.accuracy, 4),
            "errors": self.errors,
        }


@dataclass(frozen=True)
class MatchResult:
    """Result of matching a parsed department to a gold department."""

    gold_name: str
    parsed_name: str | None
    matched: bool
    field_scores: dict[str, bool] = field(default_factory=dict)


@dataclass
class EvalResult:
    """Complete evaluation result for one PDF."""

    school_name: str
    source_pdf: str
    gold_dept_count: int = 0
    parsed_dept_count: int = 0
    matched_dept_count: int = 0
    field_scores: dict[str, FieldScore] = field(default_factory=dict)
    school_name_correct: bool = False
    fiscal_year_correct: bool = False

    @property
    def dept_recall(self) -> float:
        """Fraction of gold departments found in parsed output."""
        if self.gold_dept_count == 0:
            return 0.0
        return self.matched_dept_count / self.gold_dept_count

    @property
    def dept_precision(self) -> float:
        """Fraction of parsed departments that match a gold department."""
        if self.parsed_dept_count == 0:
            return 0.0
        return self.matched_dept_count / self.parsed_dept_count

    def summary(self) -> dict:
        return {
            "school_name": self.school_name,
            "source_pdf": self.source_pdf,
            "school_name_correct": self.school_name_correct,
            "fiscal_year_correct": self.fiscal_year_correct,
            "departments": {
                "gold": self.gold_dept_count,
                "parsed": self.parsed_dept_count,
                "matched": self.matched_dept_count,
                "recall": round(self.dept_recall, 4),
                "precision": round(self.dept_precision, 4),
            },
            "fields": {
                name: score.to_dict()
                for name, score in self.field_scores.items()
            },
        }


def _normalize_text(text: str) -> str:
    """Normalize Japanese text for comparison.

    Strips whitespace, normalizes full-width/half-width characters,
    and removes common formatting differences.
    """
    import unicodedata

    normalized = unicodedata.normalize("NFKC", text)
    # Remove all whitespace for comparison
    normalized = "".join(normalized.split())
    return normalized


def _match_department_name(gold_name: str, parsed_name: str) -> bool:
    """Check if department names match, allowing for minor variations."""
    g = _normalize_text(gold_name)
    p = _normalize_text(parsed_name)
    if g == p:
        return True
    # Allow substring match (parsed name contains gold name or vice versa)
    if g in p or p in g:
        return True
    return False


def _compare_numeric(
    gold_val: int | float,
    parsed_val: int | float,
    tolerance: float = 0.01,
) -> bool:
    """Compare numeric values with tolerance for floats."""
    if isinstance(gold_val, float) or isinstance(parsed_val, float):
        return math.isclose(float(gold_val), float(parsed_val), abs_tol=tolerance)
    return gold_val == parsed_val


def _find_best_match(
    gold_dept: DepartmentRecord,
    parsed_depts: list[DepartmentRecord],
    used_indices: set[int],
) -> int | None:
    """Find the best matching parsed department for a gold department.

    Returns the index into parsed_depts, or None if no match found.
    """
    for idx, parsed in enumerate(parsed_depts):
        if idx in used_indices:
            continue
        if _match_department_name(gold_dept.name, parsed.name):
            return idx
    return None


def load_gold_annotation(gold_path: Path) -> SchoolAnnotation:
    """Load a gold annotation from a JSON file."""
    with open(gold_path, encoding="utf-8") as f:
        data = json.load(f)
    return SchoolAnnotation.model_validate(data)


def load_all_gold_annotations(gold_dir: Path) -> dict[str, SchoolAnnotation]:
    """Load all gold annotations from a directory.

    Returns a dict keyed by stem name (e.g. 'jec', 'tohogakuen').
    """
    annotations: dict[str, SchoolAnnotation] = {}
    for path in sorted(gold_dir.glob("*.json")):
        annotations[path.stem] = load_gold_annotation(path)
    return annotations


def evaluate_parser(
    parse_fn: Callable[[Path], SchoolAnnotation],
    gold_key: str,
    gold_dir: Path,
    pdf_dir: Path,
) -> EvalResult:
    """Evaluate a parser function against a gold annotation.

    Args:
        parse_fn: A callable that takes a PDF path and returns a SchoolAnnotation.
        gold_key: The key name (e.g. 'jec') for the gold annotation.
        gold_dir: Directory containing gold JSON files.
        pdf_dir: Directory containing sample PDF files.

    Returns:
        An EvalResult with per-field precision/recall.
    """
    gold_path = gold_dir / f"{gold_key}.json"
    gold = load_gold_annotation(gold_path)

    pdf_path = pdf_dir / gold.source_pdf
    parsed = parse_fn(pdf_path)

    result = EvalResult(
        school_name=gold.school_name,
        source_pdf=gold.source_pdf,
        gold_dept_count=len(gold.departments),
        parsed_dept_count=len(parsed.departments),
    )

    # Compare school-level fields
    result.school_name_correct = _normalize_text(gold.school_name) == _normalize_text(
        parsed.school_name
    )
    result.fiscal_year_correct = _normalize_text(gold.fiscal_year) == _normalize_text(
        parsed.fiscal_year
    )

    # Initialize field scores
    field_totals: dict[str, int] = {f: 0 for f in ALL_FIELDS}
    field_correct: dict[str, int] = {f: 0 for f in ALL_FIELDS}
    field_errors: dict[str, list[dict]] = {f: [] for f in ALL_FIELDS}

    # Match departments
    used_parsed_indices: set[int] = set()
    matched_count = 0

    for gold_dept in gold.departments:
        match_idx = _find_best_match(gold_dept, parsed.departments, used_parsed_indices)
        if match_idx is None:
            # Gold department not found -- count all fields as missed
            for f in ALL_FIELDS:
                field_totals[f] += 1
                field_errors[f].append({
                    "gold_dept": gold_dept.name,
                    "parsed_dept": None,
                    "gold_value": getattr(gold_dept, f),
                    "parsed_value": None,
                    "reason": "department_not_found",
                })
            continue

        matched_count += 1
        used_parsed_indices.add(match_idx)
        parsed_dept = parsed.departments[match_idx]

        # Compare each field
        for f in ALL_FIELDS:
            gold_val = getattr(gold_dept, f)
            parsed_val = getattr(parsed_dept, f)
            field_totals[f] += 1

            if f in TEXT_FIELDS:
                is_correct = _normalize_text(str(gold_val)) == _normalize_text(
                    str(parsed_val)
                )
            elif f in NUMERIC_FIELDS:
                is_correct = _compare_numeric(gold_val, parsed_val)
            else:
                is_correct = gold_val == parsed_val

            if is_correct:
                field_correct[f] += 1
            else:
                field_errors[f].append({
                    "gold_dept": gold_dept.name,
                    "parsed_dept": parsed_dept.name,
                    "gold_value": gold_val,
                    "parsed_value": parsed_val,
                })

    result.matched_dept_count = matched_count

    # Build final FieldScore objects (immutable)
    result.field_scores = {
        f: FieldScore(
            field_name=f,
            total=field_totals[f],
            correct=field_correct[f],
            errors=field_errors[f],
        )
        for f in ALL_FIELDS
    }

    return result


def run_full_evaluation(
    parse_fn: Callable[[Path], SchoolAnnotation],
    gold_dir: Path,
    pdf_dir: Path,
) -> list[EvalResult]:
    """Run evaluation across all gold set annotations.

    Args:
        parse_fn: A callable that takes a PDF path and returns a SchoolAnnotation.
        gold_dir: Directory containing gold JSON files.
        pdf_dir: Directory containing sample PDF files.

    Returns:
        A list of EvalResult, one per gold annotation.
    """
    gold_annotations = load_all_gold_annotations(gold_dir)
    results: list[EvalResult] = []

    for key in gold_annotations:
        result = evaluate_parser(parse_fn, key, gold_dir, pdf_dir)
        results.append(result)

    return results


def print_eval_report(results: list[EvalResult]) -> None:
    """Print a human-readable evaluation report."""
    print("=" * 72)
    print("PDF Parser Evaluation Report")
    print("=" * 72)

    total_gold = 0
    total_matched = 0
    aggregate_field_totals: dict[str, int] = {f: 0 for f in ALL_FIELDS}
    aggregate_field_correct: dict[str, int] = {f: 0 for f in ALL_FIELDS}

    for result in results:
        print(f"\n--- {result.school_name} ({result.source_pdf}) ---")
        print(f"  School name correct: {result.school_name_correct}")
        print(f"  Fiscal year correct: {result.fiscal_year_correct}")
        print(
            f"  Departments: {result.matched_dept_count}/{result.gold_dept_count} "
            f"matched (recall={result.dept_recall:.1%}, "
            f"precision={result.dept_precision:.1%})"
        )
        print("  Field accuracy:")

        total_gold += result.gold_dept_count
        total_matched += result.matched_dept_count

        for f_name in ALL_FIELDS:
            score = result.field_scores[f_name]
            aggregate_field_totals[f_name] += score.total
            aggregate_field_correct[f_name] += score.correct
            marker = " *" if score.accuracy < 1.0 and score.total > 0 else ""
            print(
                f"    {f_name:25s}: "
                f"{score.correct:3d}/{score.total:3d} "
                f"({score.accuracy:.1%}){marker}"
            )

    # Aggregate summary
    print("\n" + "=" * 72)
    print("AGGREGATE SUMMARY")
    print("=" * 72)
    overall_recall = total_matched / total_gold if total_gold > 0 else 0.0
    print(f"  Department recall: {total_matched}/{total_gold} ({overall_recall:.1%})")
    print("  Field accuracy (across all schools):")
    for f_name in ALL_FIELDS:
        t = aggregate_field_totals[f_name]
        c = aggregate_field_correct[f_name]
        acc = c / t if t > 0 else 0.0
        print(f"    {f_name:25s}: {c:3d}/{t:3d} ({acc:.1%})")
    print("=" * 72)

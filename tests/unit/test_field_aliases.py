"""Slice 1 (RED->GREEN): field-label aliases so 生徒/学生 (seito/gakusei) and
common synonym variants all canonicalize to the same metric.

Motivation (verified): extractor.py hard-codes 生徒総定員/生徒実員 (seito) but the
大原 part-5 disclosure table uses 学生総定員数/学生実員 (gakusei), so substring
matching silently misses it. This module is the deployment-agnostic no-regret fix.
"""

import pytest

from eidp.pdf.field_aliases import canonicalize_metric_label


@pytest.mark.parametrize(
    "label,expected",
    [
        # capacity == 総定員 (seito AND gakusei spellings)
        ("生徒総定員数", "capacity"),
        ("学生総定員数", "capacity"),
        ("生徒総定員", "capacity"),
        ("学生総定員", "capacity"),
        ("収容定員", "capacity"),
        # enrollment == 実員 / 在籍
        ("生徒実員", "enrollment"),
        ("学生実員", "enrollment"),
        ("在籍者数", "enrollment"),
        # international students
        ("うち留学生数", "intl_students"),
        ("留学生数", "intl_students"),
        ("外国人留学生数", "intl_students"),
        # outcomes
        ("卒業者数", "graduates"),
        ("退学者の数", "dropouts"),
        ("中途退学者数", "dropouts"),
    ],
)
def test_canonicalizes_seito_and_gakusei_labels(label: str, expected: str) -> None:
    assert canonicalize_metric_label(label) == expected


def test_nfkc_normalizes_fullwidth_and_whitespace() -> None:
    # full-width / stray spaces from broken table cells must still canonicalize
    assert canonicalize_metric_label("　学生総定員数　") == "capacity"
    assert canonicalize_metric_label("学 生 実 員") == "enrollment"


def test_admission_capacity_is_not_conflated_with_total_capacity() -> None:
    # 入学定員 (annual admission quota) != 収容定員/総定員 (total capacity).
    # Guard against a silent conflation that would corrupt the capacity metric.
    assert canonicalize_metric_label("入学定員") == "admission_capacity"
    assert canonicalize_metric_label("入学定員") != "capacity"


@pytest.mark.parametrize("label", ["専任教員数", "兼任教員数", "総教員数", "分野", "課程名", ""])
def test_teacher_and_non_metric_labels_do_not_map_to_enrollment(label: str) -> None:
    # 大原 part-5 tables carry teacher-staffing columns; they must NOT be read as
    # enrollment/capacity. Unknown labels return None (never a wrong metric).
    result = canonicalize_metric_label(label)
    assert result not in {"capacity", "enrollment", "intl_students"}
    assert result is None

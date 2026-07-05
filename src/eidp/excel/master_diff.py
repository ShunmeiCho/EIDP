"""Pure 5-category diff of extracted metric rows against master metric rows (Slice 4b).

Categories: exact_match / value_mismatch / missing_actual (master has it, extractor
does not) / unexpected_actual (extractor has it, master does not -- the "89 unmatched"
class) / ambiguous_key (a key maps to >1 rows on either side and cannot be resolved).
ambiguous_key is BLOCKING: it must never pass silently, because an unresolved
school/campus/department/year key means the diff cannot prove correctness.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from eidp.excel.master_loader import MasterMetricRow

__all__ = ["DiffEntry", "MetricDiffResult", "diff_metric_rows"]

CATEGORIES = (
    "exact_match",
    "value_mismatch",
    "missing_actual",
    "unexpected_actual",
    "ambiguous_key",
)
_FAILURE_CATEGORIES = frozenset(CATEGORIES) - {"exact_match"}

_MetricKey = tuple[str, str | None, str, int, str]


def _key(row: MasterMetricRow) -> _MetricKey:
    return (row.school_key, row.campus_key, row.department_key, row.fiscal_year, row.metric)


def _values_equal(expected: object, actual: object, tolerance: int) -> bool:
    if expected is None and actual is None:
        return True
    if expected is None or actual is None:
        return False
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return abs(expected - actual) <= tolerance
    return expected == actual


@dataclass(frozen=True)
class DiffEntry:
    key: _MetricKey
    category: str
    expected_value: object = None
    actual_value: object = None


@dataclass(frozen=True)
class MetricDiffResult:
    entries: tuple[DiffEntry, ...]
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def has_failures(self) -> bool:
        return any(self.counts.get(c, 0) > 0 for c in _FAILURE_CATEGORIES)

    @property
    def is_blocking(self) -> bool:
        return self.counts.get("ambiguous_key", 0) > 0


def diff_metric_rows(
    expected: list[MasterMetricRow],
    actual: list[MasterMetricRow],
    *,
    numeric_tolerance: int = 0,
) -> MetricDiffResult:
    expected_by: dict[_MetricKey, list[MasterMetricRow]] = defaultdict(list)
    actual_by: dict[_MetricKey, list[MasterMetricRow]] = defaultdict(list)
    for row in expected:
        expected_by[_key(row)].append(row)
    for row in actual:
        actual_by[_key(row)].append(row)

    entries: list[DiffEntry] = []
    counts = dict.fromkeys(CATEGORIES, 0)
    for key in sorted(set(expected_by) | set(actual_by), key=repr):
        exp_rows = expected_by.get(key, [])
        act_rows = actual_by.get(key, [])
        if len(exp_rows) > 1 or len(act_rows) > 1:
            category = "ambiguous_key"
            entry = DiffEntry(key, category)
        elif exp_rows and not act_rows:
            category = "missing_actual"
            entry = DiffEntry(key, category, expected_value=exp_rows[0].value)
        elif act_rows and not exp_rows:
            category = "unexpected_actual"
            entry = DiffEntry(key, category, actual_value=act_rows[0].value)
        else:
            exp_value = exp_rows[0].value
            act_value = act_rows[0].value
            category = (
                "exact_match"
                if _values_equal(exp_value, act_value, numeric_tolerance)
                else "value_mismatch"
            )
            entry = DiffEntry(key, category, expected_value=exp_value, actual_value=act_value)
        counts[category] += 1
        entries.append(entry)

    return MetricDiffResult(entries=tuple(entries), counts=counts)

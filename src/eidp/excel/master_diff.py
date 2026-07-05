"""Pure 5-category diff of extracted metric rows against master metric rows (Slice 4b)
plus the Rung-1 acceptance gate (Rung 1a decision).

Categories: exact_match / value_mismatch / missing_actual (master has it, extractor
does not) / unexpected_actual (extractor has it, master does not -- the "89 unmatched"
class) / ambiguous_key (a key maps to >1 rows on either side and cannot be resolved).
ambiguous_key is BLOCKING.

Gate policy (metric_policy): HARD_GATE_METRICS (enrollment, intl_students) must be all
exact_match and there must be no ambiguity; RECONCILIATION_METRICS (capacity) mismatches
are surfaced as a reconciliation report, NEVER a silent pass/fail and never auto-applied.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from eidp.excel.master_loader import MasterMetricRow
from eidp.excel.metric_policy import HARD_GATE_METRICS, RECONCILIATION_METRICS

__all__ = [
    "DiffEntry",
    "GateReport",
    "MetricDiffResult",
    "ReconciliationRow",
    "build_reconciliation_report",
    "diff_metric_rows",
    "rung_gate",
]

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

    @property
    def metric(self) -> str:
        return self.key[4]


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
    counts: dict[str, int] = dict.fromkeys(CATEGORIES, 0)
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


# ----- Rung-1 acceptance gate + capacity reconciliation (Rung 1a decision) -----


@dataclass(frozen=True)
class GateReport:
    passed: bool
    status: str  # "pass" | "pass_with_reconciliation" | "fail"
    gate_failures: tuple[DiffEntry, ...]
    reconciliation: tuple[DiffEntry, ...]


def rung_gate(
    result: MetricDiffResult,
    *,
    gate_metrics: frozenset[str] = HARD_GATE_METRICS,
    reconcile_metrics: frozenset[str] = RECONCILIATION_METRICS,
) -> GateReport:
    """Rung-1 acceptance: gate_metrics must all be exact_match and no ambiguity.

    Non-gate (reconciliation) metric mismatches are returned as reconciliation items,
    NOT gate failures. ambiguous_key on any metric is always a gate failure.
    """
    gate_failures: list[DiffEntry] = []
    reconciliation: list[DiffEntry] = []
    for entry in result.entries:
        if entry.category == "ambiguous_key":
            gate_failures.append(entry)
        elif entry.metric in gate_metrics and entry.category != "exact_match":
            gate_failures.append(entry)
        elif entry.metric in reconcile_metrics and entry.category == "value_mismatch":
            reconciliation.append(entry)
    passed = not gate_failures
    if not passed:
        status = "fail"
    elif reconciliation:
        status = "pass_with_reconciliation"
    else:
        status = "pass"
    return GateReport(passed, status, tuple(gate_failures), tuple(reconciliation))


@dataclass(frozen=True)
class ReconciliationRow:
    school_key: str
    campus_key: str | None
    department_key: str
    fiscal_year: int
    metric: str
    master_value: object
    pdf_value: object
    delta: int | float | None
    classification: str
    operator_decision: str


def build_reconciliation_report(
    result: MetricDiffResult,
    *,
    reconcile_metrics: frozenset[str] = RECONCILIATION_METRICS,
) -> list[ReconciliationRow]:
    """Emit one reconciliation row per reconciliation-metric value_mismatch, keeping the
    official PDF value and the master value side by side (never auto-resolved)."""
    rows: list[ReconciliationRow] = []
    for entry in result.entries:
        if entry.metric not in reconcile_metrics or entry.category != "value_mismatch":
            continue
        master_value = entry.expected_value
        pdf_value = entry.actual_value
        delta = (
            pdf_value - master_value
            if isinstance(pdf_value, (int, float)) and isinstance(master_value, (int, float))
            else None
        )
        rows.append(
            ReconciliationRow(
                school_key=entry.key[0],
                campus_key=entry.key[1],
                department_key=entry.key[2],
                fiscal_year=entry.key[3],
                metric=entry.metric,
                master_value=master_value,
                pdf_value=pdf_value,
                delta=delta,
                classification="capacity_cross_source_delta",
                operator_decision="needs_owner_decision",
            )
        )
    return rows

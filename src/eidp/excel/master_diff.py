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
from dataclasses import dataclass, field, replace

from eidp.excel.master_loader import MasterMetricRow
from eidp.excel.metric_policy import HARD_GATE_METRICS, RECONCILIATION_METRICS

__all__ = [
    "DepartmentCollisionRow",
    "DiffEntry",
    "GateReport",
    "MetricDiffResult",
    "ReconciliationArtifacts",
    "ReconciliationRow",
    "TaxonomyReconciliationRow",
    "align_department_fields",
    "build_reconciliation_artifacts",
    "build_reconciliation_report",
    "detect_department_key_collisions",
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
        elif entry.metric in reconcile_metrics and entry.category != "exact_match":
            # Any non-exact reconcile-metric entry (value_mismatch AND missing/unexpected) is
            # surfaced as a non-blocking reconciliation, never dropped (G4 fall-through fix).
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


# ----- 分野-agnostic department alignment + taxonomy reconciliation (Rung 1b decision) -----


@dataclass(frozen=True)
class TaxonomyReconciliationRow:
    school_key: str
    campus_key: str | None
    department_gakka: str  # the 学科 key, 分野-agnostic
    fiscal_year: int
    master_field: str  # canonical 分野 as filed in master
    pdf_field: str  # canonical 分野 as read from the official PDF
    classification: str
    operator_decision: str


_ALIGN_SENTINEL = "*"
_AlignScope = tuple[str, str | None, int]


def _split_dept_key(department_key: str) -> tuple[str, str]:
    field_part, sep, gakka = department_key.partition("|")
    return (field_part, gakka) if sep else ("", department_key)


def _bunya_by_gakka(rows: list[MasterMetricRow]) -> dict[_AlignScope, dict[str, set[str]]]:
    out: dict[_AlignScope, dict[str, set[str]]] = {}
    for row in rows:
        field_part, gakka = _split_dept_key(row.department_key)
        scope = (row.school_key, row.campus_key, row.fiscal_year)
        out.setdefault(scope, {}).setdefault(gakka, set()).add(field_part)
    return out


def align_department_fields(
    expected: list[MasterMetricRow],
    actual: list[MasterMetricRow],
) -> tuple[list[MasterMetricRow], list[MasterMetricRow], list[TaxonomyReconciliationRow]]:
    """Join master and PDF on 学科 identity when their 分野 disagrees (Rung 1b decision).

    Within each (school, campus, fiscal_year) scope, a 学科 key that maps to at most one 分野
    on BOTH sides is collapsed to a 分野-agnostic key so equal values still join even when
    master files the dept under a different 分野 than the PDF (e.g. 公務員学科 under 文化教養
    vs 商業実務). A 学科 that appears under >1 分野 on the same side is a genuine collision and
    keeps its full 分野|学科 key (compose_department_key's collision protection is preserved).
    Emits one TaxonomyReconciliationRow per collapsed dept whose master/PDF 分野 differ; these
    are NON-blocking (surfaced for owner decision, never auto-resolved).
    """
    exp_map = _bunya_by_gakka(expected)
    act_map = _bunya_by_gakka(actual)

    def collapsible(scope: _AlignScope, gakka: str) -> bool:
        exp_fields = exp_map.get(scope, {}).get(gakka, set())
        act_fields = act_map.get(scope, {}).get(gakka, set())
        return len(exp_fields) <= 1 and len(act_fields) <= 1

    def rewrite(rows: list[MasterMetricRow]) -> list[MasterMetricRow]:
        out: list[MasterMetricRow] = []
        for row in rows:
            _field, gakka = _split_dept_key(row.department_key)
            scope = (row.school_key, row.campus_key, row.fiscal_year)
            if collapsible(scope, gakka):
                out.append(replace(row, department_key=f"{_ALIGN_SENTINEL}|{gakka}"))
            else:
                out.append(row)
        return out

    taxonomy: list[TaxonomyReconciliationRow] = []
    seen: set[tuple[_AlignScope, str]] = set()
    for row in expected:
        _field, gakka = _split_dept_key(row.department_key)
        scope = (row.school_key, row.campus_key, row.fiscal_year)
        if (scope, gakka) in seen or not collapsible(scope, gakka):
            continue
        master_fields = exp_map[scope][gakka]
        pdf_fields = act_map.get(scope, {}).get(gakka, set())
        if not pdf_fields:  # dept absent from PDF -> a missing_actual diff, not a 分野 delta
            continue
        master_field = next(iter(master_fields))
        pdf_field = next(iter(pdf_fields))
        if master_field != pdf_field:
            seen.add((scope, gakka))
            taxonomy.append(
                TaxonomyReconciliationRow(
                    school_key=row.school_key,
                    campus_key=row.campus_key,
                    department_gakka=gakka,
                    fiscal_year=row.fiscal_year,
                    master_field=master_field,
                    pdf_field=pdf_field,
                    classification="field_taxonomy_cross_source_delta",
                    operator_decision="needs_owner_decision",
                )
            )
    return rewrite(expected), rewrite(actual), taxonomy


# ----- Guardrail G2: loose-key department-uniqueness invariant -----


@dataclass(frozen=True)
class DepartmentCollisionRow:
    """A 学科 key that is NOT a unique department identifier within a (school, campus, FY)
    scope -- it maps to >1 分野 on one side, so a loose (分野-agnostic) join is unsafe and
    must block. Surfaced for human disambiguation; never silently loose-matched."""

    school_key: str
    campus_key: str | None
    department_gakka: str
    fiscal_year: int
    fields: tuple[str, ...]  # the >=2 分野 the 学科 is filed under on the offending side
    side: str  # "master" | "pdf"


def detect_department_key_collisions(
    expected: list[MasterMetricRow],
    actual: list[MasterMetricRow],
) -> list[DepartmentCollisionRow]:
    """Flag every 学科 key that maps to >1 分野 on a side (loose-key uniqueness violation)."""
    out: list[DepartmentCollisionRow] = []
    for side, rows in (("master", expected), ("pdf", actual)):
        for scope, gakka_map in _bunya_by_gakka(rows).items():
            for gakka, fields in gakka_map.items():
                if len(fields) > 1:
                    out.append(
                        DepartmentCollisionRow(
                            school_key=scope[0],
                            campus_key=scope[1],
                            department_gakka=gakka,
                            fiscal_year=scope[2],
                            fields=tuple(sorted(fields)),
                            side=side,
                        )
                    )
    return out


# ----- Guardrail G4: structured reconciliation artifacts -----


@dataclass(frozen=True)
class ReconciliationArtifacts:
    """Every non-exact outcome consolidated into typed, owner-visible buckets so nothing is
    silently dropped: reconcile-metric (capacity) deltas, 分野-taxonomy deltas, and hard-gate
    value_mismatches (the master_expected_error class, e.g. 06 在籍 91 vs official PDF 92)."""

    capacity: tuple[ReconciliationRow, ...]
    taxonomy: tuple[TaxonomyReconciliationRow, ...]
    hard_gate_discrepancies: tuple[DiffEntry, ...]


def build_reconciliation_artifacts(
    result: MetricDiffResult,
    taxonomy: list[TaxonomyReconciliationRow],
    *,
    gate_metrics: frozenset[str] = HARD_GATE_METRICS,
    reconcile_metrics: frozenset[str] = RECONCILIATION_METRICS,
) -> ReconciliationArtifacts:
    """Bundle capacity reconciliations, 分野-taxonomy reconciliations, and hard-gate
    value_mismatches into one structured, auditable artifact."""
    capacity = tuple(build_reconciliation_report(result, reconcile_metrics=reconcile_metrics))
    hard_gate = tuple(
        e for e in result.entries if e.metric in gate_metrics and e.category == "value_mismatch"
    )
    return ReconciliationArtifacts(
        capacity=capacity,
        taxonomy=tuple(taxonomy),
        hard_gate_discrepancies=hard_gate,
    )

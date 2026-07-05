"""Rung-1 acceptance gate + capacity reconciliation (Rung 1a decision).

enrollment / intl_students are the hard gate; capacity (収容定員 vs 生徒総定員数) is a
reconciliation metric that must NOT fail the gate but MUST be surfaced with both values.
"""

from eidp.excel.master_diff import (
    build_reconciliation_report,
    diff_metric_rows,
    rung_gate,
)
from eidp.excel.master_loader import MasterMetricRow


def _row(dept: str, metric: str, value: object) -> MasterMetricRow:
    return MasterMetricRow(
        school_key="大原学園", campus_key="札幌校", department_key=dept, fiscal_year=2025,
        metric=metric, value=value, source_sheet="学科別", source_cell=None,
    )


def _result(expected: list, actual: list):
    return diff_metric_rows(expected, actual)


def test_capacity_mismatch_does_not_fail_the_gate() -> None:
    expected = [_row("商業実務|会計2年制", "enrollment", 104), _row("商業実務|会計2年制", "capacity", 140)]
    actual = [_row("商業実務|会計2年制", "enrollment", 104), _row("商業実務|会計2年制", "capacity", 120)]
    gate = rung_gate(_result(expected, actual))
    assert gate.passed is True
    assert gate.status == "pass_with_reconciliation"
    assert len(gate.reconciliation) == 1
    assert not gate.gate_failures


def test_enrollment_mismatch_fails_the_gate() -> None:
    expected = [_row("商業実務|会計2年制", "enrollment", 104)]
    actual = [_row("商業実務|会計2年制", "enrollment", 100)]
    gate = rung_gate(_result(expected, actual))
    assert gate.passed is False
    assert gate.status == "fail"
    assert len(gate.gate_failures) == 1


def test_intl_students_mismatch_fails_the_gate() -> None:
    expected = [_row("商業実務|会計2年制", "intl_students", 0)]
    actual = [_row("商業実務|会計2年制", "intl_students", 2)]
    assert rung_gate(_result(expected, actual)).passed is False


def test_ambiguous_key_fails_the_gate_even_on_reconcile_metric() -> None:
    expected = [_row("商業実務|会計2年制", "capacity", 140), _row("商業実務|会計2年制", "capacity", 150)]
    actual = [_row("商業実務|会計2年制", "capacity", 120)]
    gate = rung_gate(_result(expected, actual))
    assert gate.passed is False
    assert any(e.category == "ambiguous_key" for e in gate.gate_failures)


def test_clean_result_is_plain_pass() -> None:
    rows = [_row("商業実務|会計2年制", "enrollment", 104), _row("商業実務|会計2年制", "intl_students", 0)]
    gate = rung_gate(_result(rows, list(rows)))
    assert gate.passed is True
    assert gate.status == "pass"
    assert not gate.reconciliation


def test_reconciliation_report_keeps_both_values_and_flags_owner() -> None:
    expected = [_row("商業実務|会計2年制", "capacity", 140)]
    actual = [_row("商業実務|会計2年制", "capacity", 120)]
    report = build_reconciliation_report(_result(expected, actual))
    assert len(report) == 1
    row = report[0]
    assert row.master_value == 140
    assert row.pdf_value == 120
    assert row.delta == -20
    assert row.classification == "capacity_cross_source_delta"
    assert row.operator_decision == "needs_owner_decision"

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

script = Path(__file__).resolve().parents[2] / "scripts" / "ship_gate_contract.py"
spec = importlib.util.spec_from_file_location("ship_gate_contract", script)
assert spec is not None
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["ship_gate_contract"] = module
spec.loader.exec_module(module)


def test_ship_gate_contract_names_distinct_bootstrap_and_weekly_metrics() -> None:
    assert module.SHIP_GATE_STRICT_TARGET_AUTO_YIELD_PCT == 60.0
    assert module.SHIP_GATE_MAX_MANUAL_WORKLOAD_PCT == 30.0
    assert module.SHIP_GATE_MANUAL_WORKLOAD_OPERATOR_REVIEWABLE_PCT == 70.0
    assert module.SHIP_GATE_AUTO_YIELD_PCT == 60.0
    assert module.SHIP_GATE_OPERATOR_COVERAGE_PCT == 60.0
    assert module.SHIP_GATE_AUTO_YIELD_PCT == module.SHIP_GATE_OPERATOR_COVERAGE_PCT
    assert module.SHIP_GATE_STATUSES == frozenset({"pass", "below_gate", "not_measured"})
    assert module.BOOTSTRAP_SHIP_GATE_METRIC_BASIS == "post_bootstrap_operator_reviewable_coverage"
    assert module.WEEKLY_SHIP_GATE_METRIC_BASIS == "weekly_operator_reviewable_acquisition"
    assert module.MATURE_YEAR_SHIP_GATE_METRIC_BASIS == "mature_year_retroactive_operator_reviewable_acquisition"
    assert module.SHIP_GATE_EXCEPTION_REASONS == frozenset({"publication_lag"})
    assert module.BOOTSTRAP_SHIP_GATE_METRIC_BASIS != module.WEEKLY_SHIP_GATE_METRIC_BASIS
    assert module.MATURE_YEAR_SHIP_GATE_METRIC_BASIS != module.WEEKLY_SHIP_GATE_METRIC_BASIS


def test_ship_gate_status_from_operator_coverage_keeps_not_measured_separate_from_below_gate() -> None:
    assert module.ship_gate_status_from_operator_coverage(None) == "not_measured"
    assert module.ship_gate_status_from_operator_coverage(59.9) == "below_gate"
    assert module.ship_gate_status_from_operator_coverage(60.0) == "pass"


def test_ship_gate_status_from_yield_remains_compatibility_alias() -> None:
    assert module.ship_gate_status_from_yield(None) == module.ship_gate_status_from_operator_coverage(None)
    assert module.ship_gate_status_from_yield(59.9) == module.ship_gate_status_from_operator_coverage(59.9)
    assert module.ship_gate_status_from_yield(60.0) == module.ship_gate_status_from_operator_coverage(60.0)


def test_ship_gate_exception_reasons_are_explicit() -> None:
    assert module.is_ship_gate_exception_reason("publication_lag") is True
    assert module.is_ship_gate_exception_reason("manual_override") is False
    assert module.is_ship_gate_exception_reason(None) is False


def test_ship_gate_threshold_gaps_surface_mature_year_miscalibration() -> None:
    assert module.ship_gate_threshold_gaps(
        target_pdf_auto_yield_pct=30.0,
        operator_reviewable_yield_pct=41.0,
    ) == ("strict_auto_yield", "manual_workload")
    assert module.ship_gate_threshold_gaps(
        target_pdf_auto_yield_pct=60.0,
        operator_reviewable_yield_pct=70.0,
    ) == ()
    assert module.ship_gate_threshold_gaps(
        target_pdf_auto_yield_pct=None,
        operator_reviewable_yield_pct=None,
    ) == ()

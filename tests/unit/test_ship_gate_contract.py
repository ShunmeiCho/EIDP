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
    assert module.SHIP_GATE_AUTO_YIELD_PCT == 60.0
    assert module.SHIP_GATE_OPERATOR_COVERAGE_PCT == 60.0
    assert module.SHIP_GATE_AUTO_YIELD_PCT == module.SHIP_GATE_OPERATOR_COVERAGE_PCT
    assert module.SHIP_GATE_STATUSES == frozenset({"pass", "below_gate", "not_measured"})
    assert module.BOOTSTRAP_SHIP_GATE_METRIC_BASIS == "post_bootstrap_operator_reviewable_coverage"
    assert module.WEEKLY_SHIP_GATE_METRIC_BASIS == "weekly_operator_reviewable_acquisition"
    assert module.BOOTSTRAP_SHIP_GATE_METRIC_BASIS != module.WEEKLY_SHIP_GATE_METRIC_BASIS


def test_ship_gate_status_from_operator_coverage_keeps_not_measured_separate_from_below_gate() -> None:
    assert module.ship_gate_status_from_operator_coverage(None) == "not_measured"
    assert module.ship_gate_status_from_operator_coverage(59.9) == "below_gate"
    assert module.ship_gate_status_from_operator_coverage(60.0) == "pass"


def test_ship_gate_status_from_yield_remains_compatibility_alias() -> None:
    assert module.ship_gate_status_from_yield(None) == module.ship_gate_status_from_operator_coverage(None)
    assert module.ship_gate_status_from_yield(59.9) == module.ship_gate_status_from_operator_coverage(59.9)
    assert module.ship_gate_status_from_yield(60.0) == module.ship_gate_status_from_operator_coverage(60.0)

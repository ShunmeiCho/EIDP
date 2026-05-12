"""Shared ship-gate field contract for Windows bootstrap and weekly runs.

Keep this module stdlib-only: ``scripts/validate_install.bat`` may run the
validator before the project wheel is installed.
"""

from __future__ import annotations

BOOTSTRAP_SHIP_GATE_METRIC_BASIS = "post_bootstrap_operator_reviewable_coverage"
SHIP_GATE_AUTO_YIELD_PCT = 60.0
SHIP_GATE_OPERATOR_COVERAGE_PCT = 60.0
SHIP_GATE_STATUSES = frozenset({"pass", "below_gate", "not_measured"})
WEEKLY_SHIP_GATE_METRIC_BASIS = "weekly_operator_reviewable_acquisition"


def ship_gate_status_from_yield(yield_pct: float | None) -> str:
    if yield_pct is None:
        return "not_measured"
    return "pass" if float(yield_pct) >= SHIP_GATE_OPERATOR_COVERAGE_PCT else "below_gate"

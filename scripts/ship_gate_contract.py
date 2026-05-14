"""Shared ship-gate field contract for Windows bootstrap and weekly runs.

Keep this module stdlib-only: ``scripts/validate_install.bat`` may run the
validator before the project wheel is installed.
"""

from __future__ import annotations

BOOTSTRAP_SHIP_GATE_METRIC_BASIS = "post_bootstrap_operator_reviewable_coverage"
SHIP_GATE_OPERATOR_COVERAGE_PCT = 60.0
# Deprecated compatibility field name kept for existing JSON payloads.
SHIP_GATE_AUTO_YIELD_PCT = SHIP_GATE_OPERATOR_COVERAGE_PCT
SHIP_GATE_STATUSES = frozenset({"pass", "below_gate", "not_measured"})
WEEKLY_SHIP_GATE_METRIC_BASIS = "weekly_operator_reviewable_acquisition"


def ship_gate_status_from_operator_coverage(operator_coverage_pct: float | None) -> str:
    if operator_coverage_pct is None:
        return "not_measured"
    return "pass" if float(operator_coverage_pct) >= SHIP_GATE_OPERATOR_COVERAGE_PCT else "below_gate"


def ship_gate_status_from_yield(yield_pct: float | None) -> str:
    """Compatibility alias for older scripts and JSON field names.

    The release gate is based on operator-reviewable coverage, not strict
    auto-yield. New code should call ``ship_gate_status_from_operator_coverage``.
    """

    return ship_gate_status_from_operator_coverage(yield_pct)

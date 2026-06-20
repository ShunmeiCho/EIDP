"""Shared ship-gate field contract for Windows bootstrap and weekly runs.

Keep this module stdlib-only: ``scripts/validate_install.bat`` may run the
validator before the project wheel is installed.
"""

from __future__ import annotations

BOOTSTRAP_SHIP_GATE_METRIC_BASIS = "post_bootstrap_operator_reviewable_coverage"
# This is a strict per-fiscal-year data gate, not a broad "PDF found" rate.
SHIP_GATE_STRICT_TARGET_AUTO_YIELD_BASIS = "per_fiscal_year_strict_target_pdf_excel_ready"
SHIP_GATE_STRICT_TARGET_AUTO_YIELD_PCT = 60.0
SHIP_GATE_MAX_MANUAL_WORKLOAD_PCT = 30.0
SHIP_GATE_MANUAL_WORKLOAD_OPERATOR_REVIEWABLE_PCT = 100.0 - SHIP_GATE_MAX_MANUAL_WORKLOAD_PCT
SHIP_GATE_OPERATOR_COVERAGE_PCT = 60.0
# Deprecated compatibility field name kept for existing JSON payloads.
SHIP_GATE_AUTO_YIELD_PCT = SHIP_GATE_OPERATOR_COVERAGE_PCT
SHIP_GATE_STATUSES = frozenset({"pass", "below_gate", "not_measured"})
WEEKLY_SHIP_GATE_METRIC_BASIS = "weekly_strict_target_pdf_and_operator_reviewable_acquisition"
LEGACY_WEEKLY_SHIP_GATE_METRIC_BASES = frozenset({"weekly_operator_reviewable_acquisition"})
WEEKLY_SHIP_GATE_DENOMINATOR_SCOPE = "target_missing_schools_before_run"
MATURE_YEAR_SHIP_GATE_METRIC_BASIS = "mature_year_retroactive_strict_target_pdf_and_operator_reviewable_acquisition"
MATURE_YEAR_PROOF_MIN_DENOMINATOR = 1000
V1_RELEASE_SCHOOL_TYPE = "専門学校"
MATURE_YEAR_PROOF_SCHOOL_TYPE = V1_RELEASE_SCHOOL_TYPE
SHIP_GATE_EXCEPTION_REASONS = frozenset({"publication_lag"})
SHIP_GATE_THRESHOLD_GAPS = frozenset({"strict_auto_yield", "manual_workload"})


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


def ship_gate_status_from_weekly_metrics(
    *,
    target_pdf_auto_yield_pct: float | None,
    operator_reviewable_yield_pct: float | None,
) -> str:
    """Return weekly status from strict target-document/Excel-ready yield and workload."""

    if target_pdf_auto_yield_pct is None or operator_reviewable_yield_pct is None:
        return "not_measured"
    return (
        "pass"
        if not ship_gate_threshold_gaps(
            target_pdf_auto_yield_pct=target_pdf_auto_yield_pct,
            operator_reviewable_yield_pct=operator_reviewable_yield_pct,
        )
        else "below_gate"
    )


def is_ship_gate_exception_reason(reason: str | None) -> bool:
    return reason in SHIP_GATE_EXCEPTION_REASONS


def ship_gate_threshold_gaps(
    *,
    target_pdf_auto_yield_pct: float | None,
    operator_reviewable_yield_pct: float | None,
    min_target_pdf_auto_yield_pct: float = SHIP_GATE_STRICT_TARGET_AUTO_YIELD_PCT,
    max_manual_workload_pct: float = SHIP_GATE_MAX_MANUAL_WORKLOAD_PCT,
) -> tuple[str, ...]:
    """Return named threshold gaps without changing release-gate behavior."""

    gaps: list[str] = []
    if target_pdf_auto_yield_pct is not None and float(target_pdf_auto_yield_pct) < min_target_pdf_auto_yield_pct:
        gaps.append("strict_auto_yield")
    if operator_reviewable_yield_pct is not None:
        manual_workload_pct = 100.0 - float(operator_reviewable_yield_pct)
        if manual_workload_pct > max_manual_workload_pct + 1e-9:
            gaps.append("manual_workload")
    return tuple(gaps)

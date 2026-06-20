"""Guard release wording for EIDP's rolling fiscal-year contract."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _doc(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _normalized_doc(path: str) -> str:
    return re.sub(r"\s+", " ", _doc(path))


def test_project_rules_define_eidp_as_rolling_fiscal_year_operation() -> None:
    text = _doc("docs/governance/project-rules.md")

    assert "rolling fiscal-year" in text
    assert "not a one-year PDF scraper" in text
    assert "reused across future years" in text
    assert "scoped to an explicit `fiscal_year`" in text


def test_release_gate_defines_sixty_percent_as_strict_excel_ready_not_broad_discovery() -> None:
    text = _normalized_doc("docs/governance/release-gates.md")

    assert "rolling fiscal-year operation, not a one-year scraping run" in text
    assert "The `60%` v1 minimum is strict" in text
    assert "target application PDF identity" in text
    assert "Excel-ready" in text
    assert "not a broad PDF discovery rate" in text


def test_v1_exit_criteria_preserve_future_year_scope_without_expanding_v1() -> None:
    text = _normalized_doc("docs/release/v1-exit-criteria.md")

    assert "rolling fiscal-year workflow" in text
    assert "not complete merely because one fiscal year's PDFs were scraped once" in text
    assert "reusable across future fiscal years" in text
    assert "documents, metrics, tasks, exports, and gate evidence stay `fiscal_year`-scoped" in text
    assert "university production support" in text


def test_goal_execution_requires_lightweight_forecast_and_formal_release_checklist() -> None:
    text = _normalized_doc("docs/governance/goal-execution.md")

    assert "## Release Forecast Cadence" in text
    assert "Release Forecast: READY / RC_ONLY / NOT_READY" in text
    assert "Evidence: source head, packaged commit, latest CI, latest Windows canary" in text
    assert "P0: open release blockers" in text
    assert "full release gate checklist and evidence bundle" in text
    assert "A release forecast is not a substitute for the checklist" in text


def test_owner_signoff_is_simple_but_evidence_based() -> None:
    signoff = _normalized_doc("docs/governance/owner-release-signoff.md")
    goal_execution = _normalized_doc("docs/governance/goal-execution.md")
    release_gates = _normalized_doc("docs/governance/release-gates.md")

    assert "The sign-off form may be simple; the sign-off basis may not be simple." in signoff
    assert "release summary" in signoff
    assert "release evidence bundle" in signoff
    assert "READY`, `RC_ONLY`, or `NOT_READY`" in signoff
    assert "Operator smoke sign-off is separate from owner release approval" in signoff
    assert "it can support `RC_ONLY`" in signoff
    assert "it does not make the release `READY`" in signoff
    assert "unconfirmed rows must not enter final Excel output" in signoff
    assert "v1 may release the text-PDF workflow without requiring full automatic OCR success" in signoff
    assert "unconfirmed data entering final Excel output" in signoff

    assert "Owner sign-off should be short" in goal_execution
    assert "Owner sign-off may be a short form" in release_gates

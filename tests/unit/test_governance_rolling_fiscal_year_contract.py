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


def test_owner_decision_briefs_do_not_relax_release_gates() -> None:
    publication_lag = _normalized_doc("docs/release/owner-decisions/publication-lag.md")
    ocr_scope = _normalized_doc("docs/release/owner-decisions/ocr-scope.md")
    known_limits = _normalized_doc("docs/release/v1-known-limitations.md")

    assert "It is not approval by itself" in publication_lag
    assert "`APPROVE_RC_ONLY`" in publication_lag
    assert "at most `RC_ONLY`" in publication_lag
    assert "unconfirmed rows must not enter final Excel output" in publication_lag
    assert "old-year PDFs may be counted as current-year success" in publication_lag
    assert "successful `scripts/verify_stage6_return.py` result" in publication_lag

    assert "It is not approval by itself" in ocr_scope
    assert "`CORE_TEXT_PDF_ONLY`" in ocr_scope
    assert "`OCR_ADDON_REQUIRED`" in ocr_scope
    assert "unreviewed OCR rows must not enter final Excel output" in ocr_scope
    assert "With no OCR scope decision: `NOT_READY`" in ocr_scope
    assert "current Windows OCR proof is present" in ocr_scope

    assert "docs/release/owner-decisions/" in known_limits
    assert "The v1 OCR release scope must be explicitly selected before approval" in known_limits


def test_stage6_return_docs_wire_owner_decision_briefs_into_release_verification() -> None:
    template = _normalized_doc("docs/runbooks/eidp-operator-e2e-template.md")
    checklist = _normalized_doc("docs/runbooks/eidp-v1-release-admin-checklist.md")

    assert "docs/release/owner-decisions/publication-lag.md" in template
    assert "docs/release/owner-decisions/ocr-scope.md" in template
    assert "--publication-lag-decision-brief" in template
    assert "--ocr-scope-decision-brief" in template
    assert "canonical publication-lag brief" in template
    assert "canonical owner decision brief" in template

    assert "Stage 6 return verifier has not checked the canonical owner decision briefs" in checklist
    assert "publication_lag_decision_brief" in checklist
    assert "ocr_scope_decision_brief" in checklist
    assert "Any source/package change after v540 requires a new Windows package/canary" in checklist
    assert "Current v540 package evidence" in checklist


def test_v540_owner_handoff_is_current_but_not_release_approval() -> None:
    first_read = _normalized_doc("docs/runbooks/00-READ-ME-FIRST-v540.txt")
    request = _normalized_doc("docs/runbooks/eidp-v540-owner-request-20260620.txt")
    return_sheet = _normalized_doc("docs/runbooks/eidp-v540-owner-return-fill-sheet.md")
    release_summary = _normalized_doc("docs/runbooks/eidp-v540-release-summary.md")
    owner_signoff = _normalized_doc("docs/runbooks/eidp-v540-owner-signoff.md")
    current_status = _normalized_doc("docs/reports/current-release-status.md")
    objective_checklist = _normalized_doc("docs/reports/eidp-current-objective-evidence-checklist.md")
    r2_staging = _normalized_doc("docs/reports/2026-06-20-v540-owner-docs-r2-windows-staging.md")

    expected_sha = "6f246e47c41869dce401810731df48e99268756622719a0e59461c33fd645fd6"

    assert expected_sha in first_read
    assert expected_sha in request
    assert expected_sha in return_sheet
    assert expected_sha in release_summary
    assert expected_sha in owner_signoff
    assert "docs\\runbooks\\eidp-v540-release-summary.md" in first_read
    assert "docs\\runbooks\\eidp-v540-owner-signoff.md" in first_read
    assert "release conclusion remains NOT_READY" in request
    assert "The owner may record a NOT_READY acknowledgement" in request
    assert "This file is not v1.0 approval" in first_read
    assert "This file is not v1.0 approval" in request
    assert "It is not release approval" in return_sheet
    assert "Current release conclusion: `NOT_READY`" in release_summary
    assert "The owner signs this short form, not the engineering checklist" in owner_signoff
    assert "the supported decision is `NOT_READY`" in owner_signoff
    assert "It does not make v540 `READY`" in owner_signoff
    assert "Do not treat the v540 bounded canary as owner real-cycle sign-off" in first_read
    assert "unconfirmed rows into final Excel output" in return_sheet
    assert "Unknown-year, old-year, school-mismatch, non-target, low-confidence" in owner_signoff
    assert "docs/runbooks/00-READ-ME-FIRST-v540.txt" in current_status
    assert "docs/runbooks/eidp-v540-release-summary.md" in current_status
    assert "docs/runbooks/eidp-v540-owner-signoff.md" in current_status
    assert "docs/runbooks/eidp-v540-owner-request-20260620.txt" in current_status
    assert "docs/runbooks/eidp-v540-owner-return-fill-sheet.md" in current_status
    assert "docs/reports/2026-06-20-v540-owner-docs-r2-windows-staging.md" in current_status
    assert "Latest packaged bounded Windows canary: `dist/eidp-windows-v540.zip`" in objective_checklist
    assert "C:\\EIDP-staging\\v540-owner-docs-20260620-r2" in objective_checklist
    assert "eidp-v540-release-summary.md" in objective_checklist
    assert "eidp-v540-owner-signoff.md" in objective_checklist
    assert "Run the prepared owner/operator v540 return path" in objective_checklist
    assert "ZIP SHA256" in r2_staging
    assert "owner-signoff short-form marker: True" in r2_staging
    assert "old r1 zip exists: False" in r2_staging
    assert "scheduled task execute:" in r2_staging

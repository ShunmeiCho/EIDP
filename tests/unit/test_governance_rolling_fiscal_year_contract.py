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
    assert "Any source/package change after v541 requires a new Windows package/canary" in checklist
    assert "Current v541 package evidence" in checklist


def test_v541_owner_handoff_is_current_but_not_release_approval() -> None:
    first_read = _normalized_doc("docs/runbooks/00-READ-ME-FIRST-v541.txt")
    request = _normalized_doc("docs/runbooks/eidp-v541-owner-request-20260621.txt")
    return_sheet = _normalized_doc("docs/runbooks/eidp-v541-owner-return-fill-sheet.md")
    release_summary = _normalized_doc("docs/runbooks/eidp-v541-release-summary.md")
    owner_signoff = _normalized_doc("docs/runbooks/eidp-v541-owner-signoff.md")
    current_status = _normalized_doc("docs/reports/current-release-status.md")
    objective_checklist = _normalized_doc("docs/reports/eidp-current-objective-evidence-checklist.md")
    staging = _normalized_doc("docs/reports/2026-06-21-v541-owner-docs-windows-staging.md")

    expected_package_sha = "2ffb25884e15b9e2937f43bab7a8f5866d9434bc9f29f8067dbc1760397fa46f"
    expected_docs_sha = "4ab692e47c0077eaedac91f340a561507ebaac79277bdce9db17d28ceea6c731"

    assert expected_package_sha in first_read
    assert expected_package_sha in request
    assert expected_package_sha in return_sheet
    assert expected_package_sha in release_summary
    assert expected_package_sha in owner_signoff
    assert "docs\\runbooks\\eidp-v541-release-summary.md" in first_read
    assert "docs\\runbooks\\eidp-v541-owner-signoff.md" in first_read
    assert "release conclusion remains NOT_READY" in request
    assert "The owner may record a NOT_READY acknowledgement" in request
    assert "This file is not v1.0 approval" in first_read
    assert "This file is not v1.0 approval" in request
    assert "It is not release approval" in return_sheet
    assert "Current release conclusion: `NOT_READY`" in release_summary
    assert "The owner signs this short form, not the engineering checklist" in owner_signoff
    assert "the supported decision is `NOT_READY`" in owner_signoff
    assert "It does not make v541 `READY`" in owner_signoff
    assert "Do not treat the v541 bounded canary as owner real-cycle sign-off" in first_read
    assert "unconfirmed rows into final Excel output" in return_sheet
    assert "Unknown-year, old-year, school-mismatch, non-target, low-confidence" in owner_signoff
    assert "docs/runbooks/00-READ-ME-FIRST-v541.txt" in current_status
    assert "docs/runbooks/eidp-v541-release-summary.md" in current_status
    assert "docs/runbooks/eidp-v541-owner-signoff.md" in current_status
    assert "docs/runbooks/eidp-v541-owner-request-20260621.txt" in current_status
    assert "docs/runbooks/eidp-v541-owner-return-fill-sheet.md" in current_status
    assert "docs/reports/2026-06-21-v541-owner-docs-windows-staging.md" in current_status
    assert 'not a generic "PDF not found" or crawler-runtime failure' in current_status
    assert "FY2026/R8 strict target-document to Excel-ready yield" in current_status
    assert 'simplified to "the algorithm/model is broken"' in current_status
    assert "without counting old-year PDFs" in objective_checklist
    assert "not framed as \"the crawler cannot run\" or \"PDFs are missing\"" in objective_checklist
    assert "not framed as a generic algorithm/model failure" in objective_checklist
    assert "rejection-bucket false-reject audit" in objective_checklist
    assert "fiscal-year mismatch / publication-lag or old target" in objective_checklist
    assert "docs/reports/2026-06-21-v541-false-reject-audit-packet.md" in current_status
    assert "docs/reports/2026-06-21-v541-false-reject-audit-packet.md" in objective_checklist
    assert "docs/reports/2026-06-21-v541-false-reject-review-sheet.csv" in current_status
    assert "docs/reports/2026-06-21-v541-false-reject-review-sheet.csv" in objective_checklist
    assert "scripts/build_false_reject_audit.py" in objective_checklist
    assert "--validate-review-csv" in objective_checklist
    assert "--require-decisions" in objective_checklist
    assert "context_mismatch_count=0" in current_status
    assert "bucket_decision_counts" in objective_checklist
    assert "immutable row context" in objective_checklist
    assert "Latest packaged bounded Windows canary: `dist/eidp-windows-v541.zip`" in objective_checklist
    assert "Owner handoff docs have been refreshed to v541" in objective_checklist
    assert "C:\\EIDP-staging\\v541-owner-docs-20260621" in objective_checklist
    assert "eidp-v541-release-summary.md" in objective_checklist
    assert "eidp-v541-owner-signoff.md" in objective_checklist
    assert "Run the prepared owner/operator v541 return path" in objective_checklist
    assert expected_docs_sha in current_status
    assert expected_docs_sha in objective_checklist
    assert expected_docs_sha in staging
    assert "ZIP SHA256" in staging
    assert "owner-signoff short-form marker: True" in staging
    assert "old v540 zip exists: False" in staging
    assert "old v540 dir exists: False" in staging
    assert "scheduled task execute:" in staging
    assert "v540 r2 handoff" in current_status

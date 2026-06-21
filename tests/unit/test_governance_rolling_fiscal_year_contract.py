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
    assert "v547 still remains below the strict/Excel-ready release gate" in checklist
    assert "Current v547 package and Windows bounded canary evidence is recorded" in checklist
    assert "Previous v546 Windows bounded canary evidence is recorded" in checklist


def test_v547_owner_handoff_is_current_but_not_release_approval() -> None:
    first_read = _normalized_doc("docs/runbooks/00-READ-ME-FIRST-v547.txt")
    request = _normalized_doc("docs/runbooks/eidp-v547-owner-request-20260621.txt")
    return_sheet = _normalized_doc("docs/runbooks/eidp-v547-owner-return-fill-sheet.md")
    release_summary = _normalized_doc("docs/runbooks/eidp-v547-release-summary.md")
    owner_signoff = _normalized_doc("docs/runbooks/eidp-v547-owner-signoff.md")
    current_status = _normalized_doc("docs/reports/current-release-status.md")
    objective_checklist = _normalized_doc("docs/reports/eidp-current-objective-evidence-checklist.md")
    staging = _normalized_doc("docs/reports/2026-06-21-v547-owner-docs-windows-staging.md")

    expected_package_sha = "f167e17b89f0ff96a45c817abcfd0403a2d487eddf3fb3a85a73d866b351de4b"
    expected_source_sha = "86c848f68e1dbde85c9b6422cfc827149940e02a"
    expected_docs_sha = "6ec0507cf62820de686a18d23dbb560e2a3132cdaaabd75ef4ba616ece0eec81"

    for text in (first_read, request, return_sheet, release_summary, owner_signoff):
        assert expected_package_sha in text
        assert expected_source_sha in text
        assert "v545" not in text

    assert "docs\\reports\\2026-06-21-v547-package-gates.md" in first_read
    assert "docs\\reports\\2026-06-21-v547-false-reject-review-sheet.csv" in first_read
    assert "docs\\reports\\2026-06-21-v547-false-reject-review-worklist.md" in first_read
    assert "docs\\reports\\2026-06-21-v547-false-reject-audit-packet.md" not in first_read
    assert "GitHub main CI for packaged source commit 86c848f: success, run 27894031180" in first_read
    assert "Do not treat the v547 bounded canary as owner real-cycle sign-off" in first_read
    assert "release conclusion remains NOT_READY" in request
    assert "Current release conclusion: `NOT_READY`" in release_summary
    assert "Current release conclusion | `NOT_READY`" in owner_signoff
    assert "docs\\runbooks\\eidp-v547-owner-signoff.md" in request
    assert (
        "--false-reject-evidence-zip logs/win-v547-86c848f-canary/stage6-evidence-20260621-054545.zip"
        in return_sheet
    )
    assert "--false-reject-review-csv docs/reports/2026-06-21-v547-false-reject-review-sheet.csv" in return_sheet
    assert "It does not make v547 `READY`" in owner_signoff

    assert "latest owner/operator handoff docs have been refreshed to v547 package identity" in current_status
    assert "C:\\EIDP-staging\\v547-owner-docs-20260621" in current_status
    assert "docs/reports/2026-06-21-v547-owner-docs-windows-staging.md" in current_status
    assert "earlier v545, v544, v542, and v541 owner-docs refreshes remain historical" in current_status
    assert "Latest v547 owner/operator docs staging" in objective_checklist
    assert "The current staged owner handoff lane is now v547" in objective_checklist
    assert "still target v545 until owner docs are refreshed again" not in objective_checklist

    assert expected_docs_sha in staging
    assert "ok\": true" in staging
    assert "C:\\EIDP-staging\\v547-owner-docs-20260621" in staging
    assert "active_task" in staging
    assert "docs\\reports\\2026-06-21-v547-false-reject-review-worklist.md" in staging
    assert "EIDP-v527-69fe81f-env0\\scripts\\weekly_run.bat" in staging
    assert "This copied documentation only" in staging
    assert "does not approve v1.0" in staging


def test_v545_owner_handoff_is_historical_not_release_approval() -> None:
    first_read = _normalized_doc("docs/runbooks/00-READ-ME-FIRST-v545.txt")
    request = _normalized_doc("docs/runbooks/eidp-v545-owner-request-20260621.txt")
    return_sheet = _normalized_doc("docs/runbooks/eidp-v545-owner-return-fill-sheet.md")
    release_summary = _normalized_doc("docs/runbooks/eidp-v545-release-summary.md")
    owner_signoff = _normalized_doc("docs/runbooks/eidp-v545-owner-signoff.md")
    admin_checklist = _normalized_doc("docs/runbooks/eidp-v1-release-admin-checklist.md")
    current_status = _normalized_doc("docs/reports/current-release-status.md")
    objective_checklist = _normalized_doc("docs/reports/eidp-current-objective-evidence-checklist.md")
    objective_checklist_raw = _doc("docs/reports/eidp-current-objective-evidence-checklist.md")
    required_next_actions = objective_checklist_raw.split("## Required Next Actions", maxsplit=1)[1]
    v547_windows_canary = _normalized_doc("docs/reports/2026-06-21-v547-windows-canary.md")
    staging = _normalized_doc("docs/reports/2026-06-21-v545-owner-docs-windows-staging.md")
    historical_staging_v544 = _normalized_doc("docs/reports/2026-06-21-v544-owner-docs-windows-staging.md")
    historical_staging_v542 = _normalized_doc("docs/reports/2026-06-21-v542-owner-docs-windows-staging.md")
    historical_staging_v541 = _normalized_doc("docs/reports/2026-06-21-v541-owner-docs-windows-staging.md")
    historical_staging_v541_r3 = _normalized_doc("docs/reports/2026-06-21-v541-owner-docs-r3-windows-staging.md")

    expected_v547_package_sha = "f167e17b89f0ff96a45c817abcfd0403a2d487eddf3fb3a85a73d866b351de4b"
    expected_v547_source_sha = "86c848f68e1dbde85c9b6422cfc827149940e02a"
    expected_v546_package_sha = "ece0bbf3c1e96f3bf5be6dd553f3a547244edf15ad65ea2bc38c61600887ecfd"
    expected_v546_source_sha = "63016054f948b1f4f285c3c822197f76c25b4b7d"
    expected_package_sha = "ba4d36189d671ce59e01cf8f1bffeb0710d8d2b171376e4cbc0cb4e362f1b8d0"
    expected_source_sha = "f3eb1663c0333f296856a84f447ef2424ea77ddf"
    expected_v544_package_sha = "781da0a3c1a3f4ae80536c68de2971a1ae431a01c7eb2d58001de061f62df0c1"
    expected_v544_source_sha = "74325bc278c3e96052ef27e67cd554e426c87c60"
    expected_v543_package_sha = "c3b80835225864f57f62c33fa87cde2cdb5b2006ee2da0fdfa726cccfdc5a094"
    expected_v543_source_sha = "6aa5735d164101cbe6ec85648bcb8b6f46168c63"
    expected_v542_package_sha = "89ace547fcabf43f80b697024f5c13d1398244ad4d4b165160a489c8386f9ecc"
    expected_v542_source_sha = "d98ecd7196631a00c27aff1c240ebc7969579ce7"
    expected_docs_sha = "13a2950b14a0481bc33c8e736a091f308d2b340270aeb36ee2dbd290742bb6a7"
    expected_v544_docs_sha = "c227b2bbc1db305ac7f44e8ad6e74aa0b38f3ddd734b239b52e2d30b014c5671"
    expected_v541_docs_sha = "4ab692e47c0077eaedac91f340a561507ebaac79277bdce9db17d28ceea6c731"
    expected_v541_docs_r3_sha = "8b28d260a81f7854c4c6ecf678f7cbaaef26aa48139e4744f5d5f54dc018dc49"

    assert expected_package_sha in first_read
    assert expected_package_sha in request
    assert expected_package_sha in return_sheet
    assert expected_package_sha in release_summary
    assert expected_package_sha in owner_signoff
    assert expected_source_sha in first_read
    assert expected_source_sha in request
    assert expected_source_sha in return_sheet
    assert expected_source_sha in release_summary
    assert expected_source_sha in owner_signoff
    assert "Re-check current main before release approval" in first_read
    assert "moving \"latest docs commit\" value" in release_summary
    assert "docs-only handoff commits do not change packaged runtime" in return_sheet
    assert "re-check current main CI before release approval" in return_sheet
    assert "latest v545 false-reject review-summary docs commit" not in first_read
    assert "latest v545 false-reject review-summary docs commit" not in return_sheet
    assert "latest v545 false-reject review-summary docs commit" not in release_summary
    assert "docs\\runbooks\\eidp-v545-release-summary.md" in first_read
    assert "docs\\runbooks\\eidp-v545-owner-signoff.md" in first_read
    assert "latest false-reject worksheet triage guidance" in first_read
    assert "release conclusion remains NOT_READY" in request
    assert "The owner may record a NOT_READY acknowledgement" in request
    assert "This file is not v1.0 approval" in first_read
    assert "This file is not v1.0 approval" in request
    assert "It is not release approval" in return_sheet
    assert "Current release conclusion: `NOT_READY`" in release_summary
    assert "The owner signs this short form, not the engineering checklist" in owner_signoff
    assert "the supported decision is `NOT_READY`" in owner_signoff
    assert "It does not make v545 `READY`" in owner_signoff
    assert "Do not treat the v545 bounded canary as owner real-cycle sign-off" in first_read
    assert "unconfirmed rows into final Excel output" in return_sheet
    assert "False-Reject RCA Worksheet" in return_sheet
    assert "Fill only these columns" in return_sheet
    assert "`decision`" in return_sheet
    assert "`reviewer`" in return_sheet
    assert "`reviewed_at`" in return_sheet
    assert "`notes`" in return_sheet
    assert "Developer validation is run from current `main`" in return_sheet
    assert "review_status=complete" in return_sheet
    assert "--false-reject-evidence-zip" in return_sheet
    assert "--false-reject-review-csv" in return_sheet
    assert "--false-reject-sample-size 12" in return_sheet
    assert "False-reject worksheet rules" in request
    assert "Fill only decision/reviewer/reviewed_at/notes" in request
    assert "from the staged v545 package" in request
    assert "The v545 package proves the verifier and helper are available" in request
    assert "from the staged v545 package" in return_sheet
    assert "The v545 package proves the verifier and helper are available" in return_sheet
    assert "scripts\\verify_stage6_return.py" in request
    assert "Unknown-year, old-year, school-mismatch, non-target, low-confidence" in owner_signoff

    assert "earlier v545, v544, v542, and v541 owner-docs refreshes remain historical" in current_status
    assert "docs/runbooks/00-READ-ME-FIRST-v545.txt" not in current_status
    assert "docs/runbooks/eidp-v545-release-summary.md" not in current_status
    assert "docs/runbooks/eidp-v545-owner-signoff.md" not in current_status
    assert "docs/runbooks/eidp-v545-owner-request-20260621.txt" not in current_status
    assert "docs/runbooks/eidp-v545-owner-return-fill-sheet.md" not in current_status
    assert "Current packaged bounded Windows canary is `v547`" in current_status
    assert "docs/reports/2026-06-21-v547-package-gates.md" in current_status
    assert "logs/eidp-windows-v547-distribution-verify-20260621.json" in current_status
    assert "logs/eidp-windows-v547-release-gates-20260621.json" in current_status
    assert "logs/eidp-v547-local-prune-20260621.json" in current_status
    assert "docs/reports/2026-06-21-v547-windows-canary.md" in current_status
    assert "logs/win-v547-86c848f-canary/stage6-evidence-20260621-054545.zip" in current_status
    assert "logs/win-v547-86c848f-canary/stage6-evidence-verify-20260621-144556.json" in current_status
    assert "logs/win-v547-86c848f-canary/stage6-evidence-verify-mac-20260621.json" in current_status
    assert "logs/win-v547-86c848f-canary/20260621_053425-summary.json" in current_status
    assert "Previous packaged bounded Windows canary is `v546`" in current_status
    assert "docs/reports/2026-06-21-v546-rca-summary-package-gates.md" in current_status
    assert "logs/eidp-windows-v546-distribution-verify-20260621.json" in current_status
    assert "logs/eidp-windows-v546-release-gates-20260621.json" in current_status
    assert "logs/eidp-v546-local-prune-20260621.json" in current_status
    assert "v547` completed side-by-side Windows setup" in current_status
    assert "v546` completed side-by-side Windows setup" in current_status
    assert "strict/Excel-ready FY2026 yield `12/50 (24.0%)`" in current_status
    assert "not a PDF acquisition success rate" in current_status
    assert "not a PDF acquisition success rate or an overall project completion rate" in current_status
    assert "candidate sets were found for `50/50` selected schools" in current_status
    assert "only `12` schools reached strict target PDF plus Excel-ready" in current_status
    assert "earlier v545, v544, v542, and v541" in current_status
    assert 'not a generic "PDF not found" or crawler-runtime failure' in current_status
    assert "FY2026/R8 strict target-document to Excel-ready yield" in current_status
    assert 'simplified to "the algorithm/model is broken"' in current_status
    assert "without counting old-year PDFs" in objective_checklist
    assert "not framed as \"the crawler cannot run\" or \"PDFs are missing\"" in objective_checklist
    assert "not framed as a generic algorithm/model failure" in objective_checklist
    assert "rejection-bucket false-reject audit" in objective_checklist
    assert "fiscal-year mismatch / publication-lag or old target" in objective_checklist
    assert "The current false-reject review lane uses the v547 Windows canary evidence" in objective_checklist
    assert "staged owner handoff docs now target v547" in objective_checklist
    assert "do not prove the v547 worksheet has been completed or approved" in objective_checklist
    assert "docs/reports/2026-06-21-v545-false-reject-audit-packet.md" in current_status
    assert "docs/reports/2026-06-21-v545-false-reject-audit-packet.md" in objective_checklist
    assert "docs/reports/2026-06-21-v545-false-reject-review-sheet.csv" in current_status
    assert "docs/reports/2026-06-21-v545-false-reject-review-sheet.csv" in objective_checklist
    assert "docs/reports/2026-06-21-v545-false-reject-review-summary.md" in objective_checklist
    assert "read-only review summary" in objective_checklist
    assert "docs/reports/2026-06-21-v545-false-reject-review-validation.json" in current_status
    assert "docs/reports/2026-06-21-v545-false-reject-review-validation.json" in objective_checklist
    assert "docs/reports/2026-06-21-v545-false-reject-review-validation-summary.md" in objective_checklist
    assert "docs/reports/2026-06-21-v547-false-reject-review-sheet.csv" in current_status
    assert "docs/reports/2026-06-21-v547-false-reject-review-summary.md" in current_status
    assert "docs/reports/2026-06-21-v547-false-reject-review-validation.json" in current_status
    assert "docs/reports/2026-06-21-v547-false-reject-review-validation-summary.md" in current_status
    assert "docs/reports/2026-06-21-v547-false-reject-review-sheet.csv" in objective_checklist
    assert "docs/reports/2026-06-21-v547-false-reject-review-summary.md" in objective_checklist
    assert "docs/reports/2026-06-21-v547-false-reject-review-validation.json" in objective_checklist
    assert "docs/reports/2026-06-21-v547-false-reject-review-validation-summary.md" in objective_checklist
    assert "Review `docs/reports/2026-06-21-v547-false-reject-review-sheet.csv`" in required_next_actions
    assert "Review `docs/reports/2026-06-21-v545-false-reject-review-sheet.csv`" not in required_next_actions
    assert "current v547 blank worksheet validation is recorded" in objective_checklist
    assert "false_reject_review_summary" in current_status
    assert "false_reject_review_summary" in objective_checklist
    assert "review-rca-summary" in current_status
    assert "review-rca-summary" in objective_checklist
    assert "review-rca-summary" in return_sheet
    assert "docs/reports/2026-06-21-v545-false-reject-review-rca-summary.md" in current_status
    assert "docs/reports/2026-06-21-v545-false-reject-review-rca-summary.md" in objective_checklist
    assert "RCA conclusion=INVALID_RETURN" in current_status
    assert "RCA conclusion=INVALID_RETURN" in objective_checklist
    assert "SPECIFIC_RULE_DEFECTS_FOUND" in return_sheet
    assert "GENERIC_MODEL_FAILURE_NOT_SUPPORTED" in return_sheet
    assert "source-side handoff hardening" in objective_checklist
    assert "v547 package, non-Windows gate, and Windows canary evidence" in objective_checklist
    assert "v546 package, non-Windows gate, and Windows canary evidence" in objective_checklist
    assert "docs/reports/2026-06-21-v547-package-gates.md" in objective_checklist
    assert "docs/reports/2026-06-21-v547-windows-canary.md" in objective_checklist
    assert "logs/eidp-windows-v547-release-gates-20260621.json" in objective_checklist
    assert "logs/win-v547-86c848f-canary/stage6-evidence-20260621-054545.zip" in objective_checklist
    assert "logs/win-v547-86c848f-canary/stage6-evidence-verify-mac-20260621.json" in objective_checklist
    assert "docs/reports/2026-06-21-v546-rca-summary-package-gates.md" in objective_checklist
    assert "logs/eidp-windows-v546-release-gates-20260621.json" in objective_checklist
    assert "strict/Excel-ready `12/50 (24.0%)`" in objective_checklist
    assert "not a PDF acquisition success rate and not overall" in objective_checklist
    assert "`12/50` selected target-missing schools" in objective_checklist
    assert "`15` documents were downloaded and processed" in objective_checklist
    assert "docs/reports/2026-06-21-v544-false-reject-audit-packet.md" not in admin_checklist
    assert "dist/eidp-windows-v547.zip" in admin_checklist
    assert "dist/eidp-windows-v546.zip" in admin_checklist
    assert "v547 Windows bounded canary evidence" in admin_checklist
    assert "logs/win-v547-86c848f-canary/stage6-evidence-20260621-054545.zip" in admin_checklist
    assert "logs/win-v547-86c848f-canary/stage6-evidence-verify-mac-20260621.json" in admin_checklist
    assert "docs/reports/2026-06-21-v547-false-reject-review-sheet.csv" in admin_checklist
    assert "docs/reports/2026-06-21-v547-false-reject-review-validation.json" in admin_checklist
    assert "v546 Windows bounded canary evidence" in admin_checklist
    assert "logs/win-v546-6301605-canary/stage6-evidence-20260621-043811.zip" in admin_checklist
    assert "docs/reports/2026-06-21-v545-false-reject-audit-packet.md" in admin_checklist
    assert "docs/reports/2026-06-21-v545-false-reject-review-sheet.csv" in admin_checklist
    assert "docs/reports/2026-06-21-v545-false-reject-review-validation.json" in admin_checklist
    assert "scripts/build_false_reject_audit.py" in objective_checklist
    assert "--validate-review-csv" in objective_checklist
    assert "--require-decisions" in objective_checklist
    assert "context_mismatch_count=0" in current_status
    assert "Completed rows require `reviewer` and an ISO `reviewed_at` timestamp" in current_status
    assert "`false_reject` / `needs_operator_review` rows require `notes`" in current_status
    assert "row context must remain unchanged" in current_status
    assert "The owner-return verifier now accepts `--false-reject-evidence-zip`" in current_status
    assert "`context_mismatch_count=0`" in current_status
    assert expected_v547_package_sha in current_status
    assert expected_v547_package_sha in objective_checklist
    assert expected_v547_package_sha in admin_checklist
    assert expected_v547_source_sha in current_status
    assert expected_v547_source_sha in objective_checklist
    assert expected_v547_source_sha in admin_checklist
    assert expected_v546_package_sha in current_status
    assert expected_v546_package_sha in objective_checklist
    assert expected_v546_package_sha in admin_checklist
    assert expected_v546_source_sha in current_status
    assert expected_v546_source_sha in objective_checklist
    assert expected_v546_source_sha in admin_checklist
    assert expected_package_sha in current_status
    assert expected_package_sha in objective_checklist
    assert expected_source_sha in current_status
    assert expected_source_sha in objective_checklist
    assert expected_v544_package_sha in current_status
    assert expected_v544_package_sha in objective_checklist
    assert expected_v544_source_sha in current_status
    assert expected_v544_source_sha in objective_checklist
    assert expected_v543_package_sha in current_status
    assert expected_v543_package_sha in objective_checklist
    assert expected_v543_source_sha in current_status
    assert expected_v543_source_sha in objective_checklist
    assert expected_v542_package_sha in current_status
    assert expected_v542_source_sha in current_status
    assert "GitHub CI for packaged source commit `f3eb166`: success" in release_summary
    assert (
        "This false-reject owner-return verifier integration was first packaged and Windows-canary verified"
        in current_status
    )
    assert "docs/reports/2026-06-21-v544-triage-helper-windows-canary.md" in current_status
    assert "docs/reports/2026-06-21-v544-triage-helper-windows-canary.md" in objective_checklist
    assert "Latest packaged bounded Windows canary: `dist/eidp-windows-v547.zip`" in objective_checklist
    assert "Current v547 package contains the latest false-reject worksheet guidance" in objective_checklist
    assert "Latest bounded Windows canary: v547" in objective_checklist
    assert "The `24.0%` value is not a PDF download/acquisition success rate" in v547_windows_canary
    assert "not the overall project completion rate" in v547_windows_canary
    assert "candidate sets for `50/50` selected schools" in v547_windows_canary
    assert "downloaded `15` documents" in v547_windows_canary
    assert "only `12` schools had evidence strong enough to enter Excel-ready safely" in v547_windows_canary
    assert "If owner/operator review finds many `false_reject` rows" in v547_windows_canary
    assert "If most rows are `correct_reject`" in v547_windows_canary
    assert "If many rows remain `needs_operator_review`" in v547_windows_canary
    assert "current staged owner handoff lane" in objective_checklist
    assert "Previous v544 package/canary contains the false-reject audit helper" in objective_checklist
    assert "Current v542 package/canary contains the post-v541 false-reject owner-return" in objective_checklist
    assert "v545-owner-docs-20260621" not in current_status
    assert "docs/reports/2026-06-21-v545-owner-docs-windows-staging.md" not in current_status
    assert "bucket_decision_counts" in objective_checklist
    assert "immutable row context" in objective_checklist
    assert "required reviewer/timestamp fields" in objective_checklist
    assert "notes for `false_reject` and `needs_operator_review`" in objective_checklist
    assert "fill only `decision`, `reviewer`, `reviewed_at`, and `notes`" in objective_checklist
    assert "`scripts/verify_stage6_return.py` can validate the returned worksheet" in objective_checklist
    assert "v545-owner-docs-20260621" in objective_checklist
    assert "v545 false-reject RCA packet" in staging
    assert "read-only review summary" in staging
    assert "current-main recheck wording in first-read: True" in staging
    assert "current-main recheck wording in release summary: True" in staging
    assert "current-main recheck wording in return sheet: True" in staging
    assert "moving latest-docs commit absent in first-read: True" in staging
    assert "moving latest-docs commit absent in release summary: True" in staging
    assert "moving latest-docs commit absent in return sheet: True" in staging
    assert "docs\\reports\\2026-06-21-v545-false-reject-review-summary.md` present" in staging
    assert "review summary read-only warning: True" in staging
    assert "review summary strict yield: True" in staging
    assert "validation summary completed 0/53: True" in staging
    assert "validation summary blank 53: True" in staging
    assert "validation summary Excel warning: True" in staging
    assert "False-reject worksheet rules" in staging
    assert "return sheet verifier false-reject args: True" in staging
    assert "return sheet review summary warning: True" in staging
    assert "current-release-status NOT_READY: True" in staging
    assert "current-release-status v545 handoff: True" in staging
    assert "current-release-status review summary: True" in staging
    assert "current-release-status validation summary: True" in staging
    assert "objective checklist v545 handoff: True" in staging
    assert "objective checklist review summary: True" in staging
    assert "objective checklist validation summary: True" in staging
    assert "superseded v544 owner-docs staging absent: True" in staging
    assert "Previous packaged bounded Windows canary: `dist/eidp-windows-v543.zip`" in objective_checklist
    assert "Owner handoff docs have been refreshed to v542" in objective_checklist
    assert "C:\\EIDP-staging\\v545-owner-docs-20260621" in objective_checklist
    assert "eidp-v545-release-summary.md" in objective_checklist
    assert "eidp-v545-owner-signoff.md" in objective_checklist
    assert "Refresh owner/operator handoff docs to v545" not in objective_checklist
    assert expected_docs_sha in staging
    assert "ZIP SHA256" in staging
    assert (
        "scheduled task EIDP Weekly Run action: "
        "\"C:\\Users\\cyo20\\EIDP-v527-69fe81f-env0\\scripts\\weekly_run.bat\"" in staging
    )
    assert expected_v544_docs_sha in historical_staging_v544
    assert "v542 Owner Docs Windows Staging" in historical_staging_v542
    assert expected_v541_docs_sha in historical_staging_v541
    assert expected_v541_docs_r3_sha in historical_staging_v541_r3
    assert "Historical docs-only handoff evidence" in objective_checklist

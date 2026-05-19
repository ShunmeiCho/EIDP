# EIDP Current Objective Evidence Checklist

Updated: 2026-05-20
Branch: `sprint8-handoff-finalize`
PR: `#2`
Status: **NOT COMPLETE**

This file is the prompt-to-artifact checklist for the current long-term EIDP
objective. It intentionally replaces the older historical v464/v460 narrative
with the current v506/v502/v501 state.

## Objective Restated

EIDP is complete only when one Windows operator can process the national
vocational-school universe each rolling fiscal year by:

1. starting from the 47 prefectural official "confirmed institution" lists,
2. covering 1,700+ vocational schools,
3. discovering the current rolling target fiscal-year PDF in strict mode,
   currently FY2026/Reiwa 8, while excluding old-year fallback from success,
4. extracting rows with the PDF/OCR stack and admitting only rows with
   three-factor confidence `>= 0.70`,
5. writing `DepartmentYearly` and `SupportRecipient` append-only records,
6. transferring accepted data to the Excel template,
7. auditing all operator actions in `ManualActionLog`,
8. running offline from the Windows ZIP through double-click setup and browser
   UI, and
9. meeting the ship line: true target-form auto-acquisition `>= 60%` and
   operator manual workload `<= 30%` for the current rolling FY.

The goal is not zero-human full automation. It is a Windows one-operator flow
that keeps manual work below the release threshold.

## Current Candidate Boundary

- Current package candidate: `dist/eidp-windows-v506.zip`
- Package source commit from ZIP `BUILD_INFO.json`:
  `2d266c5f39399e71d19f12b2d99aa87f5e1333e8`
- Package SHA256:
  `f2221af5d82352085bbf470335d3c726eb9b31ce133d876ec6e4e5c74df8927e`
- Latest complete Windows side-by-side smoke: v501
- Latest partial Windows side-by-side setup/canary: v502
- Latest source/package audit-surface fix: v506 operator URL registration audit
- Release verdict: blocked by FY2026/R8 strict yield, missing v506 Windows smoke,
  missing owner real Windows cycle, and unapproved `publication_lag` exception.

Passing unit tests, package verification, and a complete Windows smoke are
necessary but not sufficient for completion. They do not by themselves prove
the current FY2026/R8 60-70% target-PDF acquisition line or owner sign-off.

## Prompt-To-Artifact Checklist

| Requirement | Evidence checked | Status |
| --- | --- | --- |
| 47 prefecture official-list seeds are packaged and usable | `logs/win-v506-stage6-v506-non-windows-release-gates-20260520.json`, result `package_verify` stdout: `prefecture_seed_rows=47`, `prefecture_seed_downloadable=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_school_rows_total=2148` | PASS |
| 1,700+ vocational-school scope | v502 Windows setup validator `logs/win-v502-stage6-v502-env0-validate-after-setup-20260520.json`: `.details.school_count=2418`, `.details.school_fiscal_year_status_count=2418`, `.details.sqlite_integrity_check="ok"`; v506 Windows setup pending | PASS via v502, v506 pending |
| Current rolling FY is FY2026/Reiwa 8 | `logs/win-v502-stage6-v502-last-run-after-weekly-canary-limit50-20260520.json`: `current_fy=2026`, `status=success` | PASS |
| Strict mode excludes old-year fallback from success | `logs/win-v485-stage6/fy2026-strict-yield-upper-bound-fail-20260519.json` and v502 `ship_gate_status=below_gate` preserve old-year exclusion instead of counting stale target forms as success | PASS for contract, FAIL for release yield |
| Current FY2026 strict target-PDF/Excel-ready yield is `>= 60%` | v502 limit-50 canary: strict/Excel-ready `10.0%`; production-scale upper-bound proof: max possible `39.3%` after 607/1000 schools | FAIL |
| Operator manual workload is `<= 30%` for current FY | v502 limit-50 operator-reviewable `84.0%` implies reviewable evidence exists, but strict Excel-ready success is still `10.0%`; owner real-cycle workload proof is missing | FAIL |
| Mature-year exception input exists | `logs/mature-year-acquisition-proof-fy2025-release-exception-v497-20260519.json`: FY2025 denominator `1000`, strict/Excel-ready `60.0%`, operator-reviewable `79.8%`, manual workload `20.2%` | PASS as exception input only |
| Publication-lag exception is approved if release uses the mature-year lane | `docs/reports/2026-05-19-publication-lag-release-exception-record.md`: `Status: NOT_APPROVED`, `Decision: NOT_APPROVED` | BLOCKED |
| PDF extraction stack is packaged | v506 package verifier stdout: `has_runtime=True`, `wheel_count=84`; v501 OCR runtime proof `logs/win-v501-stage6-v501-validate-ocr-runtime-20260520.json` is `ok=true` with Tesseract `5.4.0.20240606`, `jpn`, and `jpn_vert` | PASS for package, v506 Windows OCR runtime pending |
| Confidence `>= 0.70` gate exists | v506 full unit suite in release gate: `1886 passed`; confidence/export/review tests are covered by the unit suite | PASS for code contract, PARTIAL for production OCR corpus |
| `DepartmentYearly` and `SupportRecipient` append-only paths exist | v502 install validator confirms required tables including `department_yearly`, `support_recipient`, and `manual_action_log`; v506 unit suite is green | PASS for code/schema, PARTIAL for real operator workflow |
| Excel transfer works | v501 full smoke: `logs/win-v501-stage6-v501-excel-summary-20260520.json` is `ok=true`; v502 Excel smoke did not finish because Windows SSH reset new sessions | PASS via v501, v502 pending |
| Operator actions are auditable in `ManualActionLog` | v502 install validator confirms the table; v503 adds `operator_settings_saved` audit coverage for the settings page with API-key redaction; v504 adds `excel_preview_generated` audit coverage for Excel preview generation; v505 adds `school_year_tasks_rebuilt` audit coverage for task-board rebuilds; v506 adds `operator_url_submitted` and `operator_url_bulk_imported` audit coverage for manual URL registration; current owner real-cycle audit counts and sign-off are missing | PARTIAL, improved in v506 |
| Windows ZIP double-click setup works | v502 setup and validation: `logs/win-v502-stage6-v502-first-setup-env0-20260520.log` and `logs/win-v502-stage6-v502-env0-validate-after-setup-20260520.json` with `ok=true` | PASS |
| Browser UI runs offline on Windows | v501 UI smoke: `logs/win-v501-stage6-v501-ui-smoke-20260520.json` is `ok=true`; v502 UI smoke is pending after Windows SSH instability | PASS via v501, v502 pending |
| Active scheduled-task safety is preserved | `logs/win-v502-stage6-v502-recovery-probe-after-limit50-canary-clean-20260520.json`: `ok=true`, active weekly task still points to the expected v485 lane | PASS |
| Stage 6 evidence bundle and verifier pass | v501 evidence ZIP and verifier: `logs/win-v501-stage6-v501-stage6-evidence-20260519-182045.zip` and `logs/win-v501-stage6-v501-stage6-evidence-verify-20260520-032045.json` with `ok=true`; v502 bundle is pending | PASS via v501, v502 pending |
| v502 RCA is current | `docs/reports/2026-05-20-v502-windows-partial-side-by-side-limit50.md`: 20 RCA items across 45 candidates, buckets `8 no_pdf_candidates`, `8 publication_lag_or_old_target_pdf`, `4 target_form_without_year_evidence`; no residual `non_target_candidates_only` bucket | PASS for RCA, FAIL for yield |
| Owner real Windows cycle and sign-off are complete | No completed owner KPI/sign-off template or owner-return verifier pass is present | BLOCKED |
| PR merge and v1.0 tag are allowed | FY2026 strict proof, v506 Windows smoke, owner real cycle, and exception approval are incomplete | BLOCKED |

## Fresh Local Verification In This Audit Pass

- `uv run python -m eidp.cli eval-discovery-gold --predictions data/discovery-gold-set/expected-predictions.jsonl --json --fail-on-regression` returned 44 exact matches and 0 failures.
- `uv run pytest tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_eval.py tests/unit/test_cli_discovery_gold_set.py tests/unit/test_cli_eval_discovery_gold.py -q` returned `36 passed`.
- v503 settings-audit focused verification is recorded in `docs/reports/2026-05-20-v503-settings-audit-package.md`.
- v504 Excel-preview audit focused verification is recorded in `docs/reports/2026-05-20-v504-excel-preview-audit-package.md`.
- v505 school-year task rebuild audit focused verification is recorded in `docs/reports/2026-05-20-v505-school-task-rebuild-audit-package.md`.
- v506 operator URL registration audit focused verification is recorded in `docs/reports/2026-05-20-v506-operator-url-audit-package.md`.

These checks validate the gold-set contract used by the package verifier. They
do not remove the FY2026/R8 release blocker.

## Required Next Actions

1. Restore Windows OpenSSH/exec access or provide the current Windows IPv4.
2. Complete v506 transfer/setup, OCR runtime, UI smoke, Excel smoke, Stage 6 evidence bundle,
   evidence verifier, and final recovery.
3. Resolve the FY2026/R8 strict-yield blocker by either reaching the `>= 60%`
   current-year strict line or approving the documented `publication_lag`
   exception path.
4. Run the owner real Windows cycle and return KPI/sign-off evidence.
5. Run `scripts/verify_stage6_return.py` against the returned owner evidence.
6. Merge PR #2 and create the signed `v1.0` tag only after the above blockers
   are resolved.

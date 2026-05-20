# EIDP Current Objective Evidence Checklist

Updated: 2026-05-20
Branch: `sprint8-handoff-finalize`
PR: `#2`
Status: **NOT COMPLETE**

This file is the prompt-to-artifact checklist for the current long-term EIDP
objective. It intentionally replaces the older historical v464/v460 narrative
with the current v519/v502/v501 state.

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

- Current package candidate: `dist/eidp-windows-v519.zip`
- Package source commit from ZIP `BUILD_INFO.json`:
  `24fa09a49115196c2a977296eec127f6747e4426`
- Package SHA256:
  `fbc2ae0016b7b293c0fd534d7b3e7eb881f74205fa6df19acda42a8d21ba195a`
- Latest complete Windows side-by-side smoke: v501
- Latest partial Windows side-by-side setup/canary: v502
- Latest source/package discovery fix: v522 stale-yearless RCA bucket classification
- Latest FY2026/R8 Mac-side continuation canary:
  `docs/reports/2026-05-20-v521-mac-limit50-continuation-canary.md`
- Latest RCA reclassification report:
  `docs/reports/2026-05-20-v522-stale-yearless-rca-bucket-source.md`
- Release verdict: blocked by FY2026/R8 strict yield, missing v519 Windows smoke,
  missing owner real Windows cycle, and unapproved `publication_lag` exception.

Passing unit tests, package verification, and a complete Windows smoke are
necessary but not sufficient for completion. They do not by themselves prove
the current FY2026/R8 60-70% target-PDF acquisition line or owner sign-off.

## Prompt-To-Artifact Checklist

| Requirement | Evidence checked | Status |
| --- | --- | --- |
| 47 prefecture official-list seeds are packaged and usable | `logs/win-v519-stage6-v519-non-windows-release-gates-20260520.json`, result `package_verify` stdout: `prefecture_seed_rows=47`, `prefecture_seed_downloadable=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_school_rows_total=2148` | PASS |
| 1,700+ vocational-school scope | v502 Windows setup validator `logs/win-v502-stage6-v502-env0-validate-after-setup-20260520.json`: `.details.school_count=2418`, `.details.school_fiscal_year_status_count=2418`, `.details.sqlite_integrity_check="ok"`; v519 Windows setup pending | PASS via v502, v519 pending |
| Current rolling FY is FY2026/Reiwa 8 | `logs/win-v502-stage6-v502-last-run-after-weekly-canary-limit50-20260520.json`: `current_fy=2026`, `status=success` | PASS |
| Strict mode excludes old-year fallback from success | `logs/win-v485-stage6/fy2026-strict-yield-upper-bound-fail-20260519.json` and v502 `ship_gate_status=below_gate` preserve old-year exclusion instead of counting stale target forms as success | PASS for contract, FAIL for release yield |
| Current FY2026 strict target-PDF/Excel-ready yield is `>= 60%` | v502 limit-50 canary: strict/Excel-ready `10.0%`; v515 Mac continuation canary from the v513 isolated DB: strict `2/50 (4.0%)`; v516 target-missing canary after confirmed-target exclusion: strict `0/50 (0.0%)`; v519 Mac continuation canary with checked-in URL sources: strict `0/50 (0.0%)`; v521 Mac continuation canary after corporation suppression: strict `0/50 (0.0%)`; v522 only reclassifies RCA buckets and leaves strict `0/50 (0.0%)`; production-scale upper-bound proof: max possible `39.3%` after 607/1000 schools | FAIL |
| Operator manual workload is `<= 30%` for current FY | v502 limit-50 operator-reviewable `84.0%`; v515 Mac continuation canary operator-reviewable `50/50 (100.0%)`; v516 target-missing canary operator-reviewable `49/50 (98.0%)`; v519 Mac continuation canary operator-reviewable `50/50 (100.0%)`; v521 Mac continuation canary operator-reviewable `50/50 (100.0%)`; strict Excel-ready success is still below gate and owner real-cycle workload proof is missing | FAIL |
| Mature-year exception input exists | `logs/mature-year-acquisition-proof-fy2025-release-exception-v497-20260519.json`: FY2025 denominator `1000`, strict/Excel-ready `60.0%`, operator-reviewable `79.8%`, manual workload `20.2%` | PASS as exception input only |
| Publication-lag exception is approved if release uses the mature-year lane | `docs/reports/2026-05-19-publication-lag-release-exception-record.md`: `Status: NOT_APPROVED`, `Decision: NOT_APPROVED` | BLOCKED |
| PDF extraction stack is packaged | v519 package verifier stdout: `has_runtime=True`, `wheel_count=84`; v501 OCR runtime proof `logs/win-v501-stage6-v501-validate-ocr-runtime-20260520.json` is `ok=true` with Tesseract `5.4.0.20240606`, `jpn`, and `jpn_vert` | PASS for package, v519 Windows OCR runtime pending |
| Confidence `>= 0.70` gate exists | v519 full unit suite in release gate: `1893 passed`; confidence/export/review tests are covered by the unit suite | PASS for code contract, PARTIAL for production OCR corpus |
| `DepartmentYearly` and `SupportRecipient` append-only paths exist | v502 install validator confirms required tables including `department_yearly`, `support_recipient`, and `manual_action_log`; v519 unit suite is green | PASS for code/schema, PARTIAL for real operator workflow |
| Excel transfer works | v501 full smoke: `logs/win-v501-stage6-v501-excel-summary-20260520.json` is `ok=true`; v502 Excel smoke did not finish because Windows SSH reset new sessions | PASS via v501, v502 pending |
| Operator actions are auditable in `ManualActionLog` | v502 install validator confirms the table; v503 adds `operator_settings_saved` audit coverage for the settings page with API-key redaction; v504 adds `excel_preview_generated` audit coverage for Excel preview generation; v505 adds `school_year_tasks_rebuilt` audit coverage for task-board rebuilds; v506 adds `operator_url_submitted` and `operator_url_bulk_imported` audit coverage for manual URL registration; v507 adds `prefecture_remark_approved` and `prefecture_remark_rejected` audit coverage for official-list remark decisions; v508 adds `excel_export_generated` audit coverage for master and competition Excel exports; v509 exposes the current audit action and target-table vocabulary in the audit-log filters; v510 adds `school_alias_approved` audit coverage for approved school-alias proposals; v511 adds `proposal_decision_recorded` audit coverage for proposal review decisions; v512 adds `bug_report_generated` audit coverage for local support ZIP generation without storing raw operator notes; current owner real-cycle audit counts and sign-off are missing | PARTIAL, improved in v512 |
| Windows ZIP double-click setup works | v502 setup and validation: `logs/win-v502-stage6-v502-first-setup-env0-20260520.log` and `logs/win-v502-stage6-v502-env0-validate-after-setup-20260520.json` with `ok=true` | PASS |
| Browser UI runs offline on Windows | v501 UI smoke: `logs/win-v501-stage6-v501-ui-smoke-20260520.json` is `ok=true`; v502 UI smoke is pending after Windows SSH instability | PASS via v501, v502 pending |
| Active scheduled-task safety is preserved | `logs/win-v502-stage6-v502-recovery-probe-after-limit50-canary-clean-20260520.json`: `ok=true`, active weekly task still points to the expected v485 lane | PASS |
| Stage 6 evidence bundle and verifier pass | v501 evidence ZIP and verifier: `logs/win-v501-stage6-v501-stage6-evidence-20260519-182045.zip` and `logs/win-v501-stage6-v501-stage6-evidence-verify-20260520-032045.json` with `ok=true`; v502 bundle is pending | PASS via v501, v502 pending |
| v502 RCA is current | `docs/reports/2026-05-20-v502-windows-partial-side-by-side-limit50.md`: 20 RCA items across 45 candidates, buckets `8 no_pdf_candidates`, `8 publication_lag_or_old_target_pdf`, `4 target_form_without_year_evidence`; no residual `non_target_candidates_only` bucket | PASS for RCA, FAIL for yield |
| Weekly selected-school denominator actually gets crawled | v514 focused isolated Mac smoke `target-year-discovery-after-sitecount-fix/20260519_231930-summary.json`: selected NEEC school IDs 1-3 were crawled (`crawled=3`) and remained reviewable, not strict FY2026 successes; v516 selection probe excludes already confirmed target schools 4 and 7 from the target-missing queue while preserving a 50-school queue; v517 targeted school ID 55 smoke confirms the new exact override is crawled and yields FY2019-FY2025 target-form evidence instead of corporation-only non-target evidence; v518 packages that case as discovery gold-set regression evidence; v519 filters vocational-practice basic-info PDFs out of target-form review; v519 Mac continuation canary with copied URL sources crawls 58 site rows for 50 selected schools and moves school ID 55 to `publication_lag_or_old_target_pdf`; v520 adds exact Katayanagi crawl entries while preserving NEEC no-year PDFs as reviewable, not strict successes; v521 suppresses same-school `corporation_pattern` rows when exact school-domain overrides exist, reducing the Katayanagi limit-3 crawl from 6 to 3 and candidate-school mismatches from 69 to 0; the v521 limit-50 canary crawls 54 site rows, finds 50 candidate PDFs, keeps `candidate_school_mismatch=0`, and keeps all 50 selected schools reviewable; v522 reclassifies stale-labeled Sanko school ID 44 evidence into publication-lag, leaving only NEEC school IDs 1 and 2 in the top RCA no-year bucket | PASS for code/evidence contract, current-source Windows smoke pending |
| Owner real Windows cycle and sign-off are complete | No completed owner KPI/sign-off template or owner-return verifier pass is present | BLOCKED |
| PR merge and v1.0 tag are allowed | FY2026 strict proof, v519 Windows smoke, owner real cycle, and exception approval are incomplete | BLOCKED |

## Fresh Local Verification In This Audit Pass

- `uv run python -m eidp.cli eval-discovery-gold --predictions data/discovery-gold-set/expected-predictions.jsonl --json --fail-on-regression` returned 45 exact matches and 0 failures.
- `uv run pytest tests/unit/test_discovery_gold_set_seed.py tests/unit/test_discovery_gold_set_summary.py tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_eval.py tests/unit/test_cli_discovery_gold_set.py tests/unit/test_cli_eval_discovery_gold.py -q` returned `49 passed`.
- v503 settings-audit focused verification is recorded in `docs/reports/2026-05-20-v503-settings-audit-package.md`.
- v504 Excel-preview audit focused verification is recorded in `docs/reports/2026-05-20-v504-excel-preview-audit-package.md`.
- v505 school-year task rebuild audit focused verification is recorded in `docs/reports/2026-05-20-v505-school-task-rebuild-audit-package.md`.
- v506 operator URL registration audit focused verification is recorded in `docs/reports/2026-05-20-v506-operator-url-audit-package.md`.
- v507 prefecture remark decision audit focused verification is recorded in `docs/reports/2026-05-20-v507-prefecture-remark-audit-package.md`.
- v508 Excel export audit focused verification is recorded in `docs/reports/2026-05-20-v508-excel-export-audit-package.md`.
- v509 audit-log filter vocabulary verification is recorded in `docs/reports/2026-05-20-v509-audit-log-filter-package.md`.
- v510 school alias approval audit verification is recorded in `docs/reports/2026-05-20-v510-school-alias-audit-package.md`.
- v511 proposal review decision audit verification is recorded in `docs/reports/2026-05-20-v511-proposal-decision-audit-package.md`.
- v512 bug-report ZIP audit verification is recorded in `docs/reports/2026-05-20-v512-bug-report-audit-package.md`.
- v513 Sanko disclosure slug-probe verification is recorded in `docs/reports/2026-05-20-v513-sanko-disclosure-probe-package.md`.
- v514 weekly selected-site count verification is recorded in `docs/reports/2026-05-20-v514-weekly-selected-site-count-package.md`.
- v514 Mac continuation canary is recorded in `docs/reports/2026-05-20-v514-mac-continuation-canary.md`: strict `2/50 (4.0%)`, operator-reviewable `47/50 (94.0%)`, and `ship_gate_status=below_gate`.
- v515 Sanko child override verification is recorded in `docs/reports/2026-05-20-v515-sanko-child-overrides-package.md`: strict `2/50 (4.0%)`, operator-reviewable `50/50 (100.0%)`, no residual `non_target_candidates_only` RCA bucket, and `ship_gate_status=below_gate`.
- v515 post-docs-only release gate is recorded in `logs/win-v515-stage6-v515-post-docs-only-gates-20260520.json`: `ok=true`, `docs_only_stale=true`, full unit `1891 passed`.
- v516 target-missing queue verification is recorded in `docs/reports/2026-05-20-v516-weekly-target-missing-selection-package.md`: current-FY `review_pending` target PDFs no longer re-enter the target-missing acquisition queue, and v516 full unit `1892 passed`.
- v516 post-docs-only release gate is recorded in `logs/win-v516-stage6-v516-post-docs-only-gates-20260520.json`: `ok=true`, `docs_only_stale=true`, full unit `1892 passed`.
- v517 remaining Sanko child override verification is recorded in `docs/reports/2026-05-20-v517-remaining-sanko-child-overrides-package.md`: school ID 55 now crawls `https://www.sanko.ac.jp/tokyo-child/`, moves from corporation-only non-target evidence to FY2019-FY2025 publication-lag evidence, and v517 full unit `1892 passed`.
- v517 post-docs-only release gate is recorded in `logs/win-v517-stage6-v517-post-docs-only-gates-20260520.json`: `ok=true`, `docs_only_stale=true`, full unit `1892 passed`.
- v518 gold-set publication-lag verification is recorded in `docs/reports/2026-05-20-v518-gold-set-publication-lag-package.md`: the Sanko Tokyo child publication-lag case is packaged as a gold-set entry, expected predictions are 45/45 exact, and v518 full unit `1892 passed`.
- v518 post-docs-only release gate is recorded in `logs/win-v518-stage6-v518-post-docs-only-gates-20260520.json`: `ok=true`, `docs_only_stale=true`, full unit `1892 passed`.
- v519 vocational-practice basic-info verification is recorded in `docs/reports/2026-05-20-v519-vocational-practice-basic-info-filter-package.md`: four FY2026 current-hint RCA sample PDFs now classify as `non_target`, and v519 full unit `1893 passed`.
- v519 post-docs-only release gate is recorded in `logs/win-v519-stage6-v519-post-docs-only-gates-20260520.json`: `ok=true`, `docs_only_stale=true`, full unit `1893 passed`.
- v519 Mac limit-50 continuation canary is recorded in `docs/reports/2026-05-20-v519-mac-limit50-continuation-canary.md`: URL sources loaded, 5 school overrides inferred, `crawled=58`, strict `0/50 (0.0%)`, operator-reviewable `50/50 (100.0%)`, RCA buckets `16 publication_lag_or_old_target_pdf` and `4 target_form_without_year_evidence`, and `ship_gate_status=below_gate`.
- v520 Katayanagi URL boundary verification is recorded in `docs/reports/2026-05-20-v520-katayanagi-url-boundary-package.md`: exact Katayanagi URL overrides load, NEEC no-year `portal/syllabus` PDFs cannot use `school_domain_override_disclosure` trusted-year fill, limit-3 smoke remains strict `0/3 (0.0%)`, operator-reviewable `3/3 (100.0%)`, `ship_gate_status=below_gate`, and v520 full unit `1895 passed`.
- v521 school-override corporation suppression is recorded in `docs/reports/2026-05-20-v521-school-override-corporation-suppression-package.md`: same-school `corporation_pattern` rows are skipped when usable `school_domain_override` rows are in scope, Katayanagi limit-3 `crawled=3`, `candidate_school_mismatch=0`, strict `0/3 (0.0%)`, operator-reviewable `3/3 (100.0%)`, PDF discovery unit `227 passed`, and full unit `1896 passed`.
- v521 Mac limit-50 continuation canary is recorded in `docs/reports/2026-05-20-v521-mac-limit50-continuation-canary.md`: URL sources loaded, 8 school overrides inferred, `crawled=54`, `found=50`, `failed=0`, `candidate_school_mismatch=0`, strict `0/50 (0.0%)`, operator-reviewable `50/50 (100.0%)`, RCA buckets `17 publication_lag_or_old_target_pdf` and `3 target_form_without_year_evidence`, and `ship_gate_status=below_gate`.
- v522 stale-yearless RCA bucket verification is recorded in `docs/reports/2026-05-20-v522-stale-yearless-rca-bucket-source.md`: stale-labeled no-year/image-only Sanko school ID 44 evidence now classifies as `publication_lag_or_old_target_pdf`, genuine NEEC no-year target forms remain in `target_form_without_year_evidence`, the recomputed v521 top 20 RCA split is `18 publication_lag_or_old_target_pdf` and `2 target_form_without_year_evidence`, and full unit `1897 passed`.
- Fresh read-only Windows connectivity recheck on 2026-05-20 found `ssh win` still points at stale `192.168.0.9`; current LAN candidates `192.168.10.12`, `.70`, `.71`, `.72`, and `.73` exposed no usable TCP/22, 135, 139, 445, 3389, 5985, or 5986.

These checks validate the gold-set contract used by the package verifier. They
do not remove the FY2026/R8 release blocker.

## Required Next Actions

1. Restore Windows OpenSSH/exec access or provide the current Windows IPv4.
2. Complete v519 transfer/setup, OCR runtime, UI smoke, Excel smoke, Stage 6 evidence bundle,
   evidence verifier, and final recovery.
3. Resolve the FY2026/R8 strict-yield blocker by either reaching the `>= 60%`
   current-year strict line or approving the documented `publication_lag`
   exception path.
4. Run the owner real Windows cycle and return KPI/sign-off evidence.
5. Run `scripts/verify_stage6_return.py` against the returned owner evidence.
6. Merge PR #2 and create the signed `v1.0` tag only after the above blockers
   are resolved.

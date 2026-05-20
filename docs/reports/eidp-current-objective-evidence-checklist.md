# EIDP Current Objective Evidence Checklist

Updated: 2026-05-20
Branch: `sprint8-handoff-finalize`
PR: `#2`
PR live state: verify with
`gh pr view 2 --json headRefOid,mergeStateStatus,statusCheckRollup,url`.
Last recorded live check before this docs-only audit update:
`614e93a7fcf7fe374ec9d096cb6d26b999f0e964` was `CLEAN` with required checks
`SUCCESS` for both push and pull_request runs.
Status: **NOT COMPLETE**

This file is the prompt-to-artifact checklist for the current long-term EIDP
objective. It intentionally replaces the older historical v464/v460 narrative
with the current v526 state.

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

- Latest package/source candidate: `dist/eidp-windows-v526.zip`
- Latest complete Windows side-by-side smoke package: `dist/eidp-windows-v526.zip`
- v526 package/source commit:
  `5b30eb78edc331f992c1a99fdc7611174791ab87`
- v526 package SHA256:
  `4a03e975243d1327e79470de82fe468814c42a66e2749ec32c3251176da9ebca`
- Latest complete Windows side-by-side smoke: v526
- Latest partial Windows side-by-side setup/canary: v502, superseded by v523/v524/v525/v526
- Latest source/package discovery fix: v523 package rebuild including v522 stale-yearless RCA bucket classification
- Latest source/package verifier hardening: v524/v525/v526 owner-return verifier requires
  Excel proof and ManualActionLog / JSONL outbox proof rows.
- Latest operator UI supplement fix: v526 exposes extracted-PDF
  confirmation/supplement entry points and prefilled manual-entry saves.
- Latest FY2026/R8 Mac-side continuation canary:
  `docs/reports/2026-05-20-v521-mac-limit50-continuation-canary.md`
- Latest RCA reclassification report:
  `docs/reports/2026-05-20-v522-stale-yearless-rca-bucket-source.md`
- Latest same-domain FY2026 negative probe:
  `docs/reports/2026-05-20-v522-same-domain-2026-negative-probe.md`
- Release verdict: blocked by FY2026/R8 strict yield, missing owner real Windows
  cycle, and unapproved `publication_lag` exception.

Passing unit tests, package verification, and a complete Windows smoke are
necessary but not sufficient for completion. They do not by themselves prove
the current FY2026/R8 60-70% target-PDF acquisition line or owner sign-off.

## Prompt-To-Artifact Checklist

| Requirement | Evidence checked | Status |
| --- | --- | --- |
| 47 prefecture official-list seeds are packaged and usable | `logs/win-v526-stage6-v526-non-windows-release-gates-20260520.json`, result `package_verify` stdout: `prefecture_seed_rows=47`, `prefecture_seed_downloadable=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_school_rows_total=2148` | PASS |
| 1,700+ vocational-school scope | v526 Windows setup validator `logs/win-v526-stage6-v526-env0-validate-after-setup-20260520.json`: `.details.school_count=2418`, `.details.school_fiscal_year_status_count=2418`, `.details.sqlite_integrity_check="ok"` | PASS |
| Current rolling FY is FY2026/Reiwa 8 | `logs/win-v526-stage6-v526-last-run-after-weekly-canary-limit50-20260520.json`: `current_fy=2026`, `status=success` | PASS |
| Strict mode excludes old-year fallback from success | `logs/win-v485-stage6/fy2026-strict-yield-upper-bound-fail-20260519.json` and v526 `ship_gate_status=below_gate` preserve old-year exclusion instead of counting stale target forms as success | PASS for contract, FAIL for release yield |
| Current FY2026 strict target-PDF/Excel-ready yield is `>= 60%` | v526 Windows limit-50 canary: strict/Excel-ready `5/50 (10.0%)`; v525 Windows limit-50 canary: strict/Excel-ready `5/50 (10.0%)`; v524 Windows limit-50 canary: strict/Excel-ready `5/50 (10.0%)`; v523 Windows limit-50 canary: strict/Excel-ready `5/50 (10.0%)`; v515 Mac continuation canary from the v513 isolated DB: strict `2/50 (4.0%)`; v516 target-missing canary after confirmed-target exclusion: strict `0/50 (0.0%)`; v519 Mac continuation canary with checked-in URL sources: strict `0/50 (0.0%)`; v521 Mac continuation canary after corporation suppression: strict `0/50 (0.0%)`; v522 only reclassifies RCA buckets and leaves strict `0/50 (0.0%)`; v522 same-domain `2025 -> 2026` and short-year/R7 replacement probe found `404` for all 47 expanded candidates; production-scale upper-bound proof: max possible `39.3%` after 607/1000 schools | FAIL |
| Operator manual workload is `<= 30%` for current FY | v526 Windows limit-50 operator-reviewable `50/50 (100.0%)`; v525 Windows limit-50 operator-reviewable `50/50 (100.0%)`; v524 Windows limit-50 operator-reviewable `50/50 (100.0%)`; v523 Windows limit-50 operator-reviewable `50/50 (100.0%)`; v515 Mac continuation canary operator-reviewable `50/50 (100.0%)`; v516 target-missing canary operator-reviewable `49/50 (98.0%)`; v519 Mac continuation canary operator-reviewable `50/50 (100.0%)`; v521 Mac continuation canary operator-reviewable `50/50 (100.0%)`; strict Excel-ready success is still below gate and owner real-cycle workload proof is missing | FAIL |
| Mature-year exception input exists | `logs/mature-year-acquisition-proof-fy2025-release-exception-v497-20260519.json`: FY2025 denominator `1000`, strict/Excel-ready `60.0%`, operator-reviewable `79.8%`, manual workload `20.2%` | PASS as exception input only |
| Publication-lag exception is approved if release uses the mature-year lane | `docs/reports/2026-05-19-publication-lag-release-exception-record.md`: `Status: NOT_APPROVED`, `Decision: NOT_APPROVED` | BLOCKED |
| PDF extraction stack is packaged | v526 package verifier stdout: `has_runtime=True`, `wheel_count=84`; v526 Windows OCR runtime proof `logs/win-v526-stage6-v526-env0-validate-ocr-runtime-20260520.json` is `ok=true` with Tesseract runtime and `jpn` / `jpn_vert` tessdata present | PASS |
| Confidence `>= 0.70` gate exists | v526 full unit suite in release gate: `1901 passed`; confidence/export/review tests are covered by the unit suite | PASS for code contract, PARTIAL for production OCR corpus |
| `DepartmentYearly` and `SupportRecipient` append-only paths exist | v526 install validator confirms required tables including `department_yearly`, `support_recipient`, and `manual_action_log`; v526 unit suite is green | PASS for code/schema, PARTIAL for real operator workflow |
| Extracted rows can be confirmed/supplemented | `docs/reports/2026-05-20-v526-extracted-confirmation-package.md`: extracted `confirmed_target` rows get `抽出済内容を確認・補足`; the PDF確認・手入力 form preloads current extracted data and saves through existing append-only manual-entry/audit paths | PASS for code/UI contract, PARTIAL for real operator workflow |
| Excel transfer works | v526 full smoke: `logs/win-v526-stage6-v526-excel-summary-20260520.json` is `ok=true`; master workbook, competition workbook, and gap report generated | PASS |
| Operator actions are auditable in `ManualActionLog` | v502 install validator confirms the table; v503 adds `operator_settings_saved` audit coverage for the settings page with API-key redaction; v504 adds `excel_preview_generated` audit coverage for Excel preview generation; v505 adds `school_year_tasks_rebuilt` audit coverage for task-board rebuilds; v506 adds `operator_url_submitted` and `operator_url_bulk_imported` audit coverage for manual URL registration; v507 adds `prefecture_remark_approved` and `prefecture_remark_rejected` audit coverage for official-list remark decisions; v508 adds `excel_export_generated` audit coverage for master and competition Excel exports; v509 exposes the current audit action and target-table vocabulary in the audit-log filters; v510 adds `school_alias_approved` audit coverage for approved school-alias proposals; v511 adds `proposal_decision_recorded` audit coverage for proposal review decisions; v512 adds `bug_report_generated` audit coverage for local support ZIP generation without storing raw operator notes; v524 hardens `scripts/verify_stage6_return.py` so returned owner evidence must include audit page proof, numeric `manual_action_log` count, after-flush JSONL outbox count `0`, audit-flush status, and `JSONL action_id` duplicate status; current owner real-cycle audit counts and sign-off are still missing | PASS for code/verifier contract, BLOCKED for real owner evidence |
| Windows ZIP double-click setup works | v526 setup and validation: `logs/win-v526-stage6-v526-first-setup-env0-20260520.log` and `logs/win-v526-stage6-v526-env0-validate-after-setup-20260520.json` with `ok=true` | PASS |
| Browser UI runs offline on Windows | v526 UI smoke: `logs/win-v526-stage6-v526-ui-smoke-20260520.json` is `ok=true`, port `8526`, health `200/ok`, root `200`, stopped cleanly | PASS |
| Active scheduled-task safety is preserved | `logs/stage6-recovery-20260520-v526.json`: `ok=true`, active weekly task still points to the expected v485 lane; post-reboot preflight `docs/reports/2026-05-20-v526-post-reboot-active-task-preflight.md` confirms active v485 was not accidentally promoted, but also records that active v485 is not healthy release evidence because its latest weekly log failed with a SQLAlchemy import error and no `last_run.json` exists | PASS for no accidental promotion, NOT release evidence |
| Stage 6 evidence bundle and verifier pass | v526 evidence ZIP and verifier: `logs/stage6-evidence-20260520-091540.zip` and `logs/stage6-evidence-verify-local-v526-20260520.json` with `ok=true`; SHA256 `1e7efcb1bdbac6c88d3b38f2b209655fc022518ddaeefa07c2b15fc57c2f2283` | PASS |
| v526/v525/v524/v523 RCA is current | `docs/reports/2026-05-20-v526-extracted-confirmation-package.md`, `docs/reports/2026-05-20-v525-rc-metadata-package.md`, `docs/reports/2026-05-20-v524-full-windows-side-by-side-smoke.md`, and `docs/reports/2026-05-20-v523-full-windows-side-by-side-smoke.md`: v526/v525/v524/v523 repeat the same strict `5/50 (10.0%)`, operator-reviewable `50/50 (100.0%)`, `ship_gate_status=below_gate` blocker; v526 discovery stats record `pre_filtered_non_target_hint=631`, `fiscal_year_mismatch=267`, `classified_non_target=88`, `no_candidates_found=8`, `target_fiscal_year_not_detected=5`, and `http_error_httpstatuserror=1`, with no `candidate_school_mismatch` in the v526 Windows run | PASS for RCA, FAIL for yield |
| Weekly selected-school denominator actually gets crawled | v514 focused isolated Mac smoke `target-year-discovery-after-sitecount-fix/20260519_231930-summary.json`: selected NEEC school IDs 1-3 were crawled (`crawled=3`) and remained reviewable, not strict FY2026 successes; v516 selection probe excludes already confirmed target schools 4 and 7 from the target-missing queue while preserving a 50-school queue; v517 targeted school ID 55 smoke confirms the new exact override is crawled and yields FY2019-FY2025 target-form evidence instead of corporation-only non-target evidence; v518 packages that case as discovery gold-set regression evidence; v519 filters vocational-practice basic-info PDFs out of target-form review; v519 Mac continuation canary with copied URL sources crawls 58 site rows for 50 selected schools and moves school ID 55 to `publication_lag_or_old_target_pdf`; v520 adds exact Katayanagi crawl entries while preserving NEEC no-year PDFs as reviewable, not strict successes; v521 suppresses same-school `corporation_pattern` rows when exact school-domain overrides exist, reducing the Katayanagi limit-3 crawl from 6 to 3 and candidate-school mismatches from 69 to 0; the v526/v525/v524/v523 Windows limit-50 canaries each download 5 strict/current PDFs and keep all 50 selected schools reviewable | PASS for code/evidence contract, FAIL for strict yield |
| Owner real Windows cycle and sign-off are complete | No completed owner KPI/sign-off template or owner-return verifier pass is present; v526 negative verifier probe now blocks missing Excel ready/consistency proof, audit/outbox proof rows, and unapproved `publication_lag` fields | BLOCKED |
| PR merge and v1.0 tag are allowed | FY2026 strict proof, owner real cycle, and exception approval are incomplete | BLOCKED |

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
- v522 same-domain FY2026 negative probe is recorded in `docs/reports/2026-05-20-v522-same-domain-2026-negative-probe.md`: 38 simple `2025 -> 2026` candidates and 47 expanded short-year/R7 variants were generated from v521 FY2025 target-form evidence; HEAD and ranged GET both returned `404` for all 47 expanded candidates.
- Fresh read-only Windows connectivity recheck on 2026-05-20 is recorded in `docs/reports/2026-05-20-v522-windows-connectivity-recheck.md`: the first probe found no usable SSH/SMB/RDP/WinRM service. After the user restarted Windows SSH, `ssh win` worked again and v523 Windows side-by-side validation completed.
- v523 current-head package verification is recorded in `docs/reports/2026-05-20-v523-current-head-package.md`: package `dist/eidp-windows-v523.zip`, SHA256 `5d47ca9e016aa6aadf3608b5799c773a769af585d158813eada1f80cebe762ce`, package/source commit `9a5cefc74751ec849daff86d68ff552f79f376e0`, core + OCR add-on verifier `ok=true`, non-Windows release gate `ok=true`, full unit `1897 passed`, and 45/45 discovery-gold expected predictions.
- v523 full Windows side-by-side smoke is recorded in `docs/reports/2026-05-20-v523-full-windows-side-by-side-smoke.md`: setup/validate/OCR runtime/UI/Excel/weekly limit-50/Stage 6 evidence verifier/residual-cleanup dry run/recovery all returned `ok=true`; the weekly canary crawled 59 site rows, found 50 candidate PDFs, downloaded 5 strict FY2026/R8 PDFs, processed 5 documents into 106 departments and 107 yearly rows, reported strict `5/50 (10.0%)`, operator-reviewable `50/50 (100.0%)`, and kept `ship_gate_status=below_gate`.
- v523 owner/operator request is prepared in `docs/runbooks/eidp-v523-owner-request-20260520.txt`: it points to the v523 package, SHA, side-by-side root, Windows smoke evidence, required return files, KPI/sign-off fields, and the `publication_lag`/strict-FY release-decision boundary.
- The `publication_lag` release-exception record is refreshed to the v526 evidence packet in `docs/reports/2026-05-19-publication-lag-release-exception-record.md`, but remains `NOT_APPROVED`.
- Negative v523 return-verifier probe is recorded in `logs/win-v523-stage6-v523-verify-stage6-return-not-approved-exception-20260520.json` with rc `1`: the refreshed exception packet still fails on `Status must be APPROVED`, `Decision must be APPROVED`, placeholder approval fields, and missing owner/operator sign-off.
- Temporary positive v523 return-verifier probe is recorded in `logs/win-v523-stage6-v523-verify-stage6-return-positive-exception-probe-20260520.json`: with a temporary filled owner E2E template and temporary `APPROVED` exception copy under `_temp/`, the verifier returns `ok=true`, proving the approval/sign-off path is internally consistent but not approved in the real record.
- v523 post-docs-only release gate is recorded in `logs/win-v523-stage6-v523-post-docs-only-gates-20260520.json`: `ok=true`, `docs_only_stale=true`, full unit `1897 passed`.
- v523 campus network probe is recorded in `docs/reports/2026-05-20-v523-campus-network-probe.md`: `ssh win hostname` returned `junming`; the active Windows Wi-Fi profile was `Private`, current Wi-Fi IPv4 was `192.168.0.9/24`, and the OpenSSH inbound firewall rule was enabled. This confirms the current remote-management path but does not remove the FY2026/R8 yield or owner sign-off blockers.
- v523 owner-return verifier coverage audit is recorded in `docs/reports/2026-05-20-v523-owner-return-verifier-coverage-audit.md`: `verify_stage6_return.py` enforces last_run KPI consistency, Stage 6 evidence labels, selected E2E KPI rows, sign-off blocks, approved `publication_lag` records, and mature-year proof, but does not machine-enforce Excel proof or ManualActionLog / JSONL outbox consistency. A green return verifier is therefore necessary but not sufficient for owner-cycle acceptance. The script is packaged in `dist/eidp-windows-v523.zip`, so hardening those checks would require a new source/package lane rather than another v523 docs-only update.
- v523 manual owner-return review companion is prepared in `docs/runbooks/eidp-v523-owner-return-manual-review-checklist.md`: it covers Excel proof, ManualActionLog / JSONL outbox proof, append-only `DepartmentYearly` / `SupportRecipient` evidence, and OCR-scope evidence that remain required but not machine-enforced by the v523 packaged return verifier.
- v523 owner/operator first-read handoff is prepared in `docs/runbooks/00-READ-ME-FIRST-v523.txt`: it lists the selected package, SHA, side-by-side root, current active v485 root to preserve, required evidence, safety red lines, and the release-decision boundary.
- v523 owner/operator docs were staged on Windows under `C:\EIDP-staging\v523-owner-docs-20260520`, recorded in `docs/reports/2026-05-20-v523-owner-docs-windows-staging.md`: the transferred ZIP SHA256 is `11faa8be238c6ae6ff91652af8de7734f1465e135b53358c65365ca42fba6989`, and the extracted docs include the v523 first-read handoff, owner request, manual review checklist, E2E template, package report, Windows smoke report, exception record, objective checklist, and release status. A post-staging read-only recheck confirmed `EIDP Weekly Run` still executes `C:\Users\cyo20\EIDP-v485-70e3db4\scripts\weekly_run.bat`, while both v485 and v523 roots remain present. This copies docs only and does not modify active runtime, DB, PDFs, or Task Scheduler.
- v524 owner-return verifier hardening is recorded in `docs/reports/2026-05-20-v524-owner-return-verifier-hardening-package.md`: the new red test first failed because the old verifier accepted missing Excel/audit proof, the focused verifier suite now returns `14 passed`, the packaging contract slice returns `100 passed`, v524 package/source verification returns `ok=true`, full unit returns `1898 passed`, and the real unapproved owner template is rejected with new missing Excel/audit proof errors.
- v524 full Windows side-by-side smoke is recorded in `docs/reports/2026-05-20-v524-full-windows-side-by-side-smoke.md`: setup/validate/OCR runtime/UI/weekly limit-50/Excel/Stage 6 evidence verifier/residual-cleanup dry run/recovery all returned `ok=true`; the weekly canary remains strict `5/50 (10.0%)`, operator-reviewable `50/50 (100.0%)`, and `ship_gate_status=below_gate`.
- v525 RC metadata package and Windows smoke evidence is recorded in `docs/reports/2026-05-20-v525-rc-metadata-package.md`: package `dist/eidp-windows-v525.zip`, SHA256 `5e0ed056e37c5b105b38de033062c4f7a7a8f0966509adb0251cade8f151efc4`, package/source commit `73392f7a246b4dcd7396524b87e2db48b25dec61`, version `1.0.0rc1`, non-Windows release gate `ok=true`, Windows setup/validate/OCR runtime/UI/weekly limit-50/Excel/Stage 6 evidence verifier/residual-cleanup dry run/recovery all returned `ok=true`, and the weekly canary remains strict `5/50 (10.0%)`, operator-reviewable `50/50 (100.0%)`, `ship_gate_status=below_gate`.
- v525 owner/operator request is prepared in `docs/runbooks/eidp-v525-owner-request-20260520.txt`: it points to the v525 package, SHA, side-by-side root, Windows smoke evidence, required return files, KPI/sign-off fields, and the `publication_lag`/strict-FY release-decision boundary.
- v525 owner/operator docs were staged on Windows under `C:\EIDP-staging\v525-owner-docs-20260520`, recorded in `docs/reports/2026-05-20-v525-owner-docs-windows-staging.md`: the transferred ZIP SHA256 is `5b66839c24dd73a68092f823a584475a44779be1f1ae59947284f81af6dab4bb`, and the extracted docs include the v525 first-read handoff, owner request, E2E template, release admin checklist, package report, exception record, objective checklist, and release status. A post-staging read-only recheck confirmed `EIDP Weekly Run` still executes `C:\Users\cyo20\EIDP-v485-70e3db4\scripts\weekly_run.bat`, while both v485 and v525 roots remain present. This copies docs only and does not modify active runtime, DB, PDFs, or Task Scheduler.
- Negative v525 return-verifier probe is recorded in `logs/win-v525-stage6-v525-verify-stage6-return-not-approved-exception-20260520.json` with rc `1`: the refreshed v525 exception packet still fails on `Status must be APPROVED`, `Decision must be APPROVED`, placeholder approval fields, missing owner/operator KPI and sign-off rows, and missing Excel/audit proof rows.
- v526 extracted confirmation package and Windows smoke evidence is recorded in `docs/reports/2026-05-20-v526-extracted-confirmation-package.md`: package `dist/eidp-windows-v526.zip`, SHA256 `4a03e975243d1327e79470de82fe468814c42a66e2749ec32c3251176da9ebca`, package/source commit `5b30eb78edc331f992c1a99fdc7611174791ab87`, extracted `confirmed_target` rows now expose `抽出済内容を確認・補足`, non-Windows release gate `ok=true`, full unit `1901 passed`, Windows setup/validate/OCR runtime/UI/weekly limit-50/Excel/Stage 6 evidence verifier/residual-cleanup dry run/recovery all returned `ok=true`, and the weekly canary remains strict `5/50 (10.0%)`, operator-reviewable `50/50 (100.0%)`, `ship_gate_status=below_gate`.
- v526 owner/operator request is prepared in `docs/runbooks/eidp-v526-owner-request-20260520.txt`: it points to the v526 package, SHA, side-by-side root, extracted confirmation/supplement UI behavior, Windows smoke evidence, required return files, KPI/sign-off fields, and the `publication_lag`/strict-FY release-decision boundary.
- v526 owner/operator docs were staged on Windows under `C:\EIDP-staging\v526-owner-docs-20260520`, recorded in `docs/reports/2026-05-20-v526-owner-docs-windows-staging.md`: the transferred ZIP SHA256 is `bafab5db3192da5e156974c8585a01b05df7e753c35adc180e253b8c7e5457b3`, and the extracted docs include the v526 first-read handoff, owner request, package report, exception record, objective checklist, release status, and post-reboot active-task preflight. A post-staging read-only recheck confirmed `EIDP Weekly Run` still executes `C:\Users\cyo20\EIDP-v485-70e3db4\scripts\weekly_run.bat`, while both v485 and v526 roots remain present. This copies docs only and does not modify active runtime, DB, PDFs, or Task Scheduler.
- v526 runtime boundary recheck is recorded in `docs/reports/2026-05-20-v526-runtime-boundary-recheck.md`: the active weekly task still points to v485, no Streamlit listeners remained on ports `8523/8524/8525/8526`, and both the v526 side-by-side root and v526 staged docs directory were present.
- Negative v526 return-verifier probe is recorded in `logs/win-v526-stage6-v526-verify-stage6-return-not-approved-exception-20260520.json` with rc `1`: the refreshed v526 exception packet still fails on `Status must be APPROVED`, `Decision must be APPROVED`, placeholder approval fields, missing owner/operator KPI and sign-off rows, and missing Excel/audit proof rows.

These checks validate the gold-set contract used by the package verifier. They
do not remove the FY2026/R8 release blocker.

## Required Next Actions

1. Resolve the FY2026/R8 strict-yield blocker by either reaching the `>= 60%`
   current-year strict line or approving the documented `publication_lag`
   exception path.
2. Run the owner real Windows cycle and return KPI/sign-off evidence.
3. Run `scripts/verify_stage6_return.py` against the returned owner evidence.
4. Merge PR #2 and create the signed `v1.0` tag only after the above blockers
   are resolved.

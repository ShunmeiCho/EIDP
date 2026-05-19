# Final Objective Audit - v501 Windows Side-by-Side State

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
PR: `#2`
Package source commit: `d2fa01d4f060e803f173ecae59bfb0867dbe3afd`
Package: `dist/eidp-windows-v501.zip`
Package SHA256: `a301e4dbc295f5bfd3dc11bc4778db1887f2b8a55dda65f16708e9d8abff3f83`

## Verdict

`NOT COMPLETE`.

v501 is the current package candidate. It has Mac-side package/source
verification and full automated Windows side-by-side smoke evidence: setup,
install validation, OCR runtime, UI health, bounded weekly canary, Excel export,
Stage 6 evidence-bundle verification, and active-task recovery.

This is still not v1.0 approval. The controlling business blocker remains the
FY2026/R8 strict current-year yield: the current proof is below the `60.0%`
ship line unless an explicit `publication_lag` release exception is approved.
Owner real-cycle and sign-off evidence are also still missing.

## Objective Restated As Success Criteria

The objective is complete only when all of the following are true:

1. 47 prefecture official-list seeds are packaged and usable.
2. The school universe covers 1,700+ specialty schools.
3. Current rolling FY, now FY2026/Reiwa 8, target PDFs are found in strict mode
   with old-year fallback excluded from success.
4. `pdfplumber` + PyMuPDF + Tesseract OCR extraction exists, and only rows with
   three-factor confidence `>= 0.70` are allowed into Excel-facing output.
5. `DepartmentYearly` / `SupportRecipient` writes are append-only.
6. Excel transfer is verified.
7. All operator changes are auditable through `ManualActionLog`.
8. The Windows ZIP installs by double click and serves the browser UI offline.
9. The ship line is met: strict target-PDF/Excel-ready `>= 60%` and manual
   workload `<= 30%` for the current rolling FY.
10. The owner real Windows cycle and sign-off evidence are complete.

## Prompt-to-Artifact Checklist

| Requirement | Current evidence | Status |
| --- | --- | --- |
| 47 prefecture official-list seeds | `logs/win-v501-stage6-v501-non-windows-release-gates-20260520.json`: package verifier returned `0`, `prefecture_seed_rows=47`, `prefecture_seed_downloadable=47`, `prefecture_seed_parser_supported=47`; discovery gold checks returned `0` | PASS |
| 1,700+ specialty-school scope | `logs/win-v501-stage6-v501-env0-validate-after-setup-20260520.json`: `school_count=2418`, `school_fiscal_year_status_count=2418`, SQLite integrity `ok` | PASS |
| Current rolling FY is FY2026/Reiwa 8 | `logs/win-v501-stage6-v501-last-run-after-weekly-canary-limit50-20260520.json`: `current_fy=2026`, `status=success` | PASS |
| Strict current-FY success excludes old-year fallback | `logs/win-v485-stage6/fy2026-strict-yield-upper-bound-fail-20260519.json` keeps old-year fallback out of strict FY2026 success; v501 reports `ship_gate_status=below_gate`, not a release pass | PASS for contract, FAIL for yield |
| Current FY2026 strict yield `>= 60%` | v501 limit-50 canary in `logs/win-v501-stage6-v501-last-run-after-weekly-canary-limit50-20260520.json` yielded strict/Excel-ready `10.0%`; the production-scale upper-bound proof in `logs/win-v485-stage6/fy2026-strict-yield-upper-bound-fail-20260519.json` remains below gate with max possible `39.3%` | FAIL |
| Mature FY2025 strict proof for exception path | `logs/mature-year-acquisition-proof-fy2025-release-exception-v497-20260519.json`: `ok=true`, FY2025 denominator `1000`, strict `60.0%`, Excel-ready `60.0%`, manual workload `20.2%` | PASS for exception input only |
| PDF extraction stack packaged | `logs/win-v501-stage6-v501-non-windows-release-gates-20260520.json`: full unit suite `1880 passed`, package verify returned `0`, `has_runtime=true`, `wheel_count=84` | PASS |
| Tesseract OCR runtime/add-on | `logs/win-v501-stage6-v501-validate-ocr-runtime-20260520.json`: `ok=true`, Tesseract `5.4.0.20240606`, `jpn` and `jpn_vert` present | PASS |
| Confidence `>= 0.70` gating | Full unit suite returned `1880 passed`, including confidence, ingest, review, Excel, OCR, and verifier unit tests. This proves code contract, not production OCR corpus yield | PASS for code/runtime, PARTIAL for production OCR corpus |
| Append-only business writes | Full unit suite returned `1880 passed`; validator confirms required tables include `department_yearly`, `support_recipient`, and `manual_action_log`. Owner real-cycle audit counts are not returned yet | PASS for code, PARTIAL for real workflow |
| Excel template transfer | `logs/win-v501-stage6-v501-excel-summary-20260520.json`: master workbook, competition workbook, and gap report exist; command logs generated both workbooks from the v501 Windows root | PASS |
| ManualActionLog audit | Full unit suite returned `1880 passed` and validator confirms `manual_action_log` table exists. Owner real-cycle audit counts/outbox proof are not returned yet | PARTIAL |
| ZIP distribution and offline setup | `logs/win-v501-stage6-v501-preflight-20260520.json`, `logs/win-v501-stage6-v501-first-setup-env0-20260520.log`, and `logs/win-v501-stage6-v501-env0-validate-after-setup-20260520.json` show Windows SHA/BUILD_INFO match, setup completion, and `ok=true` install validation | PASS |
| Browser UI on Windows | `logs/win-v501-stage6-v501-ui-smoke-20260520.json`: `ok=true`, port `8522`, health `200/ok`, root `200`, no traceback, listener stopped cleanly | PASS |
| Active scheduled task safety | `logs/win-v501-stage6-v501-recovery-probe-after-full-smoke-clean-20260520.json`: `ok=true`, active scheduled task still points to `C:\Users\cyo20\EIDP-v485-70e3db4\scripts\weekly_run.bat`, lock probe disabled/not held | PASS |
| Bounded Windows canary correctness | `logs/win-v501-stage6-v501-last-run-after-weekly-canary-limit50-20260520.json`: `status=success`, strict/Excel-ready `10.0%`, operator-reviewable `80.0%`; recovery stayed on v485 | PASS for execution, FAIL for release gate |
| Fresh FY2026 limit-50 RCA | `docs/reports/2026-05-20-v501-windows-partial-side-by-side-limit50.md`: 20 RCA items across 45 candidates, with buckets `8 no_pdf_candidates`, `2 non_target_candidates_only`, `7 publication_lag_or_old_target_pdf`, `3 target_form_without_year_evidence` | PASS for RCA, FAIL for release gate |
| Stage 6 evidence bundle | `logs/win-v501-stage6-v501-stage6-evidence-20260519-182045.zip`; SHA256 `2270956e1511285b6e0ad5c737faa7766ad1fd7a62e5092ae28bec5c6a186336` | PASS |
| Stage 6 evidence verifier | `logs/win-v501-stage6-v501-stage6-evidence-verify-20260520-032045.json`: `ok=true`, required labels present, no unsafe/forbidden entries | PASS |
| Package/source freshness | `logs/win-v501-stage6-v501-non-windows-release-gates-20260520.json`: package/source check fresh at package commit. Later docs-only commits require a `--allow-docs-only-stale-package` gate and should be recorded in the PR body rather than pinned here | PASS |
| Publication-lag exception record | `docs/reports/2026-05-19-publication-lag-release-exception-record.md`: `Status: NOT_APPROVED`, `Decision: NOT_APPROVED` | BLOCKED |
| Unapproved exception cannot pass return verifier | `logs/win-v500-stage6-v500-verify-stage6-return-not-approved-exception-20260520.json`: verifier exit code `1`, `ok=false`, and errors include `release exception record Status must be APPROVED` plus `release exception record Decision must be APPROVED` | PASS for negative gate |
| Owner real Windows cycle | v501 has automated smoke evidence; owner real-cycle KPI table and sign-off are missing | BLOCKED |
| v1.0 tag / main merge | Not allowed while FY2026 strict proof and owner cycle are incomplete, absent explicit release exception approval | BLOCKED |

## Required Next Actions

1. Keep v1.0 blocked until FY2026/R8 strict proof reaches `60%`, or the owner
   explicitly approves the `publication_lag` release exception record.
2. If the exception path is approved, run the owner real Windows cycle on the
   selected lane and return the completed KPI/sign-off template, Stage 6
   evidence ZIP, and verifier JSON.
3. Run `scripts/verify_stage6_return.py` against the returned owner evidence,
   the approved exception record if used, and the mature-year proof JSON.
4. Only after the release blocker is resolved, merge PR #2 and create the
   signed `v1.0` tag.

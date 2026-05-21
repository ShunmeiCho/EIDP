# Final Objective Audit - v502 Partial Windows State

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
PR: `#2`
Package source commit: `dd1524c48240890a8260795b54259342d7648867`
Package: `dist/eidp-windows-v502.zip`
Package SHA256: `6764d4ee67dfd4db42272e87cbebb1b3c63c743d8388004b607b9b8590b41c05`

## Verdict

`NOT COMPLETE`.

v502 is the current package/source candidate. It has Mac-side package/source
verification and partial automated Windows side-by-side evidence: setup,
install validation, active-task recovery, and bounded FY2026/R8 limit-50
canary. v501 remains the latest package with full automated Windows smoke
evidence for OCR runtime, UI health, Excel export, Stage 6 evidence-bundle
verification, and final recovery.

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
| 47 prefecture official-list seeds | `logs/win-v502-stage6-v502-non-windows-release-gates-20260520.json`: package verifier returned `0`, `prefecture_seed_rows=47`, `prefecture_seed_downloadable=47`, `prefecture_seed_parser_supported=47`; discovery gold checks returned `0` | PASS |
| 1,700+ specialty-school scope | `logs/win-v502-stage6-v502-env0-validate-after-setup-20260520.json`: `school_count=2418`, `school_fiscal_year_status_count=2418`, SQLite integrity `ok` | PASS |
| Current rolling FY is FY2026/Reiwa 8 | `logs/win-v502-stage6-v502-last-run-after-weekly-canary-limit50-20260520.json`: `current_fy=2026`, `status=success` | PASS |
| Strict current-FY success excludes old-year fallback | `logs/win-v485-stage6/fy2026-strict-yield-upper-bound-fail-20260519.json` keeps old-year fallback out of strict FY2026 success; v502 reports `ship_gate_status=below_gate`, not a release pass | PASS for contract, FAIL for yield |
| Current FY2026 strict yield `>= 60%` | v502 limit-50 canary in `logs/win-v502-stage6-v502-last-run-after-weekly-canary-limit50-20260520.json` yielded strict/Excel-ready `10.0%`; the production-scale upper-bound proof in `logs/win-v485-stage6/fy2026-strict-yield-upper-bound-fail-20260519.json` remains below gate with max possible `39.3%` | FAIL |
| Mature FY2025 strict proof for exception path | `logs/mature-year-acquisition-proof-fy2025-release-exception-v497-20260519.json`: `ok=true`, FY2025 denominator `1000`, strict `60.0%`, Excel-ready `60.0%`, manual workload `20.2%` | PASS for exception input only |
| PDF extraction stack packaged | `logs/win-v502-stage6-v502-non-windows-release-gates-20260520.json`: full unit suite `1880 passed`, package verify returned `0`, `has_runtime=true`, `wheel_count=84` | PASS |
| Tesseract OCR runtime/add-on | `logs/win-v502-stage6-v502-verify-windows-distribution-with-ocr-addon-20260520.json`: core `ok=true`, OCR add-on `ok=true`; v501 Windows runtime proof remains `logs/win-v501-stage6-v501-validate-ocr-runtime-20260520.json` | PASS for package, v502 Windows runtime pending |
| Confidence `>= 0.70` gating | Full unit suite returned `1880 passed`, including confidence, ingest, review, Excel, OCR, and verifier unit tests. This proves code contract, not production OCR corpus yield | PASS for code/runtime, PARTIAL for production OCR corpus |
| Append-only business writes | Full unit suite returned `1880 passed`; validator confirms required tables include `department_yearly`, `support_recipient`, and `manual_action_log`. Owner real-cycle audit counts are not returned yet | PASS for code, PARTIAL for real workflow |
| Excel template transfer | v501 full smoke `logs/win-v501-stage6-v501-excel-summary-20260520.json` generated master workbook, competition workbook, and gap report; v502 Excel smoke is still pending because Win SSH/exec became unstable | PASS via v501, v502 pending |
| ManualActionLog audit | Full unit suite returned `1880 passed` and validator confirms `manual_action_log` table exists. Owner real-cycle audit counts/outbox proof are not returned yet | PARTIAL |
| ZIP distribution and offline setup | `logs/win-v502-stage6-v502-preflight-20260520.json`, `logs/win-v502-stage6-v502-first-setup-env0-20260520.log`, and `logs/win-v502-stage6-v502-env0-validate-after-setup-20260520.json` show Windows SHA/BUILD_INFO match, setup completion, and `ok=true` install validation | PASS |
| Browser UI on Windows | v501 full smoke `logs/win-v501-stage6-v501-ui-smoke-20260520.json` is `ok=true`; v502 UI smoke is still pending because Win SSH/exec became unstable before completion | PASS via v501, v502 pending |
| Active scheduled task safety | `logs/win-v502-stage6-v502-recovery-probe-after-limit50-canary-clean-20260520.json`: `ok=true`, active scheduled task still points to `C:\Users\cyo20\EIDP-v485-70e3db4\scripts\weekly_run.bat` | PASS |
| Bounded Windows canary correctness | `logs/win-v502-stage6-v502-last-run-after-weekly-canary-limit50-20260520.json`: `status=success`, strict/Excel-ready `10.0%`, operator-reviewable `84.0%`; recovery stayed on v485 | PASS for execution, FAIL for release gate |
| Fresh FY2026 limit-50 RCA | `docs/reports/2026-05-20-v502-windows-partial-side-by-side-limit50.md`: 20 RCA items across 45 candidates, with buckets `8 no_pdf_candidates`, `8 publication_lag_or_old_target_pdf`, `4 target_form_without_year_evidence`; v501 residual `non_target_candidates_only=2` is now `0` | PASS for RCA, FAIL for release gate |
| Stage 6 evidence bundle | v501 full smoke has `logs/win-v501-stage6-v501-stage6-evidence-20260519-182045.zip`; v502 Stage 6 bundle is still pending because Win SSH/exec became unstable | PASS via v501, v502 pending |
| Stage 6 evidence verifier | v501 full smoke has `logs/win-v501-stage6-v501-stage6-evidence-verify-20260520-032045.json` with `ok=true`; v502 verifier is still pending | PASS via v501, v502 pending |
| Package/source freshness | `logs/win-v502-stage6-v502-non-windows-release-gates-20260520.json`: package/source check fresh at package commit. Later docs-only commits are accepted by `logs/win-v502-stage6-v502-runbook-docs-only-stale-gates-20260520.json` with `allowed_stale_reason=docs_only` | PASS |
| Publication-lag exception record | `docs/reports/2026-05-19-publication-lag-release-exception-record.md`: `Status: NOT_APPROVED`, `Decision: NOT_APPROVED` | BLOCKED |
| Unapproved exception cannot pass return verifier | `logs/win-v500-stage6-v500-verify-stage6-return-not-approved-exception-20260520.json`: verifier exit code `1`, `ok=false`, and errors include `release exception record Status must be APPROVED` plus `release exception record Decision must be APPROVED` | PASS for negative gate |
| Owner real Windows cycle | v502 has partial automated smoke evidence; v501 has complete automated smoke evidence; owner real-cycle KPI table and sign-off are missing | BLOCKED |
| v1.0 tag / main merge | Not allowed while FY2026 strict proof and owner cycle are incomplete, absent explicit release exception approval | BLOCKED |

## Required Next Actions

1. Restore Windows OpenSSH/exec stability, then complete v502 UI, Excel/OCR,
   Stage 6 evidence-bundle, and final recovery smoke.
2. Keep v1.0 blocked until FY2026/R8 strict proof reaches `60%`, or the owner
   explicitly approves the `publication_lag` release exception record.
3. If the exception path is approved, run the owner real Windows cycle on the
   selected lane and return the completed KPI/sign-off template, Stage 6
   evidence ZIP, and verifier JSON.
4. Run `scripts/verify_stage6_return.py` against the returned owner evidence,
   the approved exception record if used, and the mature-year proof JSON.
5. Only after the release blocker is resolved, merge PR #2 and create the
   signed `v1.0` tag.

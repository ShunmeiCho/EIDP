# v532 Full Windows Side-By-Side Smoke

Date: 2026-06-20
Package: `dist/eidp-windows-v532.zip`
Package SHA256: `9743cc65c21ada06b6a1d6c8b50ba67cdaffa4f3942256ccd072d4469fa0d6c7`
Package/source commit: `723a5072f63e8a874bef85cc52d869f5e6daff15`
Windows root: `C:\Users\cyo20\EIDP-v532-723a507-env0`

## Scope

This report records the restored-SSH v532 Windows side-by-side validation run.
It supersedes the earlier same-day connectivity-only note for Windows runtime
proof, but it does not approve v1.0 release. The release boundary remains:

- FY2026/Reiwa 8 strict current-year acquisition is below the release gate.
- Owner/operator real-cycle sign-off is still missing.
- The `publication_lag` release exception remains `NOT_APPROVED`.
- v532 OCR runtime proof failed because the OCR add-on was not present in the
  staged package root.

## Evidence Location

The pulled evidence is stored on the external SSD through the repository
`logs` symlink:

```text
logs/win-v532-stage6/win-v532-stage6-side-by-side-evidence-20260620.zip
logs/win-v532-stage6/win-v532-stage6-side-by-side-evidence-manifest-20260620.json
```

The side-by-side evidence ZIP contains 19 files and the manifest reports
`missing_count=0`.

## Windows Side-By-Side Evidence

| Check | Evidence |
| --- | --- |
| Package transfer / setup | `C:\EIDP-staging\eidp-windows-v532.zip` SHA matched `9743cc65c21ada06b6a1d6c8b50ba67cdaffa4f3942256ccd072d4469fa0d6c7`; setup ran with `EIDP_REGISTER_WEEKLY_TASK=0` and returned rc `0`. |
| Setup validator | `win-v532-stage6-v532-env0-validate-after-setup-20260620.json` -> `ok=true`, `school_count=2418`, `school_fiscal_year_status_count=2418`, SQLite integrity `ok`, wheel count `84`, build commit `723a5072f63e8a874bef85cc52d869f5e6daff15`. |
| OCR runtime | `win-v532-stage6-v532-env0-validate-ocr-runtime-20260620.json` -> `ok=false`; missing `ocr-addon/tesseract/tesseract.exe` and `ocr-addon/tessdata/jpn.traineddata`. |
| Active-task safety | `stage6-recovery-20260620-v532.json` -> `ok=true`; active `EIDP Weekly Run` still points to `C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat`; lock probe `ok=true`, held `false`; historical v384 residual paths absent. |
| UI smoke | `win-v532-stage6-v532-ui-smoke-20260620.json` -> `ok=true`, bound to `127.0.0.1:8532`, health `200/ok`, root `200`, process stopped, no listener remained after stop. |
| Weekly limit-50 canary | `win-v532-stage6-v532-weekly-canary-limit50-summary-20260620.json` and `last_run.json` -> weekly rc `0`, `status=success`, `current_fy=2026`, `selection_mode=target_missing`, strict/Excel-ready `12/50 (24.0%)`, operator-reviewable `47/50 (94.0%)`, `ship_gate_status=below_gate`. |
| Discovery / ingest | v532 canary crawled `59` site rows, found `50` candidates, downloaded `14`, failed `1`, and processed `14` documents into `122` new departments and `129` yearly upserts. RCA rejects include `pre_filtered_non_target_hint=459`, `fiscal_year_mismatch=212`, `classified_non_target=103`, `target_fiscal_year_not_detected=7`, `no_candidates_found=9`, and `pdf_school_mismatch=2`. |
| Validate after weekly | `win-v532-stage6-v532-validate-after-weekly-canary-20260620.json` -> `ok=true`, build branch `main`, build commit `723a5072f63e8a874bef85cc52d869f5e6daff15`, `last_run_status=success`, RCA batch plan `20` items / `36` candidates, SQLite integrity `ok`. |
| Excel smoke | `win-v532-stage6-v532-excel-summary-20260620.json` -> `ok=true`; master workbook length `3,746,064`, competition workbook length `121,898`, competition gap CSV length `48,116`; competition export recorded `matched=6`, `unmatched=373`, `cells_written=12`, `target_yearly_rows=129`, `excel_ready_schools=12`. |
| Stage 6 bundle | `stage6-evidence-20260619-163637.zip` created with collector `ok=true`. |
| Stage 6 verifier | `stage6-evidence-verify-20260620-013724.json` -> `ok=true`, entry count `9`, required labels `build_info`, `diagnostics`, and `last_run` present; no errors, warnings, unsafe entries, or forbidden entries. Non-required missing patterns: `bootstrap_logs`, `bootstrap_progress`, and `stage6_residual_cleanup`. |

## Release Boundary

v532 now replaces v526 as the latest package with current Windows side-by-side
smoke evidence for setup, active-task safety, UI, weekly canary, Excel export,
Stage 6 bundle creation, and Stage 6 bundle verification.

It still cannot be promoted to v1.0 because the current FY2026/Reiwa 8 strict
target-document and Excel-ready yield is `12/50 (24.0%)`, below the `>= 60%`
release line. The operator-reviewable rate is `47/50 (94.0%)`, which is useful
for HITL triage but still implies manual workload above the release threshold.

If OCR remains in v1.0 scope, the OCR add-on must be restored and validated for
v532 or a later candidate. If OCR is moved out of v1.0 scope, that must be a
written release-scope decision rather than an implicit omission.

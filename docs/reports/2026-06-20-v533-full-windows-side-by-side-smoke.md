# v533 Full Windows Side-By-Side Smoke

Date: 2026-06-20
Package: `dist/eidp-windows-v533.zip`
Package SHA256: `0d4ca81a9032db1d8b98bf69ba76a4181d99d6bb8cd0091de22df211dc5d5f57`
Package/source commit: `f83f1dc5439156bb9909ea1df5132bed3a7e9b85`
Windows root: `C:\Users\cyo20\EIDP-v533-f83f1dc-env0`

## Scope

This report records the v533 Windows side-by-side validation run. It promotes
v533 from local package/source evidence to the latest Windows side-by-side
smoke candidate, but it does not approve v1.0 release.

The release boundary remains:

- FY2026/Reiwa 8 strict current-year acquisition is below the release gate.
- Owner/operator real-cycle sign-off is still missing.
- The `publication_lag` release exception remains `NOT_APPROVED`.
- v533 OCR runtime proof failed because the OCR add-on is still missing.
- The MEXT T0 target-institution index is packaged and verified, but the
  university target-document discovery/extraction/Excel lane is not complete.

## Evidence Location

The pulled evidence is stored on the external SSD through the repository
`logs` symlink:

```text
logs/win-v533-stage6/stage6-evidence-20260619-180429.zip
logs/win-v533-stage6/stage6-evidence-verify-20260620-030444.json
logs/win-v533-stage6/win-v533-stage6-v533-last-run-after-weekly-canary-limit50-20260620.json
```

The side-by-side evidence ZIP was also re-verified on the Mac:

```text
uv run python scripts/verify_stage6_evidence.py \
  logs/win-v533-stage6/stage6-evidence-20260619-180429.zip \
  --json \
  --require-label last_run
```

Result: `ok=true`, `entry_count=9`, no errors, no warnings, no unsafe entries.

## Windows Side-By-Side Evidence

| Check | Evidence |
| --- | --- |
| Package transfer / setup | `C:\EIDP-staging\eidp-windows-v533.zip` SHA matched `0d4ca81a9032db1d8b98bf69ba76a4181d99d6bb8cd0091de22df211dc5d5f57`; setup ran with `EIDP_REGISTER_WEEKLY_TASK=0` and returned rc `0`. |
| Setup validator | `win-v533-stage6-v533-env0-validate-after-setup-20260620.json` -> `ok=true`, `school_count=2418`, `school_fiscal_year_status_count=2418`, SQLite integrity `ok`, wheel count `168`, build commit `f83f1dc5439156bb9909ea1df5132bed3a7e9b85`. |
| OCR runtime | `win-v533-stage6-v533-env0-validate-ocr-runtime-20260620.json` -> `ok=false`; missing `ocr-addon/tesseract/tesseract.exe` and `ocr-addon/tessdata/jpn.traineddata`. |
| Active-task safety | `stage6-recovery-20260620-v533.json` -> `ok=true`; active `EIDP Weekly Run` still points to `C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat`; lock probe `ok=true`, held `false`; historical v384 residual paths absent. |
| UI smoke | `win-v533-stage6-v533-ui-smoke-20260620.json` -> `ok=true`, bound to `127.0.0.1:8533`, health `200/ok`, root `200`, process stopped, no listener remained after stop. |
| Weekly limit-50 canary | `win-v533-stage6-v533-weekly-canary-limit50-summary-20260620.json` and `last_run.json` -> weekly rc `0`, `status=success`, `current_fy=2026`, `selection_mode=target_missing`, strict/Excel-ready `12/50 (24.0%)`, operator-reviewable `47/50 (94.0%)`, `ship_gate_status=below_gate`. |
| Discovery / ingest | v533 canary crawled `59` site rows, found `50` candidates, downloaded `14`, failed `1`, and processed `14` documents into `122` new departments and `129` yearly upserts. RCA rejects include `pre_filtered_non_target_hint=459`, `fiscal_year_mismatch=212`, `classified_non_target=103`, `target_fiscal_year_not_detected=7`, `no_candidates_found=9`, and `pdf_school_mismatch=2`. |
| Validate after weekly | `win-v533-stage6-v533-validate-after-weekly-canary-20260620.json` -> `ok=true`, build branch `main`, build commit `f83f1dc5439156bb9909ea1df5132bed3a7e9b85`, `last_run_status=success`, RCA batch plan `20` items / `36` candidates, SQLite integrity `ok`. |
| Excel smoke | `win-v533-stage6-v533-excel-summary-20260620.json` -> `ok=true`; master workbook length `3,746,066`, competition workbook length `121,898`, competition gap CSV length `48,116`; competition export recorded `matched=6`, `unmatched=373`, `cells_written=12`, `target_yearly_rows=129`, `excel_ready_schools=12`. |
| Stage 6 bundle | `stage6-evidence-20260619-180429.zip` created with collector `ok=true`. |
| Stage 6 verifier | `stage6-evidence-verify-20260620-030444.json` -> `ok=true`, entry count `9`, required labels `build_info`, `diagnostics`, and `last_run` present; no errors, warnings, unsafe entries, or forbidden entries. Non-required missing patterns: `bootstrap_logs`, `bootstrap_progress`, and `stage6_residual_cleanup`. |

## Release Boundary

v533 now replaces v532 as the latest package with current Windows side-by-side
smoke evidence for setup, active-task safety, UI, weekly canary, Excel export,
Stage 6 bundle creation, and Stage 6 bundle verification.

It still cannot be promoted to v1.0 because the current FY2026/Reiwa 8 strict
target-document and Excel-ready yield is `12/50 (24.0%)`, below the `>= 60%`
release line. The operator-reviewable rate is `47/50 (94.0%)`, which is useful
for HITL triage but still implies manual workload above the release threshold.

If OCR remains in v1.0 scope, the OCR add-on must be restored and validated for
v533 or a later candidate. If OCR is moved out of v1.0 scope, that must be a
written release-scope decision rather than an implicit omission.

The MEXT T0 target-institution index packaged in v533 proves the official
university/specialty-school source-catalog boundary. It does not yet prove a
university PDF discovery, extraction, reconciliation, or Excel output lane.

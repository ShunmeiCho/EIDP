# v523 Full Windows Side-by-Side Smoke Evidence

Date: 2026-05-20
Package candidate: `dist/eidp-windows-v523.zip`
Windows root: `%USERPROFILE%\EIDP-v523-9a5cefc-env0`
Package source commit: `9a5cefc74751ec849daff86d68ff552f79f376e0`

## Verdict

`WINDOWS_SIDE_BY_SIDE_SMOKE_VALIDATED_BELOW_GATE`.

v523 completed side-by-side Windows smoke validation after the SSH service was
restored. The smoke covered setup, install validation, OCR runtime, UI health,
bounded weekly canary, Excel exports, Stage 6 evidence bundle verification,
residual-cleanup dry run, and active-task recovery. It was not promoted to the
active weekly Task Scheduler lane; active production still points to v485.

This is still not v1.0 approval because the FY2026/R8 strict current-year ship
gate remains below `60.0%`.

## Evidence

| Artifact | Result |
| --- | --- |
| `logs/win-v523-stage6/win-v523-stage6-v523-preflight-20260520.json` | ZIP and OCR add-on SHA256 matched on Windows and expanded to fresh v523 env0 root |
| `logs/win-v523-stage6/win-v523-stage6-v523-first-setup-env0-20260520.log` | `first_setup.bat` completed with `EIDP_REGISTER_WEEKLY_TASK=0`; Task Scheduler active lane was not changed |
| `logs/win-v523-stage6/win-v523-stage6-v523-env0-validate-after-setup-20260520.json` | `ok=true`, `school_count=2418`, `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`, package commit `9a5cefc74751ec849daff86d68ff552f79f376e0` |
| `logs/win-v523-stage6/win-v523-stage6-v523-env0-validate-ocr-runtime-20260520.json` | `ok=true`, Tesseract `v5.4.0.20240606`, `jpn` and `jpn_vert` present |
| `logs/win-v523-stage6/win-v523-stage6-v523-ui-smoke-20260520.json` | `ok=true`, port `8523`, health `200/ok`, root `200`, no traceback, listener stopped cleanly |
| `logs/win-v523-stage6/win-v523-stage6-v523-excel-summary-20260520.json` | `ok=true`, master workbook, competition workbook, and gap report were generated |
| `logs/win-v523-stage6/win-v523-stage6-v523-last-run-after-weekly-canary-limit50-20260520.json` | `status=success`, strict/Excel-ready yield `10.0%`, operator-reviewable yield `100.0%`, `ship_gate_status=below_gate` |
| `logs/win-v523-stage6/run-20260520.log` | discovery `crawled=59`, `found=50`, `downloaded=5`, `failed=0`, `candidate_school_mismatch=0`; ingest `processed=5`, `departments_created=106`, `yearly_upserted=107` |
| `logs/win-v523-stage6/win-v523-stage6-v523-weekly-canary-limit50-summary-20260520.json` | wrapper `ok=true`, weekly rc `0`, post-weekly validation rc `0`, recovery rc `0` |
| `logs/win-v523-stage6/stage6-evidence-20260520-043937.zip` | Stage 6 evidence ZIP, SHA256 `f3e5c7df1444c777eed1e710a99a1bede613b315ca130e4102a94e03d1d4c310` |
| `logs/win-v523-stage6/stage6-evidence-verify-20260520-133938.json` | `ok=true`, required labels present, no unsafe/forbidden entries |
| `logs/win-v523-stage6/stage6-recovery-20260520-133934.json` | `ok=true`, `action_matches_expected=true`; active task still points to `C:\Users\cyo20\EIDP-v485-70e3db4\scripts\weekly_run.bat` |
| `logs/win-v523-stage6/stage6-residual-cleanup-20260520-133934.json` | dry-run `ok=true`, `existing_count=0`, `moved_count=0` |

## FY2026/R8 Limit-50 Canary

The v523 Windows canary selected 50 target-missing schools for current
FY2026/R8:

- crawled site rows: `59`
- candidate PDFs found: `50`
- strict/current target PDFs downloaded: `5`
- failed downloads: `0`
- strict/Excel-ready yield: `5/50 (10.0%)`
- operator-reviewable: `50/50 (100.0%)`
- discovery RCA batch: `20` planned items across `45` total candidates
- ship gate: `below_gate`

The discovery rejection distribution in `run-20260520.log` was:

- `pre_filtered_non_target_hint`: `631`
- `fiscal_year_mismatch`: `267`
- `classified_non_target`: `88`
- `no_candidates_found`: `9`
- `target_fiscal_year_not_detected`: `5`
- `http_error_httpstatuserror`: `1`

## Stage 6 Bundle Labels

The verifier reported these present labels:

- `build_info`
- `diagnostics`
- `discovery_evidence`
- `discovery_rca`
- `last_run`
- `stage6_recovery`
- `stage6_residual_cleanup`
- `weekly_run_logs`

The missing manifest patterns were `bootstrap_logs` and `bootstrap_progress`;
these are not required labels for the current verifier contract and the
verifier returned `ok=true`.

## Release Impact

v523 supersedes v501 as the latest complete Windows side-by-side smoke package
and supersedes v502 as the latest Windows side-by-side setup/canary evidence.
The bounded FY2026/R8 canary remains strict/Excel-ready `10.0%`, below the
`60.0%` release line.

v1.0 remains blocked unless current FY2026/R8 strict yield reaches the release
line, or the owner explicitly approves the `publication_lag` exception and then
completes the owner real cycle/sign-off.

# v501 Full Windows Side-by-Side Smoke Evidence

Date: 2026-05-20
Package candidate: `dist/eidp-windows-v501.zip`
Windows root: `%USERPROFILE%\EIDP-v501-d2fa01d-env0`
Package source commit: `d2fa01d4f060e803f173ecae59bfb0867dbe3afd`

## Verdict

`WINDOWS_SIDE_BY_SIDE_SMOKE_VALIDATED_BELOW_GATE`.

v501 now has the same automated Windows side-by-side smoke surface as v500:
setup, install validation, OCR runtime, UI health, bounded weekly canary, Excel
exports, Stage 6 evidence bundle verification, and active-task recovery. It was
not promoted to the active weekly Task Scheduler lane; active production still
points to v485.

This is still not v1.0 approval because the FY2026/R8 strict current-year ship
gate remains below `60.0%`.

## Evidence

| Artifact | Result |
| --- | --- |
| `logs/win-v501-stage6-v501-preflight-20260520.json` | ZIP copied to Windows and expanded to fresh v501 env0 root |
| `logs/win-v501-stage6-v501-first-setup-env0-20260520.log` | `first_setup.bat` completed with `EIDP_REGISTER_WEEKLY_TASK=0`; Task Scheduler active lane was not changed |
| `logs/win-v501-stage6-v501-env0-validate-after-setup-20260520.json` | `ok=true`, `school_count=2418`, `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`, package commit `d2fa01d4f060e803f173ecae59bfb0867dbe3afd` |
| `logs/win-v501-stage6-v501-validate-ocr-runtime-20260520.json` | `ok=true`, Tesseract `5.4.0.20240606`, `jpn` and `jpn_vert` present |
| `logs/win-v501-stage6-v501-ui-smoke-20260520.json` | `ok=true`, port `8522`, health `200/ok`, root `200`, no traceback, listener stopped cleanly |
| `logs/win-v501-stage6-v501-excel-summary-20260520.json` | `ok=true`, master workbook, competition workbook, and gap report were generated |
| `logs/win-v501-stage6-v501-last-run-after-weekly-canary-limit50-20260520.json` | `status=success`, strict/Excel-ready yield `10.0%`, operator-reviewable yield `80.0%`, `ship_gate_status=below_gate` |
| `logs/win-v501-stage6-v501-weekly-canary-limit50-rca-batch-plan-20260520.json` | RCA batch plan with 20 items / 45 total candidates |
| `logs/win-v501-stage6-v501-stage6-evidence-20260519-182045.zip` | Stage 6 evidence ZIP, SHA256 `2270956e1511285b6e0ad5c737faa7766ad1fd7a62e5092ae28bec5c6a186336` |
| `logs/win-v501-stage6-v501-stage6-evidence-verify-20260520-032045.json` | `ok=true`, required labels present, no unsafe/forbidden entries |
| `logs/win-v501-stage6-v501-recovery-probe-after-full-smoke-clean-20260520.json` | `ok=true`, `action_matches_expected=true`; active task still points to `C:\Users\cyo20\EIDP-v485-70e3db4\scripts\weekly_run.bat` |

## Stage 6 Bundle Labels

The verifier reported these present labels:

- `build_info`
- `diagnostics`
- `discovery_evidence`
- `discovery_rca`
- `last_run`
- `stage6_recovery`
- `weekly_run_logs`

The missing manifest patterns were `bootstrap_logs`, `bootstrap_progress`, and
`stage6_residual_cleanup`; these are not required labels for the current
verifier contract and the verifier returned `ok=true`.

## Release Impact

v501 supersedes v500 as the latest Windows side-by-side smoke evidence. The
bounded FY2026/R8 canary improved over v500, but strict/Excel-ready yield is
still `10.0%`, below the `60.0%` release line.

v1.0 remains blocked unless current FY2026/R8 strict yield reaches the release
line, or the owner explicitly approves the `publication_lag` exception and then
completes the owner real cycle/sign-off.

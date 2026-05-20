# v524 Full Windows Side-By-Side Smoke Evidence

Date: 2026-05-20
Package candidate: `dist/eidp-windows-v524.zip`
Windows root: `%USERPROFILE%\EIDP-v524-7751e94-env0`
Package source commit: `7751e948a2f78d9c8126a55d26c78b455a61965b`

## Verdict

`WINDOWS_SIDE_BY_SIDE_SMOKE_VALIDATED_BELOW_GATE`.

v524 completed side-by-side Windows smoke validation after the owner-return
verifier hardening package was built and transferred. The smoke covered setup,
install validation, OCR runtime, UI health, bounded weekly canary, Excel
exports, Stage 6 evidence bundle verification, residual-cleanup dry run, and
active-task recovery. It was not promoted to the active weekly Task Scheduler
lane; active production still points to v485.

This is still not v1.0 approval because the FY2026/R8 strict current-year ship
gate remains below `60.0%`.

## Evidence

| Artifact | Result |
| --- | --- |
| `logs/win-v524-stage6/win-v524-stage6-v524-preflight-20260520.json` | ZIP and OCR add-on SHA256 matched on Windows and expanded to fresh v524 env0 root |
| `logs/win-v524-stage6/win-v524-stage6-v524-first-setup-env0-20260520.log` | `first_setup.bat` completed with `EIDP_REGISTER_WEEKLY_TASK=0`; Task Scheduler active lane was not changed |
| `logs/win-v524-stage6/win-v524-stage6-v524-env0-validate-after-setup-20260520.json` | `ok=true`, `school_count=2418`, `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`, package commit `7751e948a2f78d9c8126a55d26c78b455a61965b` |
| `logs/win-v524-stage6/win-v524-stage6-v524-env0-validate-ocr-runtime-20260520.json` | `ok=true`, Tesseract runtime and `jpn` / `jpn_vert` tessdata present |
| `logs/win-v524-stage6/win-v524-stage6-v524-ui-smoke-20260520.json` | `ok=true`, port `8524`, health `200/ok`, root `200`, no traceback, listener stopped cleanly |
| `logs/win-v524-stage6/win-v524-stage6-v524-last-run-after-weekly-canary-limit50-20260520.json` | `status=success`, strict/Excel-ready yield `10.0%`, operator-reviewable yield `100.0%`, `ship_gate_status=below_gate` |
| `logs/win-v524-stage6/win-v524-stage6-v524-weekly-canary-limit50-summary-20260520.json` | wrapper `ok=true`, weekly rc `0`, post-weekly validation rc `0`, recovery rc `0` |
| `logs/win-v524-stage6/run-20260520.log` | discovery/ingest log for the bounded FY2026/R8 limit-50 canary |
| `logs/win-v524-stage6/win-v524-stage6-v524-excel-summary-20260520.json` | `ok=true`, master workbook, competition workbook, and gap report were generated |
| `logs/win-v524-stage6/stage6-evidence-20260520-072510.zip` | Stage 6 evidence ZIP, SHA256 `638804e7e78b930d2a6f7b6b12fb99af8153f0ee424c3cc677e375d3a823b956` |
| `logs/win-v524-stage6/stage6-evidence-verify-20260520-162525.json` | `ok=true`, required labels present, no unsafe/forbidden entries |
| `logs/win-v524-stage6/stage6-recovery-20260520-162452.json` | `ok=true`, `action_matches_expected=true`; active task still points to `C:\Users\cyo20\EIDP-v485-70e3db4\scripts\weekly_run.bat` |
| `logs/win-v524-stage6/stage6-residual-cleanup-20260520-162501.json` | dry-run `ok=true`, `existing_count=0`, `moved_count=0` |

## FY2026/R8 Limit-50 Canary

The v524 Windows canary selected 50 target-missing schools for current
FY2026/R8:

- strict/Excel-ready yield: `5/50 (10.0%)`
- operator-reviewable: `50/50 (100.0%)`
- current FY: `2026`
- status: `success`
- ship gate: `below_gate`

This matches the v523 release blocker shape. The verifier hardening did not
change discovery yield and did not create current-year strict success.

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

v524 supersedes v523 as the latest complete Windows side-by-side smoke package.
It also contains the hardened owner-return verifier that requires Excel proof
and ManualActionLog / JSONL outbox proof rows.

v1.0 remains blocked unless current FY2026/R8 strict yield reaches the release
line, or the owner explicitly approves the `publication_lag` exception and then
completes the owner real cycle/sign-off.

# EIDP v500 Side-by-Side Validation Record

Updated: 2026-05-20

This record validates v500 on the Windows operator PC without approving v1.0
or promoting the active lane. The active `EIDP Weekly Run` task stayed on v485.

## Package

| Item | Value |
| --- | --- |
| Package | `dist/eidp-windows-v500.zip` |
| SHA256 | `e8d1a736aa725e1a17a4b060daf62f19666ff51ccb0ccb19310d0062de1e42cf` |
| Package/source commit | `e79ac128cf7063b564f1b0c7c3bb89b6854e51e4` |
| Windows root | `%USERPROFILE%\EIDP-v500-e79ac12-env0` |
| Active lane preserved | `%USERPROFILE%\EIDP-v485-70e3db4` |

## Completed Evidence

| Check | Evidence | Result |
| --- | --- | --- |
| Mac package verifier | `logs/win-v500-stage6-v500-verify-windows-distribution-20260520.json` | `ok=true` |
| Core + OCR add-on verifier | `logs/win-v500-stage6-v500-verify-windows-distribution-with-ocr-addon-20260520.json` | `core ok=true`, `ocr-addon ok=true` |
| Non-Windows release gate | `logs/win-v500-stage6-v500-non-windows-release-gates-20260520.json` | `ok=true`, package/source fresh |
| Windows SHA / BUILD_INFO preflight | `logs/win-v500-stage6-v500-preflight-20260520.json` | `ok=true`, active task still v485 |
| Fresh env0 setup without active-task registration | `logs/win-v500-stage6-v500-first-setup-env0-20260520.log` | setup rc `0`, log contains `skipping Task Scheduler registration because EIDP_REGISTER_WEEKLY_TASK=0` |
| Fresh env0 validator | `logs/win-v500-stage6-v500-env0-validate-after-setup-20260520.json` | `ok=true` |
| Fresh env0 active-task recovery | `logs/win-v500-stage6-v500-env0-recovery-expected-v485-clean-20260520.json` | `ok=true`, `action_matches_expected=true`, lock not held |
| OCR runtime validator | `logs/win-v500-stage6-v500-validate-ocr-runtime-20260520.json` | `ok=true`, Tesseract `5.4.0.20240606`, `jpn` and `jpn_vert` present |
| UI smoke | `logs/win-v500-stage6-v500-ui-smoke-20260520.json` | `ok=true`, port `8521`, health `200/ok`, root `200`, stopped cleanly |
| Weekly canary | `logs/win-v500-stage6-v500-last-run-after-weekly-canary-limit10-20260520.json` and `logs/win-v500-stage6-v500-weekly-canary-limit10-run-20260520.log` | `ok=true`, CLI args forwarded, rc `0`, `ship_gate_status=below_gate` |
| Excel smoke | `logs/win-v500-stage6-v500-excel-summary-20260520.json` | `ok=true`, master, competition workbook, and gap report exist |
| Stage 6 evidence bundle | `logs/win-v500-stage6-v500-stage6-evidence-20260519-161653.zip` | SHA256 `674e2fdcaf6f09611c7ffd00ecff3c714a3913b6727478dac3df1917102e2a3e` |
| Stage 6 verifier | `logs/win-v500-stage6-v500-stage6-evidence-verify-20260520-011707.json` | `ok=true`, required labels present |
| Active task after validation | `logs/win-v500-stage6-v500-recovery-probe-lock-after-canary-clean-20260520.json` | `ok=true`, active task still v485, lock not held |

## v499 Finding Resolved

During v499 validation, `scripts\weekly_run.bat --limit 10 --json` did not
bound the run because the batch wrapper ignored CLI arguments. v500 fixes that
by forwarding `%*` and accepting `--json` in the Python runner. The v500 canary
log contains `cli_args --limit 10 --json`, ended with `rc=0`, and selected a
10-school denominator.

## Promotion Boundary

Stop after this side-by-side validation unless the release path is explicitly
approved. v500 is validated as a candidate package, but v1.0 remains blocked by:

- FY2026/R8 strict current-FY yield remains below gate.
- `publication_lag` exception record remains `NOT_APPROVED`.
- Owner real cycle and sign-off are still required.

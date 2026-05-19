# EIDP v498 Side-by-Side Validation Record

Updated: 2026-05-19

This record validates v498 on the Windows operator PC without approving v1.0
or intentionally promoting the active lane. The active `EIDP Weekly Run` task
is restored to v485 after the smoke.

## Package

| Item | Value |
| --- | --- |
| Package | `dist/eidp-windows-v498.zip` |
| SHA256 | `05f7dee2b6a487a798ae3121ea55ceb5593794126ef82e18afe2925ba7262930` |
| Package/source commit | `555fe014feba49e13badd66ef6fcbb434f879d26` |
| Windows root | `%USERPROFILE%\EIDP-v498-555fe01` |
| Active lane preserved | `%USERPROFILE%\EIDP-v485-70e3db4` |

## Completed Evidence

| Check | Evidence | Result |
| --- | --- | --- |
| Mac package verifier | `logs/win-v498-stage6-v498-verify-windows-distribution-20260519.json` | `ok=true` |
| Core + OCR add-on verifier | `logs/win-v498-stage6-v498-verify-windows-distribution-with-ocr-addon-20260519.json` | `core ok=true`, `ocr-addon ok=true` |
| Non-Windows release gate | `logs/win-v498-stage6-v498-non-windows-release-gates-20260519.json` | `ok=true`, package/source fresh |
| Windows setup validator | `logs/win-v498-stage6-v498-validate-after-setup-20260519.json` | `ok=true` |
| OCR runtime validator | `logs/win-v498-stage6-v498-validate-ocr-runtime-20260519.json` | `ok=true`, Tesseract `5.4.0.20240606`, `jpn` and `jpn_vert` present |
| UI smoke | `logs/win-v498-stage6-v498-ui-smoke-20260519.json` | `ok=true`, port `8519`, health `200/ok`, root `200` |
| Weekly canary | `logs/win-v498-stage6-v498-weekly-canary-limit10-20260519.json` | `ok=true`, `run_id=20260519_123058`, `ship_gate_status=below_gate` |
| Excel smoke | `logs/win-v498-stage6-v498-excel-summary-20260519.json` | `ok=true`; master and competition workbooks exist |
| Stage 6 evidence bundle | `logs/win-v498-stage6-v498-stage6-evidence-20260519-123728.zip` | SHA256 `9d51bfce550dd1d4dc12843b19ecb0a99e5b06cdcbca655cf4aa1088b02d8199` |
| Stage 6 verifier | `logs/win-v498-stage6-v498-stage6-evidence-verify-20260519-213747.json` | `ok=true` |
| Active task after restore | `logs/win-v498-stage6-v498-recovery-expected-v485-after-restore-20260519.json` | `ok=true`, `action_matches_expected=true` |

## SSH Validation Notes

For non-interactive SSH validation, do not run the root `EIDP-setup.bat`
wrapper through stdin-fed PowerShell. It ends with `pause`, which can consume
the remaining script input. Use `scripts\first_setup.bat` directly, or use an
encoded PowerShell command and ensure the scheduled task is checked afterward.

If a side-by-side setup accidentally points `EIDP Weekly Run` to the candidate
root, restore it to:

```text
C:\Users\cyo20\EIDP-v485-70e3db4\scripts\weekly_run.bat
```

and rerun `scripts\stage6_recovery_check.bat` before any owner operation.

## Promotion Boundary

Stop after this side-by-side validation unless the release path is explicitly
approved. v498 is validated as a candidate package, but v1.0 remains blocked by:

- FY2026/R8 strict current-FY yield below 60%;
- `publication_lag` exception record still `NOT_APPROVED`;
- missing owner real-cycle KPI table and sign-off.

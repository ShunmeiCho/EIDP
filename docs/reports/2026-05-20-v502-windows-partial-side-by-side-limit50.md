# v502 Windows Partial Side-by-Side And Limit-50 Evidence

Date: 2026-05-20
Package candidate: `dist/eidp-windows-v502.zip`
Windows root: `%USERPROFILE%\EIDP-v502-dd1524c-env0`
Run ID: `20260519_183903`

## Verdict

`PARTIAL_WINDOWS_VALIDATED_BELOW_GATE`.

This report records the SSH-driven Windows setup, validation, recovery, and
FY2026/R8 limit-50 canary path for v502. It does not replace the complete v501
Windows smoke report yet, because v502 UI smoke and Stage 6 evidence-bundle
verification were blocked by Windows OpenSSH session resets before completion.

## Evidence

| Artifact | Result |
| --- | --- |
| `logs/win-v502-stage6-v502-preflight-20260520.json` | ZIP copied to Windows, SHA256 matched the sidecar, expanded to fresh v502 env0 root |
| `logs/win-v502-stage6-v502-first-setup-env0-20260520.log` | `first_setup.bat` completed with `EIDP_REGISTER_WEEKLY_TASK=0`; Task Scheduler active lane was not changed |
| `logs/win-v502-stage6-v502-env0-validate-after-setup-20260520.json` | `ok=true`, `school_count=2418`, `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`, `build_commit=dd1524c48240890a8260795b54259342d7648867` |
| `logs/win-v502-stage6-v502-env0-recovery-expected-v485-clean-20260520.json` | `ok=true`, `action_matches_expected=true`; active task still points to `C:\Users\cyo20\EIDP-v485-70e3db4\scripts\weekly_run.bat` |
| `logs/win-v502-stage6-v502-last-run-after-weekly-canary-limit50-20260520.json` | `status=success`, strict/Excel-ready yield `10.0%`, operator-reviewable yield `84.0%`, `ship_gate_status=below_gate` |
| `logs/win-v502-stage6-v502-recovery-probe-after-limit50-canary-clean-20260520.json` | `ok=true`; active task still points to v485 |
| `logs/win-v502-stage6-v502-weekly-canary-limit50-rca-batch-plan-20260520.json` | RCA batch plan with 20 items / 45 total candidates |

## v502 RCA Summary

RCA batch buckets:

| Bucket | Count |
| --- | ---: |
| `no_pdf_candidates` | 8 |
| `publication_lag_or_old_target_pdf` | 8 |
| `target_form_without_year_evidence` | 4 |

The prior v501 `non_target_candidates_only` bucket is absent in v502. The
remaining buckets are either no-PDF cases, publication-lag/old-year target
forms, or target-form candidates without safe current-year evidence. They
cannot be counted as strict FY2026/R8 successes under the current release
contract.

## Release Impact

v502 supersedes v501 as the latest package/source candidate and as the latest
partial Windows side-by-side canary. v501 remains the latest complete Windows
smoke package until v502 UI, Excel/OCR pullback, Stage 6 evidence-bundle
verification, and final recovery evidence are completed and recorded.

v1.0 remains blocked unless current FY2026/R8 strict yield reaches the release
line or the owner explicitly approves the `publication_lag` exception and then
completes the owner real cycle/sign-off.

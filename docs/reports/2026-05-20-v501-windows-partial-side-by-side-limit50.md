# v501 Windows Partial Side-by-Side And Limit-50 Evidence

Date: 2026-05-20
Package candidate: `dist/eidp-windows-v501.zip`
Windows root: `%USERPROFILE%\EIDP-v501-d2fa01d-env0`
Run ID: `20260519_175624`

## Verdict

`PARTIAL_WINDOWS_VALIDATED_BELOW_GATE`; later superseded for Windows-smoke
completeness by `docs/reports/2026-05-20-v501-full-windows-side-by-side-smoke.md`.

This report records the initial SSH-driven Windows setup, validation, recovery,
and FY2026/R8 limit-50 canary path. The follow-up full smoke report adds OCR
runtime, UI, Excel, and Stage 6 evidence-bundle verification for the same v501
root.

The Sanko URL override follow-up materially improved the bounded canary result
from v500, but v501 remains below the strict current-year ship gate.

## Evidence

| Artifact | Result |
| --- | --- |
| `logs/win-v501-stage6-v501-preflight-20260520.json` | ZIP copied to Windows, extracted to fresh v501 env0 root |
| `logs/win-v501-stage6-v501-first-setup-env0-20260520.log` | `first_setup.bat` completed with `EIDP_REGISTER_WEEKLY_TASK=0`; Task Scheduler active lane was not changed |
| `logs/win-v501-stage6-v501-env0-validate-after-setup-20260520.json` | `ok=true`, `school_count=2418`, `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`, `build_commit=d2fa01d4f060e803f173ecae59bfb0867dbe3afd` |
| `logs/win-v501-stage6-v501-env0-recovery-expected-v485-clean-20260520.json` | `ok=true`, `action_matches_expected=true`; active task still points to `C:\Users\cyo20\EIDP-v485-70e3db4\scripts\weekly_run.bat` |
| `logs/win-v501-stage6-v501-last-run-after-weekly-canary-limit50-20260520.json` | `status=success`, strict/Excel-ready yield `10.0%`, operator-reviewable yield `80.0%`, `ship_gate_status=below_gate` |
| `logs/win-v501-stage6-v501-recovery-probe-lock-after-limit50-canary-20260520.json` | `ok=true`, lock not held, active task still points to v485 |
| `logs/win-v501-stage6-v501-weekly-canary-limit50-rca-batch-plan-20260520.json` | RCA batch plan with 20 items / 45 total candidates |

## v500 To v501 Limit-50 Delta

| Metric | v500 | v501 |
| --- | ---: | ---: |
| Strict / Excel-ready FY2026 yield | `4.0%` | `10.0%` |
| Operator-reviewable yield | `56.0%` | `80.0%` |
| RCA `non_target_candidates_only` bucket | `17` | `2` |
| RCA `target_form_without_year_evidence` bucket | `3` | `3` |

The delta confirms that the Sanko exact school URL overrides reduced the
corporation-root false discovery cluster. It does not prove v1.0 readiness,
because strict FY2026/R8 yield is still far below `60.0%`.

## v501 RCA Summary

RCA batch buckets:

| Bucket | Count |
| --- | ---: |
| `no_pdf_candidates` | 8 |
| `non_target_candidates_only` | 2 |
| `publication_lag_or_old_target_pdf` | 7 |
| `target_form_without_year_evidence` | 3 |

RCA evidence-row PDF types:

| PDF type | Count |
| --- | ---: |
| empty / no PDF | 8 |
| `non_target` | 66 |
| `target` | 54 |

Top RCA evidence-row reasons:

| Reason | Count |
| --- | ---: |
| `pre_filtered_non_target_hint` | 50 |
| `candidate_school_mismatch` | 15 |
| `fiscal_year_mismatch:2022` | 8 |
| `no_candidates_found` | 8 |
| `fiscal_year_mismatch:2019` | 7 |
| `fiscal_year_mismatch:2020` | 7 |
| `fiscal_year_mismatch:2021` | 7 |
| `fiscal_year_mismatch:2024` | 7 |
| `fiscal_year_mismatch:2023` | 6 |
| `fiscal_year_mismatch:2025` | 6 |

The remaining three `target_form_without_year_evidence` rows are the NEEC
schools discovered through `https://www.neec.ac.jp/`; they still cannot be
accepted as strict FY2026/R8 successes without safe year evidence. The
`publication_lag_or_old_target_pdf` bucket now accounts for a larger share of
the sample, which is consistent with the current publication-lag blocker.

## Release Impact

This partial report is superseded for Windows-smoke completeness by
`docs/reports/2026-05-20-v501-full-windows-side-by-side-smoke.md`, which adds
OCR runtime, UI, Excel, and Stage 6 evidence-bundle verification for the same
v501 root.

v1.0 remains blocked unless current FY2026/R8 strict yield reaches the release
line or the owner explicitly approves the `publication_lag` exception and then
completes the owner real cycle/sign-off.

# EIDP v446 Stage 6 Evidence Draft

Updated: 2026-05-16
Status: diagnostic pass / production yield fail

This document records the v446 Windows canary lane. v446 adds the packaged
release-artifact pruning helper and then proves the current ZIP through Windows
transfer, setup, URL-only bootstrap, bounded weekly launcher canary, and evidence
bundle verification. It is not a completed operator real-cycle Stage 6 sign-off.

## Package

| Item | Value |
| --- | --- |
| Package | `dist/eidp-windows-v446.zip` |
| Build commit | `e9f91ccbb51f82cb594be6567076df50276cc97a` |
| SHA256 | `e0436a08d12d09987f15f96c814de2290010714477e54ae0dcff0f290a3d3878` |
| Windows extract path | `C:\Users\cyo20\EIDP-v446-e9f91cc` |
| Windows staging ZIP | `C:\EIDP-staging\eidp-windows-v446.zip` |
| Canary evidence | `logs/win-v446-stage6/20260515_225803-summary.json` |
| RCA evidence | `logs/win-v446-stage6/20260515_225803-discovery-rca-batch-plan.json` |
| Rejection evidence | `logs/win-v446-stage6/20260515_225803-discovery-rejections.jsonl` |
| Evidence bundle | `logs/win-v446-stage6/stage6-evidence-20260515-225956.zip` |

## Evidence

| Check | Result | Evidence |
| --- | --- | --- |
| Mac package gate | pass | `logs/release-gate-v446.json` reports SHA sidecar match, package/source commit `e9f91ccbb51f82cb594be6567076df50276cc97a`, `source_dirty=false`, validator/distribution tests `164 passed`, and both package verifier modes pass. |
| Docs-only stale gate | pass with explicit stale allowance | `logs/release-gate-v446-docs-stale-allowed.json` reports `ok=true`, SHA sidecar match, and `stale=true` only because the source HEAD is the follow-up docs commit. |
| Windows transfer | pass | Win-side `Get-FileHash` matched SHA256 `e0436a08d12d09987f15f96c814de2290010714477e54ae0dcff0f290a3d3878`. |
| Packaged pruning helper | pass | `scripts\prune_release_artifacts.py` existed inside `C:\Users\cyo20\EIDP-v446-e9f91cc`; dry-run identified only v445 staging/deploy candidates, and `--apply` deleted those three candidates. |
| Windows retention | pass | `C:\EIDP-staging` now keeps only v442 and v446 ZIP/sidecar pairs; `C:\Users\cyo20` keeps only `EIDP-v442-22f1a98` and `EIDP-v446-e9f91cc`. |
| Windows setup | pass | `EIDP-setup.bat` completed; `validate_install.bat --after-setup --json` returned `ok=true`, `school_count=2418`, `school_fiscal_year_status_count=2418`, and `sqlite_integrity_check=ok`. |
| URL-only bootstrap | pass | `scripts\bootstrap_pdfs.bat --skip-discover --url-search off --school-url-crawl off` completed after downloading and aggregating the 47 prefecture seed artifacts. |
| Bounded weekly canary | diagnostic pass / yield fail | `scripts\weekly_run.bat` exited `0` under `EIDP_WEEKLY_LIMIT=5`, `EIDP_WEEKLY_BATCH_SIZE=5`, `EIDP_WEEKLY_RATE_LIMIT=0.5`, and `EIDP_WEEKLY_REQUEST_TIMEOUT=8`. The summary reported `crawled=5`, `found=3`, `downloaded=0`, `operator_reviewable_count=1`, and `ship_gate_status=below_gate`. |
| After-weekly validator | pass | `validate_install.bat --after-setup --after-weekly --json` returned `ok=true`, `last_run_status=success`, `sqlite_target_fy_target_pdf_school_count=0`, and `sqlite_target_fy_operator_reviewable_school_count=1`. |
| Recovery check | pass / action path skipped | `scripts\stage6_recovery_check.bat` returned `ok=true` in wrapper-default mode, with scheduled-task action check skipped. |
| Residual cleanup dry-run | pass | `scripts\stage6_residual_cleanup.bat --json` returned `ok=true`, `existing_count=0`, and `moved_count=0`. |
| Evidence bundle | pass | `logs\stage6-evidence-20260515-225956.zip` verified `ok=true` on Windows and Mac, with no forbidden/unsafe entries, no missing manifest patterns, and all expected evidence labels present. |

## Canary Result

v446 proves the current package can be transferred, set up, bootstrapped, bounded
through the real weekly launcher, and mechanically bundled for Stage 6 evidence.
The bounded canary still does not meet the production yield gate:

| Metric | Value |
| --- | --- |
| `current_fy` | `2026` |
| `target_pdf_auto_acquired_count` | `0` |
| `target_pdf_auto_yield_pct` | `0.0` |
| `operator_reviewable_count` | `1` |
| `operator_reviewable_yield_pct` | `20.0` |
| `ship_gate_status` | `below_gate` |

## Remaining Blocker

Do not sign this draft as Stage 6 complete. The remaining blocker is still the
operator-PC real-cycle sign-off with a populated KPI row and, later, the FY2026
production wet-run once current target-form PDFs are actually published.

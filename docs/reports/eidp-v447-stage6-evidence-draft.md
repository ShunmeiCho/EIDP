# EIDP v447 Stage 6 Evidence Draft

Updated: 2026-05-16
Status: diagnostic pass / production yield fail

This document records the v447 Windows diagnostic lane. v447 adds fsync before
atomic replacement for Windows-runner text outputs, restores the reusable
operator E2E template to version-neutral form, and proves the package through
Mac release gates plus Windows transfer, setup, URL-only bootstrap, bounded
weekly launcher canary, and evidence-bundle verification.

It is not a completed operator real-cycle Stage 6 sign-off.

## Package

| Item | Value |
| --- | --- |
| Package | `dist/eidp-windows-v447.zip` |
| Build commit | `55cbc1b4007a8a0e2798cc8d79f5adbff1944391` |
| SHA256 | `cada1a77a2d52793939518c62a2433aee3fe959a21ad611a3fd37264c7a38557` |
| Windows extract path | `C:\Users\cyo20\EIDP-v447-55cbc1b` |
| Windows staging ZIP | `C:\EIDP-staging\eidp-windows-v447.zip` |
| Canary evidence | `logs/win-v447-stage6/20260515_234136-summary.json` |
| RCA evidence | `logs/win-v447-stage6/20260515_234136-discovery-rca-batch-plan.json` |
| Evidence bundle | `logs/win-v447-stage6/stage6-evidence-20260515-234300.zip` |
| UI health evidence | `logs/win-v447-stage6/v447-ui-smoke-20260516-084930.json` |

## Evidence

| Check | Result | Evidence |
| --- | --- | --- |
| Atomic write hardening | pass | `scripts/atomic_write.py` now flushes and `os.fsync()`s the temp file before `replace`; `uv run pytest tests/unit/test_atomic_write.py -q` returned `4 passed`. |
| Distribution verifier regression | pass | `uv run pytest tests/unit/test_atomic_write.py tests/unit/test_windows_distribution_verifier.py -q` returned `114 passed`; Ruff passed for `scripts/atomic_write.py` and `tests/unit/test_atomic_write.py`; mypy passed for `scripts/atomic_write.py`. |
| Mac package gate | pass | `logs/release-gate-v447.json` reports SHA sidecar match, package/source commit `55cbc1b4007a8a0e2798cc8d79f5adbff1944391`, `source_dirty=false`, `stale=false`, validator/distribution tests `164 passed`, and both package verifier modes pass. |
| Windows transfer | pass | Win-side `Get-FileHash` matched SHA256 `cada1a77a2d52793939518c62a2433aee3fe959a21ad611a3fd37264c7a38557`. |
| Windows setup | pass | `EIDP-setup.bat` completed; `validate_install.bat --after-setup --json` returned `ok=true`, `school_count=2418`, `school_fiscal_year_status_count=2418`, and `sqlite_integrity_check=ok`. |
| Windows retention | pass | v447 packaged pruner dry-run found only v446 staging/deploy candidates; `--apply` deleted v446 ZIP, v446 sidecar, and `EIDP-v446-e9f91cc`, freeing `1104507037` bytes while keeping v447 current plus v442 fallback. |
| URL-only bootstrap | pass | `scripts\bootstrap_pdfs.bat --skip-discover --url-search off --school-url-crawl off` completed after downloading and aggregating the 47 prefecture seed artifacts. |
| Bounded weekly canary | diagnostic pass / yield fail | `scripts\weekly_run.bat` exited `0` under `EIDP_WEEKLY_LIMIT=5`, `EIDP_WEEKLY_BATCH_SIZE=5`, `EIDP_WEEKLY_RATE_LIMIT=0.5`, and `EIDP_WEEKLY_REQUEST_TIMEOUT=8`. The summary reported `crawled=5`, `found=3`, `downloaded=0`, `operator_reviewable_count=1`, and `ship_gate_status=below_gate`. |
| Atomic write Windows path | pass | The v447 bounded weekly wrote `data\output\last_run.json`, `20260515_234136-summary.json`, and `20260515_234136-discovery-rca-batch-plan.json` through the packaged launcher, exercising `write_text_atomic` after the fsync fix. |
| After-weekly validator | pass | `validate_install.bat --after-setup --after-weekly --json` returned `ok=true`, `last_run_status=success`, `sqlite_target_fy_target_pdf_school_count=0`, and `sqlite_target_fy_operator_reviewable_school_count=1`. |
| Recovery check | pass / action path skipped | `scripts\stage6_recovery_check.bat` returned `ok=true` in wrapper-default mode, with scheduled-task action check skipped. |
| Residual cleanup dry-run | pass | `scripts\stage6_residual_cleanup.bat --json` returned `ok=true`, `existing_count=0`, and `moved_count=0`. |
| Evidence bundle | pass | `logs\stage6-evidence-20260515-234300.zip` verified `ok=true` on Windows and Mac, with no forbidden/unsafe entries, no missing manifest patterns, and all expected evidence labels present. |
| UI health smoke | pass | v447 launched through `scripts\launch.bat`; `/_stcore/health` and `/` both returned HTTP `200`, and cleanup left no listener on `8501`. |

## Canary Result

v447 proves the fsync-hardened package can be transferred, set up,
bootstrapped, bounded through the real weekly launcher, and mechanically bundled
for Stage 6 evidence. The bounded canary still does not meet the production
yield gate:

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

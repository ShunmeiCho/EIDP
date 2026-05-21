# EIDP v448 Stage 6 Evidence Draft

Updated: 2026-05-16

This draft records the v448 Windows setup, disk-health, artifact-retention,
bounded weekly, evidence-bundle, and UI-health evidence. It is not a completed
operator real-cycle Stage 6 sign-off.

## Package

| Item | Value |
| --- | --- |
| ZIP | `dist/eidp-windows-v448.zip` |
| SHA256 | `5306b983debe3aee743869d64ded5557eacb4ab70042e5e6862cdbf3a5a9a09e` |
| Package snapshot | `639dbbbac5b1b957bb30e419d84f909b683aedec` |
| Windows deploy path | `C:\Users\cyo20\EIDP-v448-639dbbb` |
| Non-Windows gate | `logs/release-gate-v448.json` |
| Canary evidence | `logs/win-v448-stage6/20260516_001421-summary.json` |
| RCA evidence | `logs/win-v448-stage6/20260516_001421-discovery-rca-batch-plan.json` |
| Evidence bundle | `logs/win-v448-stage6/stage6-evidence-20260516-001548.zip` |
| UI health evidence | `logs/win-v448-stage6/v448-ui-smoke-20260516-091650.json` |

## Evidence

| Check | Result | Notes |
| --- | --- | --- |
| Non-Windows release gate | pass | `logs/release-gate-v448.json` returned `ok=true`, package/source commit match, SHA sidecar match, validator/distribution tests `164 passed`, mypy/Ruff pass, discovery-gold predictions `44/44`, and both package verifier modes passed. |
| Windows transfer + SHA | pass | `dist/eidp-windows-v448.zip` and sidecar were copied to `C:\EIDP-staging`; `Get-FileHash` matched `5306b983debe3aee743869d64ded5557eacb4ab70042e5e6862cdbf3a5a9a09e`. |
| Windows extract | pass | Expanded to `C:\Users\cyo20\EIDP-v448-639dbbb`; `BUILD_INFO.json` reports commit `639dbbbac5b1b957bb30e419d84f909b683aedec`, `git_dirty=false`, and `scripts\disk_health_check.py` exists. |
| Setup | pass | `EIDP-setup.bat` completed; `scripts\validate_install.bat --after-setup --json` returned `ok=true`, `school_count=2418`, `school_fiscal_year_status_count=2418`, and `sqlite_integrity_check=ok`. |
| Initial operator disk health | pass | `scripts\disk_health_check.py --profile operator-win --json` returned `ok=true` after setup with `app_root_total=843.0MiB`, `data\pdfs=0B`, `data\output=0B`, `logs=3.8KiB`, and no warn/block entries. |
| Windows retention prune | pass | v448 packaged pruner dry-run found only v447 staging/deploy candidates; `--apply` deleted v447 ZIP, sidecar, and `EIDP-v447-55cbc1b`, freeing `1104022134` bytes while keeping v448 current plus v442 fallback. |
| URL-only bootstrap | pass | `scripts\bootstrap_pdfs.bat --skip-discover --url-search off --school-url-crawl off` completed after downloading and aggregating the 47 prefecture seed artifacts. |
| Bounded weekly launcher | pass / below gate | Real `scripts\weekly_run.bat` exited `0` with `run_id=20260516_001421`, `crawled=5`, `found=3`, `downloaded=0`, `operator_reviewable_count=1`, `target_pdf_auto_acquired_count=0`, `target_pdf_auto_yield_pct=0.0`, and `ship_gate_status=below_gate`. |
| After-weekly validator | pass | `scripts\validate_install.bat --after-setup --after-weekly --json` returned `ok=true`, `last_run_status=success`, `sqlite_target_fy_target_pdf_school_count=0`, and `sqlite_target_fy_operator_reviewable_school_count=1`. |
| Recovery check | pass / action path skipped | `scripts\stage6_recovery_check.bat` returned `ok=true`, with scheduled-task action check skipped and the task execute path pointing at `C:\Users\cyo20\EIDP-v448-639dbbb\scripts\weekly_run.bat`. |
| Residual cleanup dry-run | pass | `scripts\stage6_residual_cleanup.bat --json` returned `ok=true`, `existing_count=0`, and `moved_count=0`. |
| Evidence bundle | pass | `logs\stage6-evidence-20260516-001548.zip` verified `ok=true` on Windows and Mac, with no forbidden/unsafe entries, no missing manifest patterns, and all expected evidence labels present. |
| UI health smoke | pass | v448 launched through `scripts\launch.bat`; `/_stcore/health` and `/` both returned HTTP `200`, and cleanup left no listener on `8501`. |
| Final operator disk health | pass | After bootstrap, weekly, evidence collection, and UI smoke, `scripts\disk_health_check.py --profile operator-win --json` returned `ok=true` with `app_root_total=851.4MiB`, `data\pdfs=0B`, `data\output=61.7KiB`, `logs=123.0KiB`, and no warn/block entries. |
| Mac disk health | pass | Mac pruning deleted v446/v447 ZIPs and sidecars, freeing `422489392` bytes. `scripts\disk_health_check.py --profile mac-dev --json` returned `ok=true`, `project_total=1.7GiB`, `dist=738.7MiB`, `_temp=0B`, `logs=3.4MiB`, and protected `data=20.0MiB`. |

## Canary Result

```json
{
  "run_id": "20260516_001421",
  "status": "success",
  "target_pdf_auto_acquired_count": 0,
  "target_pdf_auto_denominator_count": 5,
  "target_pdf_auto_yield_pct": 0.0,
  "operator_reviewable_count": 1,
  "operator_reviewable_yield_pct": 20.0,
  "ship_gate_status": "below_gate"
}
```

## Boundary

v448 is now the current Codex-driven Windows setup/bootstrap/bounded-weekly/UI
health/evidence lane. It is still not the owner/operator real-cycle sign-off.
The ship gate remains incomplete because the real operator sign-off is missing
and the latest bounded strict target PDF auto-yield is still `0.0%`.

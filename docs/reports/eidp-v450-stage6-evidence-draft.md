# EIDP v450 Stage 6 Evidence Draft

Updated: 2026-05-16

This draft records the v450 Windows setup, school-domain-override wiring,
bounded weekly, evidence-bundle, UI-health, and disk-retention evidence. It is
not a completed owner/operator real-cycle Stage 6 sign-off.

## Package

| Item | Value |
| --- | --- |
| ZIP | `dist/eidp-windows-v450.zip` |
| SHA256 | `07b64972c26c5f3d6e5d2ab3e3ec70b46a95bad56449b5f89ad71cd994c90cfb` |
| Package snapshot | `ad6d0179c50258f3abc4e06c58812aa6dcf5a21e` |
| Windows deploy path | `C:\Users\cyo20\EIDP-v450-ad6d017` |
| Non-Windows gate | `logs/release-gate-v450.json` |
| Canary evidence | `logs/win-v450-stage6/20260516_005535-summary.json` |
| RCA evidence | `logs/win-v450-stage6/20260516_005535-discovery-rca-batch-plan.json` |
| Evidence bundle | `logs/win-v450-stage6/stage6-evidence-20260516-005706.zip` |
| UI health evidence | `logs/win-v450-stage6/v450-ui-smoke-20260516-100014.json` |

## Evidence

| Check | Result | Notes |
| --- | --- | --- |
| Non-Windows release gate | pass | `logs/release-gate-v450.json` returned `ok=true`, package/source commit match, SHA sidecar match, validator/distribution tests `164 passed`, validator mypy/Ruff pass, discovery-gold predictions `44/44`, and both package verifier modes passed. |
| Windows transfer + SHA | pass | `dist/eidp-windows-v450.zip` and sidecar were copied to `C:\EIDP-staging`; `Get-FileHash` matched `07b64972c26c5f3d6e5d2ab3e3ec70b46a95bad56449b5f89ad71cd994c90cfb`. |
| Windows extract | pass | Expanded to `C:\Users\cyo20\EIDP-v450-ad6d017`; `BUILD_INFO.json` reports commit `ad6d0179c50258f3abc4e06c58812aa6dcf5a21e`, `git_dirty=false`, and `data\url-discovery\school_domain_overrides.csv` exists. |
| Setup | pass | `EIDP-setup.bat` completed; `scripts\validate_install.bat --after-setup --json` returned `ok=true`, `school_count=2418`, `school_fiscal_year_status_count=2418`, and `sqlite_integrity_check=ok`. |
| URL-only bootstrap | pass | `scripts\bootstrap_pdfs.bat --skip-discover --url-search off --school-url-crawl off` completed after downloading and aggregating all 47 prefecture seed artifacts. Step 2b loaded `school_domain_overrides.csv` with `count=3` and reported `school_override_inferred=3`. |
| Bounded weekly launcher | pass / below gate | Real `scripts\weekly_run.bat` exited `0` with `run_id=20260516_005535`; `methods` included `school_domain_override`; summary reported `crawled=5`, `found=3`, `downloaded=0`, `operator_reviewable_count=1`, `target_pdf_auto_acquired_count=0`, `target_pdf_auto_yield_pct=0.0`, and `ship_gate_status=below_gate`. |
| After-weekly validator | pass | `scripts\validate_install.bat --after-setup --after-weekly --json` returned `ok=true`, `last_run_status=success`, `sqlite_target_fy_target_pdf_school_count=0`, and `sqlite_target_fy_operator_reviewable_school_count=1`. |
| Recovery check | pass / action path skipped | `scripts\stage6_recovery_check.bat` returned `ok=true`, with scheduled-task action check skipped and the task execute path pointing at `C:\Users\cyo20\EIDP-v450-ad6d017\scripts\weekly_run.bat`. |
| Residual cleanup dry-run | pass | `scripts\stage6_residual_cleanup.bat --json` returned `ok=true`, `existing_count=0`, and `moved_count=0`. |
| Evidence bundle | pass | `logs\stage6-evidence-20260516-005706.zip` verified `ok=true` on Windows and Mac, with no forbidden/unsafe entries, no missing manifest patterns, and labels `bootstrap_logs`, `bootstrap_progress`, `build_info`, `diagnostics`, `discovery_evidence`, `discovery_rca`, `last_run`, `stage6_recovery`, `stage6_residual_cleanup`, and `weekly_run_logs`. |
| UI health smoke | pass | v450 launched Streamlit directly on `127.0.0.1:8501`; `/` returned HTTP `200`, and cleanup left no listener on `8501`. |
| Disk and artifact retention | pass | Mac pruning deleted v442 local ZIP and sidecar, removed local test caches, and left `project_total=1.9GiB`, `dist=940.2MiB`, `_temp=0B`, `logs=3.7MiB`, and protected `data=20.0MiB`. Windows pruning deleted v448/v442 staging ZIPs and deploy dirs, preserving v450 current plus v449 fallback; `scripts\disk_health_check.py --profile operator-win --json` returned `ok=true` with `app_root_total=850.7MiB`, `data\pdfs=0B`, `data\output=61.9KiB`, and `logs=122.5KiB`. |

## Canary Result

```json
{
  "run_id": "20260516_005535",
  "status": "success",
  "methods": [
    "prefecture_aggregator",
    "seed_csv",
    "corporation_pattern",
    "school_domain_override",
    "operator_manual",
    "scrapling_stealth"
  ],
  "target_pdf_auto_acquired_count": 0,
  "target_pdf_auto_denominator_count": 5,
  "target_pdf_auto_yield_pct": 0.0,
  "operator_reviewable_count": 1,
  "operator_reviewable_yield_pct": 20.0,
  "ship_gate_status": "below_gate"
}
```

## RCA Note

v450 fixes the v449 method wiring gap: the bounded weekly now crawls
`school_domain_override` entries. The Mode schools moved from the old
`nkz.ac.jp` corporation-root failure to the correct
`https://www.mode.ac.jp/tokyo` and `https://www.mode.ac.jp/osaka` school-level
entrypoints. The current bounded result still fails yield because those
entrypoints produced `no_pdf_candidates` during the strict current-FY PDF scan.
That is the next discovery/RCA problem, not a Windows packaging or setup
problem.

## Boundary

v450 is now the current Codex-driven Windows setup/bootstrap/bounded-weekly/UI
health/evidence lane. It is still not the owner/operator real-cycle sign-off.
The ship gate remains incomplete because the real operator sign-off is missing
and the latest bounded strict target PDF auto-yield is still `0.0%`.

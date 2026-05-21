# EIDP v452 Stage 6 Evidence Draft

Updated: 2026-05-16

This draft records the v452 Windows setup, six-entry school-domain override
bootstrap, bounded R7 weekly canary, evidence-bundle, UI-health, and disk
retention evidence. It is not a completed owner/operator real-cycle Stage 6
sign-off.

## Package

| Item | Value |
| --- | --- |
| ZIP | `dist/eidp-windows-v452.zip` |
| SHA256 | `fea164e8dc7bb8807a241a17d33a7bdaa7acaf9dadb66e85a9540618ee82c107` |
| Package snapshot | `d13cf3a212b2eedfe89e92c999f408a17cb06b62` |
| Windows deploy path | `C:\Users\cyo20\EIDP-v452-d13cf3a` |
| Non-Windows gate | `logs/release-gate-v452.json` |
| Canary evidence | `logs/win-v452-stage6/20260516_012251-summary.json` |
| RCA evidence | `logs/win-v452-stage6/20260516_012251-discovery-rca-batch-plan.json` |
| Evidence bundle | `logs/win-v452-stage6/stage6-evidence-20260516-012808.zip` |

## Evidence

| Check | Result | Notes |
| --- | --- | --- |
| Non-Windows release gate | pass | `logs/release-gate-v452.json` returned `ok=true`, package/source commit match, SHA sidecar match, full unit `1633 passed`, validator/distribution tests `164 passed`, validator mypy/Ruff pass, discovery-gold predictions `44/44`, and both package verifier modes passed. |
| Windows transfer + SHA | pass | `dist/eidp-windows-v452.zip` and sidecar were copied to `C:\EIDP-staging`; `Get-FileHash` matched `fea164e8dc7bb8807a241a17d33a7bdaa7acaf9dadb66e85a9540618ee82c107`. |
| Windows extract | pass | Expanded to `C:\Users\cyo20\EIDP-v452-d13cf3a`; `BUILD_INFO.json` reports commit `d13cf3a212b2eedfe89e92c999f408a17cb06b62`, `git_dirty=false`, and `data\url-discovery\school_domain_overrides.csv` exists. |
| Setup | pass | `EIDP-setup.bat` completed with `school_count=2418`, `school_fiscal_year_status_count=2418`, and `sqlite_integrity_check=ok`. |
| URL-only bootstrap | pass | `scripts\bootstrap_pdfs.bat --skip-discover --url-search off --school-url-crawl off` completed after downloading and aggregating all 47 prefecture seed artifacts. Step 2b loaded `school_domain_overrides.csv` with `count=6` and reported `school_override_inferred=6`. |
| Bounded R7 weekly launcher | pass | Real `scripts\weekly_run.bat` exited `0` with `EIDP_TARGET_FISCAL_YEAR=2025`, `run_id=20260516_012251`, `crawled=5`, `found=5`, `downloaded=1`, `new_document_ids=[1]`, `operator_reviewable_count=3`, `target_pdf_auto_yield_pct=20.0`, `operator_reviewable_yield_pct=60.0`, and `ship_gate_status=pass`. |
| Recovery check | pass / action path skipped | `EIDP-stage6-recovery.bat` returned `ok=true`, with scheduled-task action check skipped and the task execute path pointing at `C:\Users\cyo20\EIDP-v452-d13cf3a\scripts\weekly_run.bat`. |
| Residual cleanup dry-run | pass | `scripts\stage6_residual_cleanup.bat --json` returned `ok=true`, `existing_count=0`, and `moved_count=0`. |
| Evidence bundle | pass | `logs\stage6-evidence-20260516-012808.zip` verified `ok=true` on Windows and Mac, with no forbidden/unsafe entries, no missing manifest patterns, and labels `bootstrap_logs`, `bootstrap_progress`, `build_info`, `diagnostics`, `discovery_evidence`, `discovery_rca`, `last_run`, `stage6_recovery`, `stage6_residual_cleanup`, and `weekly_run_logs`. |
| UI health smoke | pass | v452 launched Streamlit directly on `127.0.0.1:8501`; `/` returned HTTP `200`, and cleanup left no listener on `8501`. |
| Disk and artifact retention | pass | Mac cleanup left `dist=753M`, `_temp=28K`, `logs=4.3M`, and protected `data=20M`. Windows cleanup preserved v452 current plus v450 fallback; v452 deploy totals `852.0MiB`, staging totals `402.9MiB`, `data\pdfs=0.8MiB`, `data\output=0.1MiB`, and `logs=0.2MiB`. |

## Canary Result

```json
{
  "run_id": "20260516_012251",
  "status": "success",
  "current_fy": 2025,
  "target_pdf_auto_acquired_count": 1,
  "target_pdf_auto_denominator_count": 5,
  "target_pdf_auto_yield_pct": 20.0,
  "operator_reviewable_count": 3,
  "operator_reviewable_yield_pct": 60.0,
  "ship_gate_status": "pass"
}
```

## RCA Note

v452 fixes the v450 Mode-school RCA gap by adding exact NKZ disclosure pages
above the Mode brand homepages. The bounded run accepted the Osaka Mode
FY2025 target PDF from
`https://www.nkz.ac.jp/clginfo/om/pdf/omZ-studyspt_13_25.pdf` and ingested
22 yearly rows. Tokyo and Nagoya Mode still require operator review because the
embedded target-form PDFs do not expose target-year evidence in strict mode.

## Boundary

v452 is the current Codex-driven Windows setup/bootstrap/bounded-weekly/UI
health/evidence lane. It is still not the owner/operator real-cycle sign-off,
and the bounded `20.0%` strict auto-yield is not the final production 60-70%
R8 gate.

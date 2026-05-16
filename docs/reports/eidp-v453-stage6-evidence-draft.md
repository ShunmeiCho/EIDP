# EIDP v453 Stage 6 Evidence Draft

Updated: 2026-05-16

This draft records the v453 Windows setup, bounded R7 weekly canary, evidence
bundle, UI-health, and disk-retention evidence. It is not a completed
owner/operator real-cycle Stage 6 sign-off.

## Package

| Item | Value |
| --- | --- |
| ZIP | `dist/eidp-windows-v453.zip` |
| SHA256 | `3a01a893c422b27b2d82dba6c55c349f8545c7c9a498de66390a202eed5793c3` |
| Package snapshot | `328e9540e468b1b7bddb7b0354b2f12194c93453` |
| Windows deploy path | `C:\Users\cyo20\EIDP-v453-328e954` |
| Non-Windows gate | `logs/release-gate-v453.json` |
| Canary evidence | `logs/win-v453-stage6/20260516_014639-summary.json` |
| RCA evidence | `logs/win-v453-stage6/20260516_014639-discovery-rca-batch-plan.json` |
| Evidence bundle | `logs/win-v453-stage6/stage6-evidence-20260516-014900.zip` |

## Evidence

| Check | Result | Notes |
| --- | --- | --- |
| Non-Windows release gate | pass | `logs/release-gate-v453.json` returned `ok=true`, package/source commit match, SHA sidecar match, full unit `1634 passed`, validator/distribution tests `164 passed`, validator mypy/Ruff pass, discovery-gold predictions `44/44`, and both package verifier modes passed. |
| Windows transfer + SHA | pass | `dist/eidp-windows-v453.zip` and sidecar were copied to `C:\EIDP-staging`; `Get-FileHash` matched `3a01a893c422b27b2d82dba6c55c349f8545c7c9a498de66390a202eed5793c3`. |
| Windows extract | pass | Expanded to `C:\Users\cyo20\EIDP-v453-328e954`; `BUILD_INFO.json` reports commit `328e9540e468b1b7bddb7b0354b2f12194c93453`, `git_dirty=false`, and `data\url-discovery\school_domain_overrides.csv` exists. |
| Setup | pass | `EIDP-setup.bat` completed with `school_count=2418`, `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`, and `wheel_count=78`. |
| URL-only bootstrap | pass | `scripts\bootstrap_pdfs.bat --skip-discover --url-search off --school-url-crawl off` completed after downloading and aggregating all 47 prefecture seed artifacts. Step 2b loaded `school_domain_overrides.csv` with `count=6` and reported `school_override_inferred=6`. |
| Bounded R7 weekly launcher | pass | Real `scripts\weekly_run.bat` exited `0` with `EIDP_TARGET_FISCAL_YEAR=2025`, `run_id=20260516_014639`, `crawled=5`, `found=5`, `downloaded=2`, `new_document_ids=[1, 2]`, `operator_reviewable_count=3`, `target_pdf_auto_yield_pct=40.0`, `operator_reviewable_yield_pct=60.0`, and `ship_gate_status=pass`. |
| Recovery check | pass / action path skipped | `EIDP-stage6-recovery.bat` returned `ok=true`, with scheduled-task action check skipped and the task execute path pointing at `C:\Users\cyo20\EIDP-v453-328e954\scripts\weekly_run.bat`. |
| Residual cleanup dry-run | pass | `scripts\stage6_residual_cleanup.bat --json` returned `ok=true`, `existing_count=0`, and `moved_count=0`. |
| Evidence bundle | pass | `logs\stage6-evidence-20260516-014900.zip` verified `ok=true` on Windows and Mac, with no forbidden/unsafe entries, no missing manifest patterns, and labels `bootstrap_logs`, `bootstrap_progress`, `build_info`, `diagnostics`, `discovery_evidence`, `discovery_rca`, `last_run`, `stage6_recovery`, `stage6_residual_cleanup`, and `weekly_run_logs`. |
| UI health smoke | pass | v453 launched Streamlit directly on `127.0.0.1:8501`; `/` returned HTTP `200`, and cleanup left no listener on `8501`. |
| Disk and artifact retention | pass | Mac cleanup left `_temp=0B`, `dist=753M`, `logs=4.4M`, and protected `data=20M`. Windows cleanup preserved v453 current plus v452 fallback in both staging and deploy directories. |

## Canary Result

```json
{
  "run_id": "20260516_014639",
  "status": "success",
  "current_fy": 2025,
  "target_pdf_auto_acquired_count": 2,
  "target_pdf_auto_denominator_count": 5,
  "target_pdf_auto_yield_pct": 40.0,
  "operator_reviewable_count": 3,
  "operator_reviewable_yield_pct": 60.0,
  "ship_gate_status": "pass"
}
```

## RCA Note

v453 improves the v452 bounded canary by inheriting the active fiscal-year
`dt` term for later `dd` application-form links on the NKHS disclosure page.
The bounded run accepted the Osaka Mode FY2025 target PDF and the Japanese
Institute Hokkaido FY2025 target PDF:

- `https://www.nkz.ac.jp/clginfo/om/pdf/omZ-studyspt_13_25.pdf`
- `https://mail.nkhs.ac.jp/release/2025/nkhs_application2025.pdf`

The remaining RCA queue has three items: Tokyo Mode remains a yearless embedded
target-form PDF, while the two NEEC schools currently expose only GPA/DP
non-target PDFs in the bounded registered-site path.

## Boundary

v453 is the current Codex-driven Windows setup/bootstrap/bounded-weekly/UI
health/evidence lane. It is still not the owner/operator real-cycle sign-off,
and the bounded `40.0%` strict auto-yield is not the final production 60-70%
R8 gate.

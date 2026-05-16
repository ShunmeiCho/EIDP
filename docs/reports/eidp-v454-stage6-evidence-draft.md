# EIDP v454 Stage 6 Evidence Draft

Updated: 2026-05-16

This draft records the v454 Windows setup, bounded R7 weekly canary, evidence
bundle, UI-health, and disk-retention evidence. It is not a completed
owner/operator real-cycle Stage 6 sign-off.

## Package

| Item | Value |
| --- | --- |
| ZIP | `dist/eidp-windows-v454.zip` |
| SHA256 | `0bbed01d95fe320cee70b826c63e8c500303b8a62c42d325ef2481764660b2e3` |
| Package snapshot | `48a346bb626be749adb72d1aeb6a684903f22049` |
| Windows deploy path | `C:\Users\cyo20\EIDP-v454-48a346b` |
| Non-Windows gate | `logs/release-gate-v454.json` |
| Canary evidence | `logs/win-v454-stage6/20260516_020806-summary.json` |
| RCA evidence | `logs/win-v454-stage6/20260516_020806-discovery-rca-batch-plan.json` |
| Evidence bundle | `logs/win-v454-stage6/stage6-evidence-20260516-020943.zip` |

## Evidence

| Check | Result | Notes |
| --- | --- | --- |
| Non-Windows release gate | pass | `logs/release-gate-v454.json` returned `ok=true`, package/source commit match, SHA sidecar match, full unit `1635 passed`, validator/distribution tests `164 passed`, validator mypy/Ruff pass, discovery-gold predictions `44/44`, and both package verifier modes passed. |
| Windows transfer + SHA | pass | `dist/eidp-windows-v454.zip` and sidecar were copied to `C:\EIDP-staging`; `Get-FileHash` matched `0bbed01d95fe320cee70b826c63e8c500303b8a62c42d325ef2481764660b2e3`. |
| Windows extract | pass | Expanded to `C:\Users\cyo20\EIDP-v454-48a346b`; `BUILD_INFO.json` reports commit `48a346bb626be749adb72d1aeb6a684903f22049`, `git_dirty=false`, and `data\url-discovery\school_domain_overrides.csv` exists. |
| Setup | pass | `EIDP-setup.bat` completed with `school_count=2418`, `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`, and `wheel_count=78`. |
| URL-only bootstrap | pass | `scripts\bootstrap_pdfs.bat --skip-discover --url-search off --school-url-crawl off` completed after downloading and aggregating all 47 prefecture seed artifacts. Step 2b loaded `school_domain_overrides.csv` with `count=6` and reported `school_override_inferred=6`. |
| Bounded R7 weekly launcher | pass | Real `scripts\weekly_run.bat` exited `0` with `EIDP_TARGET_FISCAL_YEAR=2025`, `run_id=20260516_020806`, `crawled=5`, `found=5`, `downloaded=2`, `new_document_ids=[1, 2]`, `operator_reviewable_count=5`, `target_pdf_auto_yield_pct=40.0`, `operator_reviewable_yield_pct=100.0`, and `ship_gate_status=pass`. |
| RCA bucket quality | pass | The two NEEC target application PDFs under `portal/syllabus/.../yoshiki.pdf` are now retained as `target_form_without_year_evidence` with `reason=target_fiscal_year_not_detected`; they are no longer hidden as `non_target_candidates_only`. |
| Recovery check | pass / action path skipped | `EIDP-stage6-recovery.bat` returned `ok=true`, with scheduled-task action check skipped and the task execute path pointing at `C:\Users\cyo20\EIDP-v454-48a346b\scripts\weekly_run.bat`. |
| Residual cleanup dry-run | pass | `scripts\stage6_residual_cleanup.bat --json` returned `ok=true`, `existing_count=0`, and `moved_count=0`. |
| Evidence bundle | pass | `logs\stage6-evidence-20260516-020943.zip` verified `ok=true` on Windows and Mac, with no forbidden/unsafe entries, no missing manifest patterns, and labels `bootstrap_logs`, `bootstrap_progress`, `build_info`, `diagnostics`, `discovery_evidence`, `discovery_rca`, `last_run`, `stage6_recovery`, `stage6_residual_cleanup`, and `weekly_run_logs`. |
| UI health smoke | pass | v454 launched Streamlit directly on `127.0.0.1:8501`; `/` returned HTTP `200`, and cleanup left no listener on `8501`. |
| Browser read-only navigation | pass | v454 rendered through SSH tunnel `127.0.0.1:18501 -> 127.0.0.1:8501` with Playwright title `EIDP Operator Console`. Snapshots/screenshots under `output/playwright/v454-ui-smoke/` cover `① 学校別タスク`, `② PDF確認・手入力`, `④ Excel プレビュー`, and `⑤ 設定（年度・OCR・API）`. Only navigation buttons were clicked; no write action was invoked. Cleanup left no listener on Windows `8501` or local `18501`. |
| Disk and artifact retention | pass | Mac cleanup left `_temp=0B`, `dist=754M`, `logs=4.5M`, and protected `data=20M`. Windows cleanup preserved v454 current plus v453 fallback in both staging and deploy directories. |

## Canary Result

```json
{
  "run_id": "20260516_020806",
  "status": "success",
  "current_fy": 2025,
  "target_pdf_auto_acquired_count": 2,
  "target_pdf_auto_denominator_count": 5,
  "target_pdf_auto_yield_pct": 40.0,
  "operator_reviewable_count": 5,
  "operator_reviewable_yield_pct": 100.0,
  "ship_gate_status": "pass"
}
```

## RCA Note

v454 keeps target application PDFs in the review/RCA path even when a negative
path token reduces the candidate score. This specifically changes the bounded
NEEC behavior from v453's `non_target_candidates_only` bucket to
`target_form_without_year_evidence` for:

- `https://www.neec.ac.jp/assets/contents/documents/portal/syllabus/kamata/portal_syllabus_kamata_yoshiki.pdf`
- `https://www.neec.ac.jp/assets/contents/documents/portal/syllabus/hachioji/portal_syllabus_hachioji_yoshiki.pdf`

Those PDFs still do not count as strict automatic acquisitions because the
bounded evidence did not prove FY2025 inside the PDF/page/URL. Tokyo Mode also
remains a yearless embedded target-form PDF.

The accepted bounded FY2025 target PDFs remain:

- `https://www.nkz.ac.jp/clginfo/om/pdf/omZ-studyspt_13_25.pdf`
- `https://mail.nkhs.ac.jp/release/2025/nkhs_application2025.pdf`

## Boundary

v454 is the current Codex-driven Windows setup/bootstrap/bounded-weekly/UI
health/evidence lane. It is still not the owner/operator real-cycle sign-off,
and the bounded `40.0%` strict auto-yield is not the final production 60-70%
R8 gate.

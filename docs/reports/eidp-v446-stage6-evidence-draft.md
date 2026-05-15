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
| UI health evidence | `logs/win-v446-stage6/v446-ui-smoke-20260516-080445.json` |
| Browser navigation evidence | `output/playwright/v446-ui-smoke/` |

## Evidence

| Check | Result | Evidence |
| --- | --- | --- |
| Mac package gate | pass | `logs/release-gate-v446.json` reports SHA sidecar match, package/source commit `e9f91ccbb51f82cb594be6567076df50276cc97a`, `source_dirty=false`, validator/distribution tests `164 passed`, and both package verifier modes pass. |
| Docs-only stale gate | pass with explicit stale allowance | `logs/release-gate-v446-docs-stale-allowed.json` reports `ok=true`, SHA sidecar match, and `stale=true` only because the source HEAD is the follow-up docs commit. |
| Windows transfer | pass | Win-side `Get-FileHash` matched SHA256 `e0436a08d12d09987f15f96c814de2290010714477e54ae0dcff0f290a3d3878`. |
| Packaged pruning helper | pass | `scripts\prune_release_artifacts.py` existed inside `C:\Users\cyo20\EIDP-v446-e9f91cc`; dry-run identified only v445 staging/deploy candidates, and `--apply` deleted those three candidates. |
| Windows retention | pass | `C:\EIDP-staging` now keeps only v442 and v446 ZIP/sidecar pairs; `C:\Users\cyo20` keeps only `EIDP-v442-22f1a98` and `EIDP-v446-e9f91cc`. |
| Operator real-cycle preflight | pass | `logs/win-v446-stage6/v446-real-cycle-preflight-20260516-082554.json` reports v446 SHA match, `C:` free `1062.44 GiB`, staging/deploy retention still v442+v446 only, no persisted canary or target-FY env vars, and no listener on `8501`. |
| Windows setup | pass | `EIDP-setup.bat` completed; `validate_install.bat --after-setup --json` returned `ok=true`, `school_count=2418`, `school_fiscal_year_status_count=2418`, and `sqlite_integrity_check=ok`. |
| URL-only bootstrap | pass | `scripts\bootstrap_pdfs.bat --skip-discover --url-search off --school-url-crawl off` completed after downloading and aggregating the 47 prefecture seed artifacts. |
| Bounded weekly canary | diagnostic pass / yield fail | `scripts\weekly_run.bat` exited `0` under `EIDP_WEEKLY_LIMIT=5`, `EIDP_WEEKLY_BATCH_SIZE=5`, `EIDP_WEEKLY_RATE_LIMIT=0.5`, and `EIDP_WEEKLY_REQUEST_TIMEOUT=8`. The summary reported `crawled=5`, `found=3`, `downloaded=0`, `operator_reviewable_count=1`, and `ship_gate_status=below_gate`. |
| After-weekly validator | pass | `validate_install.bat --after-setup --after-weekly --json` returned `ok=true`, `last_run_status=success`, `sqlite_target_fy_target_pdf_school_count=0`, and `sqlite_target_fy_operator_reviewable_school_count=1`. |
| Recovery check | pass / action path skipped | `scripts\stage6_recovery_check.bat` returned `ok=true` in wrapper-default mode, with scheduled-task action check skipped. |
| Residual cleanup dry-run | pass | `scripts\stage6_residual_cleanup.bat --json` returned `ok=true`, `existing_count=0`, and `moved_count=0`. |
| Evidence bundle | pass | `logs\stage6-evidence-20260515-225956.zip` verified `ok=true` on Windows and Mac, with no forbidden/unsafe entries, no missing manifest patterns, and all expected evidence labels present. |
| UI health smoke | pass | v446 launched through `scripts\launch.bat`; `/_stcore/health` and `/` both returned HTTP `200`, and cleanup left `listener_after_count=0`. |
| Browser read-only navigation | pass | SSH tunnel `127.0.0.1:18501 -> Windows 127.0.0.1:8501` rendered the real Streamlit UI. Snapshots captured `① 学校別タスク`, `PDF確認・手入力`, `Excel プレビュー`, and `⑤ 設定（年度・OCR・API）`; only navigation buttons were clicked. |

## Canary Result

v446 proves the current package can be transferred, set up, bootstrapped, bounded
through the real weekly launcher, rendered through the browser UI, and
mechanically bundled for Stage 6 evidence.
The bounded canary still does not meet the production yield gate:

| Metric | Value |
| --- | --- |
| `current_fy` | `2026` |
| `target_pdf_auto_acquired_count` | `0` |
| `target_pdf_auto_yield_pct` | `0.0` |
| `operator_reviewable_count` | `1` |
| `operator_reviewable_yield_pct` | `20.0` |
| `ship_gate_status` | `below_gate` |

## Retroactive Excel Boundary

A process-scoped FY2025/R7 browser Excel probe was attempted after the v446
browser navigation smoke. The UI rendered `2025年度（令和7年度）` and cleanup
confirmed no `.env` file was created at either the app root or sibling path, but
this v446 DB was initialized under FY2026 setup. The FY2025 Excel preview stayed
at `Excel出力可 0/2418`, so this attempt is diagnostic only and does not replace
the v442 R7 browser Excel proof.

## Next Operator Real-Cycle Checklist

Use this checklist for the next v446 operator-PC run. It is intentionally not a
retroactive proof and not a bounded canary.

1. Keep v446 as the current deploy and v442 as the fallback. If staging or
   deploy roots have additional old versions, run
   `python scripts\prune_release_artifacts.py --dist-dir C:\EIDP-staging --deploy-parent C:\Users\cyo20 --keep-latest 1 --keep-version 442 --json`
   first, review the dry-run, and add `--apply` only if the candidates are old
   versioned ZIPs, sidecars, or `EIDP-vNNN-<commit>` deploy directories.
2. Do not delete or edit `data\eidp.sqlite3`,
   `data\audit\manual-actions.jsonl`, `data\master.xlsx`, `data\pdfs\`, or
   operator-generated `data\output\*.xlsx` files during the run.
3. From `C:\Users\cyo20\EIDP-v446-e9f91cc`, verify the transferred ZIP hash
   against the SHA256 above, then run
   `scripts\validate_install.bat --after-setup --json`.
4. Clear canary variables before the real cycle:
   `EIDP_WEEKLY_LIMIT`, `EIDP_WEEKLY_BATCH_SIZE`, `EIDP_WEEKLY_RATE_LIMIT`, and
   `EIDP_WEEKLY_REQUEST_TIMEOUT` must be unset unless the result is explicitly
   recorded as diagnostic-only.
5. Do not persist `EIDP_TARGET_FISCAL_YEAR` in `.env`. For the current v1.0
   lane, use the default rolling target FY2026/R8 path.
6. Launch through `EIDP-start.bat`, have the operator open the four quick pages
   and the needed detailed pages, then run the normal weekly cycle from the
   packaged launcher. Record start/end time and any Defender, SmartScreen, proxy,
   Excel-lock, or UI error shown to the operator.
7. After the run, execute
   `scripts\validate_install.bat --after-setup --after-weekly --json`,
   `EIDP-stage6-evidence.bat`, and `EIDP-stage6-verify-evidence.bat`.
   Pull the evidence bundle back to Mac and verify it again with
   `scripts/verify_stage6_evidence.py`.
8. Copy the real values into
   `docs/runbooks/eidp-operator-e2e-template.md`: `last_run.status`,
   `current_fy`, crawled/found/downloaded counts, target PDF auto-yield,
   operator-reviewable count, `ship_gate_status`, evidence bundle path,
   recovery/residual-cleanup status, and owner/operator sign-off.

Stop before a v1.0 tag if the run remains `ship_gate_status=below_gate`, if the
target PDF auto-yield is still below the 60-70% ship line, or if the template
real-cycle rows are not fully populated by the owner/operator.

## Remaining Blocker

Do not sign this draft as Stage 6 complete. The remaining blocker is still the
operator-PC real-cycle sign-off with a populated KPI row and, later, the FY2026
production wet-run once current target-form PDFs are actually published.

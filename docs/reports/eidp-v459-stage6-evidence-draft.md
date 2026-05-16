# EIDP v459 Stage 6 Evidence Draft

Updated: 2026-05-16

This draft records the current v459 Windows bounded smoke. It is not the final
Stage 6 operator-PC real-cycle sign-off.

## Package

| Item | Evidence |
| --- | --- |
| Package | `dist/eidp-windows-v459.zip` |
| SHA256 | `1f50e574987a636b064c2a45ec870d1c6c8050ec036fc12a767caaed50e244b2` |
| BUILD_INFO commit | `50152a5f2bfc0b8f0a360ef87af5e4979b284f4a` |
| Windows root | `C:\Users\cyo20\EIDP-v459-50152a5` |
| Release gate | `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v459.zip` passed |

## Windows Smoke

| Check | Result |
| --- | --- |
| Transfer SHA | Win `Get-FileHash` matched the sidecar SHA256 |
| Extraction | `C:\Users\cyo20\EIDP-v459-50152a5` |
| Setup | `EIDP-setup.bat` exited `0`; `sqlite_integrity_check=ok`; `school_count=2418`; `school_fiscal_year_status_count=2418`; `wheel_count=78` |
| Setup validator | `scripts\validate_install.bat --after-setup --json` returned `ok=true` |
| Recovery check | `scripts\stage6_recovery_check.bat C:\Users\cyo20\EIDP-v459-50152a5\scripts\weekly_run.bat --json` returned `ok=true`, `action_matches_expected=true` |
| Cleanup tools | `rotate_audit_outbox.py --json` returned `rotate=false` for missing outbox; `prune_pdf_storage.py --json` returned `candidate_count=0` |
| Real-cycle entrypoints | ZIP and extracted Windows root both contain `EIDP-start.bat`, `EIDP-setup.bat`, `EIDP-stage6-evidence.bat`, `EIDP-stage6-verify-evidence.bat`, `EIDP-diagnose.bat`, `scripts\weekly_run.bat`, `scripts\validate_install.bat`, `scripts\stage6_recovery_check.bat`, and `scripts\diagnose.bat` |
| UI health | Root `EIDP-start.bat` served `_stcore/health=200` and root HTTP `200` on `127.0.0.1:8501`; cleanup left no listener |
| Browser read-only navigation | Mac Playwright over SSH tunnel clicked `① 学校別タスク`, `② PDF確認・手入力`, `④ Excel プレビュー`, and `⑤ 設定（年度・OCR・API）`; `output/playwright/v459-ui-smoke/summary.json` reported `hasJapaneseUi=true`, `hasTargetFiscalYear=true`, `hasErrorTraceback=false`, `navAllClicked=true`; screenshots `00-home.png` through `04-settings.png` were captured; cleanup removed the tunnel and left no Windows `8501` listener |

## Bounded Weekly

| Metric | Value |
| --- | --- |
| Process env | `EIDP_TARGET_FISCAL_YEAR=2025`, `EIDP_WEEKLY_LIMIT=5`, `EIDP_WEEKLY_BATCH_SIZE=5`, `EIDP_WEEKLY_RATE_LIMIT=0.5`, `EIDP_WEEKLY_REQUEST_TIMEOUT=8` |
| URL-only bootstrap | `seed_urls_imported=48`, `school_override_inferred=6`, `corporation_inferred=296` |
| `run_id` | `20260516_060230` |
| `last_run.status` | `success` |
| Crawled / found / downloaded | `5 / 5 / 2` |
| New documents | `[1, 2]` |
| Target PDF auto-yield | `40.0%` on the bounded R7 sample |
| Operator-reviewable yield | `100.0%` on the bounded R7 sample |
| Ship-gate status | `pass` for the bounded sample |
| Weekly validator | `scripts\validate_install.bat --after-setup --after-weekly --json` returned `ok=true` |

## Browser Excel

| Check | Result |
| --- | --- |
| Process env | `EIDP_TARGET_FISCAL_YEAR=2025` only for the Streamlit process |
| Preview page | `④ Excel プレビュー` showed `2025年度（令和7年度）`, `Excel出力可 2`, and `Excel対象行 7177` |
| Workbook generation | Playwright clicked `プレビュー workbook を生成` and `Excel ダウンロード` |
| Download | `output/playwright/v459-r7-excel-smoke/eidp_master.xlsx`, suggested filename `eidp_master.xlsx`, size `3,677,040` bytes |
| Workbook dimensions | `採録状況=2419x10`, `対象比率=10025x22`, `学科別=9748x83`, `在籍のみ抜粋=9748x19` |
| FY persistence check | Both checked paths, `C:\Users\cyo20\EIDP-v459-50152a5\.env` and `C:\Users\cyo20\EIDP-v459-50152a5.env`, were absent after the process-scoped run |
| Cleanup | Temporary local Playwright dependency, SSH tunnel, and Windows `8501` listener were removed |

## UI Write / Audit Sandbox

| Check | Result |
| --- | --- |
| Sandbox root | `C:\Users\cyo20\EIDP-v459-50152a5\_temp\v459-ui-write-sandbox`; copied SQLite DB, then removed after verification |
| Seed | `review_item#37` for `https://stage6-v459-ui-write-sandbox.example.invalid/` plus one pending `stage6_v459_ui_audit_flush_smoke` audit row |
| Browser action | Playwright opened `URL候補レビュー`, filled reason `v459 UI reject smoke`, clicked `却下`, opened `監査ログ`, and clicked `Outbox を flush` |
| UI result | URL candidate queue became empty; audit page reported `exported=2 already_present=0 failed=0` |
| Direct verification | `logs/win-v459-stage6/v459-ui-write-sandbox-result-final.json` returned `ok=true`, `pending_outbox=0`, `jsonl_line_count=2`, and `jsonl_action_ids_match_db=true` |
| Runtime DB safety | Real v459 runtime DB marker counts were `review_item=0`, `school_site=0`, `manual_action_log=0` |
| Cleanup | Remote sandbox, Windows `8501`, local `18505` tunnel, and temporary local Playwright dependency were removed |

## Evidence Bundle

| Item | Result |
| --- | --- |
| Bundle | `C:\Users\cyo20\EIDP-v459-50152a5\logs\stage6-evidence-20260516-070115.zip` |
| Verify JSON | `C:\Users\cyo20\EIDP-v459-50152a5\logs\stage6-evidence-verify-20260516-160115.json` |
| Verification | `ok=true`, `entry_count=12`, `missing_required_labels=[]` |
| Latest diagnostics | Root `EIDP-diagnose.bat` exited `0` and wrote `C:\Users\cyo20\EIDP-v459-50152a5\logs\diagnostics-20260516-160111.txt` before this bundle was collected |
| Mac copy | `logs/win-v459-stage6/stage6-evidence-20260516-070115.zip`, `logs/win-v459-stage6/stage6-evidence-verify-20260516-160115.json`, and `logs/win-v459-stage6/diagnostics-20260516-160111.txt` |
| Mac copy SHA256 | evidence ZIP `c4e68ee5b5f8c1cb8b74938fb369edf4c53c00efdd5624bac3c05e51ab7caf28`; verify JSON `66d1fc3f9b1247c8e1335a371a29b4f938a5dfa623ff55e2777b38289b627d78`; diagnostics `d79bc2c9a80eeaf385982a8fce177e4fec2ddfcb246cd537af220be224ffcb5c` |
| Transfer hash check | Windows `Get-FileHash` returned the same SHA256 values for the remote ZIP, verifier JSON, and diagnostics file as the Mac copies |
| Mac copy verification | `uv run python scripts/verify_stage6_evidence.py logs/win-v459-stage6/stage6-evidence-20260516-070115.zip` returned `ok=true`, `entry_count=12`, `missing_required_labels=[]` |
| Present labels | `bootstrap_logs`, `bootstrap_progress`, `build_info`, `diagnostics`, `discovery_evidence`, `discovery_rca`, `last_run`, `stage6_recovery`, `weekly_run_logs` |
| Expected missing | `stage6_residual_cleanup` was not run during this bounded smoke |

## Disk State

| Environment | Result |
| --- | --- |
| Mac dev | `ok=true`, `warn_count=0`, `block_count=0`, project `1.7GiB`, `dist=738.8MiB`, `_temp=0B`, protected `data=20.0MiB` |
| Win v459 root | `ok=true`, `warn_count=0`, `block_count=0`, app root `853.5MiB`, `data\pdfs=1.7MiB`, `data\output=40.0KiB`, `logs=117.6KiB` |
| Retention | Mac and Win staging retain v459 current plus v454 fallback; stale v458 package/deploy artifacts and v456 deploy dir were pruned |

## Open Gates

- The real operator-PC one-cycle sign-off remains open.
- FY2026/R8 production strict target-PDF auto-yield remains open.
- Operator workload `<=30%` remains open until a real cycle is measured.

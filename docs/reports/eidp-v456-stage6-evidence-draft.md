# EIDP v456 Stage 6 Evidence Draft

Updated: 2026-05-16
Package: `dist/eidp-windows-v456.zip`
Package snapshot: `f33ffc0e6fd801782f3e49fad3315adc64081f6f`
SHA256: `73b429bd21504b95b10cf7c45b5eda4e3bcd6bf9198cf8017f2740c89d0155d2`
Windows root: `C:\Users\cyo20\EIDP-v456-f33ffc0`

## Status

This is a bounded operator-PC smoke evidence draft. It proves transfer, setup,
URL-only bootstrap, bounded weekly execution, recovery, UI health, default
launcher, browser read-only navigation, UI write/audit sandbox,
R7 browser Excel generation/download, disk retention, and evidence-bundle
verification for v456. It is not the final operator real-cycle sign-off and does
not satisfy the production R8 strict target-PDF 60-70% gate.

## Evidence

- Mac gate: `logs/release-gate-v456.json` returned `ok=true`; `unit_full`
  reported `1637 passed`, validator/distribution tests reported `166 passed`,
  mypy/Ruff passed, and both package verifier modes passed.
- Docs-only current-source rerun: `logs/release-gate-v456-docs-current.json`
  returned `ok=true` with `docs_only_stale=true` for
  `docs/reports/current-release-status.md` and
  `docs/reports/eidp-current-objective-evidence-checklist.md`.
- Transfer: `C:\EIDP-staging\eidp-windows-v456.zip` matched sidecar SHA256
  `73b429bd21504b95b10cf7c45b5eda4e3bcd6bf9198cf8017f2740c89d0155d2`.
- Setup: `EIDP-setup.bat` exited `0`; independent
  `scripts\validate_install.bat --after-setup --json` returned `ok=true`,
  `sqlite_integrity_check=ok`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, and `wheel_count=78`.
- Disk: packaged `disk_health_check.py --profile operator-win --json` returned
  `warn_count=0`, `block_count=0`, `app_root_total=843.0MiB`, `data\pdfs=0B`,
  `data\output=0B`, and `logs=3.8KiB` after setup.
- Cleanup: Windows home cleanup removed 48 old loose `eidp-windows-v*.zip*`
  artifacts, freeing about `7.81GB`; packaged
  `scripts\prune_release_artifacts.py --keep-latest 2 --apply` then removed
  v453 staging/deploy artifacts, freeing another `1.11GB` and preserving v456
  current plus v454 fallback.
- UI health: direct Streamlit smoke returned `_stcore/health=ok` and root HTTP
  `200` on Windows `127.0.0.1:8501`; cleanup left no listener on `8501`.
- Default launcher: root-level packaged `EIDP-start.bat` launched
  `scripts\launch.bat` from `C:\Users\cyo20\EIDP-v456-f33ffc0`, returned
  `_stcore/health=ok` and root HTTP `200` on Windows `127.0.0.1:8501`, observed
  listener owner process `25704` before forced cleanup, and cleanup left no
  remaining `8501` listener.
- Browser read-only navigation: `scripts\launch.bat` ran the same v456 install,
  Mac tunnel `127.0.0.1:18501 -> Windows 127.0.0.1:8501` returned health `ok`,
  and Playwright rendered the real Streamlit UI with title
  `EIDP Operator Console`. Snapshots and screenshots under
  `output/playwright/v456-ui-smoke/` cover `① 学校別タスク`,
  `② PDF確認・手入力`, `④ Excel プレビュー`, and
  `⑤ 設定（年度・OCR・API）`; `browser-summary.json` confirms build `f33ffc0`
  and target FY `2026年度（令和8年度）`. Only sidebar navigation buttons were
  clicked; no write or workbook-generation action was invoked. Cleanup left no
  Mac `18501` or Windows `8501` listener.
- Browser UI write/audit sandbox: v456 ran against a disposable SQLite copy
  under `_temp\v456-ui-write-sandbox`. Playwright opened `URL候補レビュー`,
  rejected seeded `review_item#37` for
  `https://stage6-v456-ui-write-sandbox.example.invalid/` with reason
  `v456 UI reject smoke`, then opened `監査ログ` and clicked
  `Outbox を flush`. The UI reported `exported=2 already_present=0 failed=0`.
  Pulled verifier JSON
  `logs/win-v456-stage6/v456-ui-write-sandbox-result-final.json` returned
  `ok=true`, with `pending_outbox=0`, exported
  `stage6_v456_ui_audit_flush_smoke` and `url_candidate_rejected` rows, no
  `SchoolSite` for the rejected URL, matching JSONL action IDs, and real v456
  runtime DB marker counts all `0`. Screenshot/snapshot evidence is under
  `output/playwright/v456-ui-write-sandbox/`; cleanup stopped Windows `8501`,
  closed local `18501`, and removed the remote disposable sandbox.
- R7 browser Excel: v456 was launched with process-scoped
  `EIDP_TARGET_FISCAL_YEAR=2025`, rendered `④ Excel プレビュー` with
  `対象年度: 2025年度（令和7年度）`, `Excel出力可 2`, and `Excel対象行 7177`,
  generated workbook rows `採録状況=2418`, `対象比率=10024`, `学科別=9746`,
  and `在籍のみ抜粋=9746`, then downloaded
  `output/playwright/v456-r7-excel-smoke/eidp-master.xlsx`. Local `openpyxl`
  verified workbook size `3,677,041` bytes, sheets `採録状況`, `対象比率`,
  `学科別`, `在籍のみ抜粋`, and dimensions `2419x10`, `10025x22`, `9748x83`,
  and `9748x19`. Windows checks confirmed both checked v456 `.env` paths were
  absent; cleanup left no Mac `18501` or Windows `8501` listener.
- Recovery: `scripts\stage6_recovery_check.bat` with expected action
  `C:\Users\cyo20\EIDP-v456-f33ffc0\scripts\weekly_run.bat` returned `ok=true`
  and `action_matches_expected=true`.
- URL-only bootstrap: `scripts\bootstrap_pdfs.bat --skip-discover
  --url-search off --school-url-crawl off` completed; 47 prefecture seed
  artifacts were downloaded/aggregated; Step 2b reported seed URL
  `imported=48` and `school_domain_override` `count=6` / inferred `6`.
- Bounded weekly: `scripts\weekly_run.bat` with
  `EIDP_TARGET_FISCAL_YEAR=2025`, `EIDP_WEEKLY_LIMIT=5`,
  `EIDP_WEEKLY_BATCH_SIZE=5`, `EIDP_WEEKLY_RATE_LIMIT=0.5`, and
  `EIDP_WEEKLY_REQUEST_TIMEOUT=8` exited `0`; `last_run.json` recorded
  `run_id=20260516_034531`, `crawled=5`, `found=5`, `downloaded=2`,
  `new_document_ids=[1, 2]`, `target_pdf_auto_yield_pct=40.0`,
  `operator_reviewable_yield_pct=100.0`, and `ship_gate_status=pass`.
- Weekly validator: `scripts\validate_install.bat --after-setup --after-weekly
  --json` returned `ok=true`, `last_run_status=success`, `sqlite_target_fy=2025`,
  `sqlite_target_fy_target_pdf_school_count=2`, and
  `sqlite_target_fy_operator_reviewable_school_count=5`.
- Evidence bundle: `logs/win-v456-stage6/stage6-evidence-20260516-034752.zip`
  verified on Mac with `ok=true`, `entry_count=12`,
  `manifest_missing_patterns=[]`, `missing_required_labels=[]`, and present
  labels `bootstrap_logs`, `bootstrap_progress`, `build_info`, `diagnostics`,
  `discovery_evidence`, `discovery_rca`, `last_run`, `stage6_recovery`,
  `stage6_residual_cleanup`, and `weekly_run_logs`.
- Real-cycle preflight diagnostics: `scripts\diagnose.bat` wrote
  `logs/win-v456-stage6/diagnostics-20260516-134458.txt`. The diagnostic run
  returned `validate_core_rc=0`, `validate_after_setup_rc=0`,
  `stage6_recovery_rc=0`, `validate_after_weekly_rc=0`,
  `validate_after_weekly_ship_gate_rc=0`, and
  `retroactive_fiscal_year=2025` with `retroactive_ship_readiness_rc=0`.
  It also reported the expected FY2026 incompleteness via
  `ship_readiness_rc=1`; this is a preflight snapshot, not a real-cycle
  sign-off.

## Caveats

- The URL-only `--after-bootstrap` validator currently fails because
  `--skip-discover` progress does not emit ship-gate metric keys. The v456
  bounded weekly validator passed and is the authoritative acquisition smoke for
  this lane.
- The strict target-PDF yield remains `40.0%` on the bounded R7 canary, below
  the final production R8 target of 60-70%.
- No business operator completed and signed the full Stage 6 real-cycle
  template yet.

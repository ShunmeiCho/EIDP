# EIDP v442 Stage 6 Evidence Draft

Updated: 2026-05-16
Status: draft / not signed off

This document is the v442 Stage 6 evidence landing page. v442 is the current
Windows operator-PC candidate. It has Mac/non-Windows release-gate proof,
Windows transfer/setup proof, bounded weekly-runner proof, evidence-bundle
verification, browser UI navigation proof, and R7 browser Excel proof. It is
not a v1.0 sign-off because the owner/operator real-cycle row and the R8
production yield gate are still missing.

## Package Record

| Field | Value |
| --- | --- |
| Package | `dist/eidp-windows-v442.zip` |
| SHA256 | `4bf15f953be371b506b131ba59cf59c205259be1d7b49f084b94ddb78f66e0c7` |
| SHA256 sidecar | `dist/eidp-windows-v442.zip.sha256` |
| Package commit | `22f1a98ffbc3e0aeec2f658c5f1e77927045f14c` |
| Windows extract path | `C:\Users\cyo20\EIDP-v442-22f1a98` |
| Windows staging ZIP | `C:\EIDP-staging\eidp-windows-v442.zip` |
| Evidence bundle | `logs/win-v442-stage6/stage6-evidence-20260515-205932.zip` |
| Environment snapshot | `logs/win-v442-stage6/v442-environment-snapshot-20260516.json` |

## Mac Evidence

| Gate | Status | Evidence |
| --- | --- | --- |
| v442 package freshness at build time | pass | `logs/release-gate-v442.json` reports package/source commit `22f1a98ffbc3e0aeec2f658c5f1e77927045f14c`, SHA sidecar match, `source_dirty=false`, and full package verification. |
| v442 package integrity | pass | `dist/eidp-windows-v442.zip.sha256` and release-gate output both report SHA256 `4bf15f953be371b506b131ba59cf59c205259be1d7b49f084b94ddb78f66e0c7`. |
| v442 release gate | pass | `logs/release-gate-v442.json` returned `ok=true`: validator/distribution tests `164 passed`, validator mypy/Ruff passed, discovery-gold expected predictions matched `44/44`, and both package verifier modes passed. |
| Docs-only stale gates | pass | Post-evidence docs commits were checked with `--allow-docs-only-stale-package`; latest gate `logs/release-gate-v442-docs-only-stale-after-environment-snapshot.json` returned `ok=true` with stale paths limited to docs. |
| Local disk hygiene | pass | `_temp=0B`; current local retained package set is v442 current, v441 fallback, and latest alias. |

## Windows Evidence

| Gate | Status | Evidence |
| --- | --- | --- |
| Transfer + SHA | pass | v442 ZIP and sidecar were copied to `C:\EIDP-staging`; Windows SHA matched the expected digest. |
| Setup | pass | `EIDP-setup.bat` completed with SQLite integrity ok and `school_fiscal_year_status_count=2418`. |
| URL-only bootstrap | pass | `bootstrap_pdfs.bat --skip-discover --url-search off --school-url-crawl off` parsed 47 prefectures and added `official_school_sites_added=1311`. |
| Bounded weekly launcher canary | diagnostic pass / yield fail | Process env limited the run to 5 schools; `scripts\weekly_run.bat` exited `0`, `crawled=5`, `found=3`, `downloaded=0`, `target_pdf_auto_yield_pct=0.0`, and `ship_gate_status=below_gate`. |
| Recovery check | pass | `stage6_recovery_check.bat` reported `action_matches_expected=true`. |
| Residual cleanup | pass | `stage6_residual_cleanup.bat` reported existing residual count `0` and moved count `0`. |
| Evidence bundle | pass | `logs\stage6-evidence-20260515-205932.zip` verified on Windows and Mac with `ok=true` and required labels including `weekly_run_logs`. |
| Launcher health | pass | `scripts\launch.bat` served health/root HTTP `200` on `127.0.0.1:8501`; process was stopped after proof. |
| Browser navigation | pass | Mac tunnel `18501 -> 8501` rendered `① 学校別タスク`, `② PDF確認・手入力`, `④ Excel プレビュー`, and `⑤ 設定`. |
| R7 browser Excel | pass / retroactive only | Process-scoped `EIDP_TARGET_FISCAL_YEAR=2025` rendered R7 Excel preview, generated row counts `2418/10022/9719/9719`, downloaded `eidp-master.xlsx`, and did not persist `.env`. |
| Windows staging hygiene | pass | `C:\EIDP-staging` contains only v441 fallback and v442 current ZIP/sidecar. |
| Windows deploy hygiene | pass | `C:\Users\cyo20` contains only v441 fallback and v442 current EIDP-v* deploy directories. |

## Environment Snapshot

| Field | Value |
| --- | --- |
| Host / user | `JUNMING` / `junming` |
| OS | Microsoft Windows 11 Pro `10.0.26200` build `26200` |
| Locale | `culture=zh-CN`, `ui_culture=zh-CN` |
| Console encoding | output UTF-8 `65001`; input/ANSI/OEM `936` |
| CPU/RAM | i9-13900HK, 14 cores / 20 logical processors, `31.69 GB` RAM |
| Disk | C drive `1063.09 GB` free of `1888.66 GB` |
| Defender | enabled; real-time, behavior, IOAV, and on-access protection all true |
| SmartScreen | machine `Off`; user web-content evaluation `1` |
| Network / proxy | Wi-Fi `M1nG_5G`; IPv4/IPv6 connected; WinHTTP direct access |

## Stage 6 Boundary

| Requirement | Current v442 evidence | Status |
| --- | --- | --- |
| ZIP distribution -> setup -> browser UI offline operation | Transfer/SHA/setup/launcher/browser navigation are proven on v442. | Pass for deployment smoke |
| 47-prefecture official-list bootstrap | URL-only bootstrap parsed all 47 prefectures and added official school-site rows. | Pass for bootstrap smoke |
| Strict target-FY PDF discovery/download | Bounded weekly canary ran against FY2026 but downloaded 0 target PDFs. | Failing / not release-ready |
| pdfplumber/PyMuPDF/Tesseract extraction | Current v442 lane has no new full FY2026 target-PDF extraction workload. | Missing for real cycle |
| Append-only DepartmentYearly / SupportRecipient writes | Historical v408 sandbox and unit tests support the contract; v442 real-cycle write/audit delta is not captured. | Missing for real cycle |
| Excel template export | v442 R7 browser Excel export is proven; FY2026 production export remains below gate. | Retroactive pass / production missing |
| ManualActionLog audit | Historical v408 sandbox support exists; v442 owner/operator audit/outbox delta is not captured. | Missing for real cycle |
| Ship line 60-70% true target PDF / <=30% manual work | Latest v442 bounded canary has `target_pdf_auto_yield_pct=0.0` and `ship_gate_status=below_gate`. | Failing |
| Owner/operator sign-off | `docs/runbooks/eidp-operator-e2e-template.md` still needs real-cycle rows and signatures. | Missing |

## Next Windows Steps

1. Keep v442 as the current Stage 6 lane; keep v441 as fallback.
2. Have owner/operator perform the real-cycle click-through in
   `docs/runbooks/eidp-operator-e2e-template.md`.
3. Capture manual-entry, fiscal-year override, Excel preview/download, audit
   log/outbox flush, diagnostics, recovery, residual cleanup, and evidence
   bundle rows from the real cycle or an explicitly approved full-cycle copy.
4. Verify the resulting Stage 6 evidence bundle on Windows and Mac.
5. Record the owner/operator sign-off fields.
6. Do not promote v1.0 GA until the R8 production yield gate has evidence for
   true target-form auto-acquisition at 60-70% and estimated manual work at
   30% or lower.

Do not sign this draft until the v442 operator-PC real-cycle row exists.

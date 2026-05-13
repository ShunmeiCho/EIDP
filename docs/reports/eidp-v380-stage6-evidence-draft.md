# EIDP v380/v384 Stage 6 Evidence Draft

Updated: 2026-05-14
Status: **DRAFT / NOT COMPLETE**

This document maps the current v380 and v384 Windows UI/write evidence plus
newer v384 package/setup/OCR/read-only UI evidence to
`docs/runbooks/eidp-operator-e2e-template.md`. It is an evidence consolidation
draft, not a completed Stage 6 sign-off. The current evidence was collected
through SSH / Playwright / disposable DB sandboxes, not by a business operator
running one uninterrupted production cycle.

## Gate Interpretation

| Gate | Current result | Evidence |
| --- | --- | --- |
| Process gate / v1.0-rc | partial | v384 setup, diagnostics, UI service health, initial browser render, read-only quick navigation, FY2026 Excel disabled-state display, R7 Excel download, and manual-entry write; v380 URL-candidate write, audit flush, fiscal-year override write, SupportRecipient ingest smoke |
| FY2026/R8 yield gate / v1.0 GA | fail | `ship_readiness_rc=1`, `strict_target_pdf_schools=0`, `operator_reviewable_schools=0`, `excel_ready_schools=0`, `estimated_manual_workload_rate=1.0` |
| FY2025/R7 retroactive marker | pass for retroactive rehearsal only | `is_retroactive_fiscal_year=true`, `extracted_schools=2031`, `extracted_rate=0.84`, `retroactive_fiscal_year=2025`, `retroactive_ship_readiness_rc=0` |

## 1. Implementation Record

| Item | Record |
| --- | --- |
| Evidence date | 2026-05-13 to 2026-05-14 |
| Evidence host | Windows operator PC reachable as SSH host `win`; hostname observed as `JUNMING` |
| Operator | not yet captured |
| Owner attendance | not yet captured |
| Primary Windows UI evidence package | `dist/eidp-windows-v380.zip` |
| Primary UI package commit | `f6a5e6d46db7b0b836b18399e5b401362575c38d` |
| Primary UI package SHA256 | `1fef8d468ba2e7d882f7a3a774ccbbf071d1e1ee362ae62b8c4e458c576e5361` |
| Primary UI Windows extract path | `C:\Users\cyo20\EIDP-v380-f6a5e6d` |
| Latest Windows setup package | `dist/eidp-windows-v384.zip` |
| Latest Windows setup package commit | `75732b057a115afcebe35f9a40b831fac0ffa6f6` |
| Latest Windows setup package SHA256 | `2707def6337f3f35c63c9933a1805271dcf75d8bf7d8ece27c09ba8de72d31c0` |
| Latest Windows setup proof path | `C:\Users\cyo20\EIDP-v384-75732b0-setup-probe` |
| Latest Windows read-only UI proof path | `C:\Users\cyo20\EIDP-v384-75732b0-ui-nav-probe` |
| Latest Windows R7 Excel proof path | `C:\Users\cyo20\EIDP-v384-75732b0-r7-excel-probe` |
| Latest Windows manual-entry write proof path | `C:\Users\cyo20\EIDP-v384-75732b0-manual-entry-sandbox` |
| Latest package-level OCR evidence | v384 package commit `75732b057a115afcebe35f9a40b831fac0ffa6f6`, core SHA256 `2707def6337f3f35c63c9933a1805271dcf75d8bf7d8ece27c09ba8de72d31c0` |
| OCR add-on ZIP SHA256 | v383 smoke add-on `bd1e2c96dcd7ac17562d44c3338fbf8da0ac21a1b1e60386073c730775e8d853` |
| Playwright add-on ZIP SHA256 | not captured in this evidence set |
| Distribution verifier output file | not captured as a saved JSON artifact in this evidence set |

## 2. PC / Environment

| Item | Record |
| --- | --- |
| Windows version | `Microsoft Windows 11 Pro`, version `10.0.26200`, build `26200`, `AMD64` process architecture |
| Japanese locale | not Japanese; captured culture/UI/system locale were `zh-CN`; timezone was `Tokyo Standard Time` |
| Console encoding | `chcp` reported code page `936` with mojibake over SSH; prior commands used UTF-8 safeguards where needed |
| CPU cores | `13th Gen Intel(R) Core(TM) i9-13900HK`, `14` cores / `20` logical processors |
| RAM | `32453` MB visible, `16503` MB free at capture time |
| Free disk | `C:` size `1888.7` GB, free `1058.8` GB |
| Defender state | not captured |
| SmartScreen display | not captured |
| Network | SSH from Mac to Windows host `win`; local browser tunnel used `127.0.0.1:18501 -> Windows 127.0.0.1:8501` |
| Proxy / FW impact | no browser/network blocker observed in the smoke tests |

## 3. Evidence Commands / Artifacts

| Evidence | Result |
| --- | --- |
| Package transfer / extraction | v380 ZIP transferred, SHA256 matched, extracted to `C:\Users\cyo20\EIDP-v380-f6a5e6d` |
| `EIDP-setup.bat` | completed |
| After-setup validator | `ok=true`, no errors/warnings, `school_count=2418`, `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`, `wheel_count=78` |
| Diagnostics | `logs\diagnostics-20260513-231923.txt` |
| `eidp db-backup` smoke | backup opened successfully with `backup_objects=35`, `integrity=ok`, temp backup removed |
| Environment capture | `2026-05-14T00:51:48+09:00`; host `JUNMING`; Windows 11 Pro; i9-13900HK; 32 GB RAM; `C:` free `1058.8` GB |
| Task Scheduler query | task `EIDP Weekly Run` found, state `Ready`, action `"C:\Users\cyo20\EIDP-v380-f6a5e6d\scripts\weekly_run.bat"`, weekly trigger enabled from `2026-05-13T02:00:00`, last run `2026-05-11T02:00:00+09:00`, next run `2026-05-18T02:00:00+09:00`, last result `0` |
| OCR availability probe | v380 extract path had no `ocr-addon`; `detect_ocr_availability` returned `binary_path=null`, `has_jpn_traineddata=false`, `can_run=false`; the v380 packaged runtime also returned `runtime_free_ram_mb=0` because the Windows package lacks `psutil` |
| Source-side OCR RAM fallback fix | added a stdlib Windows `GlobalMemoryStatusEx` fallback; direct Windows probe returned `cpu_count=20`, `avail_phys_mb=16532`, `meets_ocr_default_threshold=true` |
| v381 OCR RAM fallback package probe | v381 disposable extraction under `C:\Users\cyo20\EIDP-v381-da29fee-runtime-probe` used the packaged runtime and returned `cpu_count=20`, `free_ram_mb=16242`, `ocr_auto_enable=true`; probe directory and uploaded v381 ZIP/sidecar were removed after capture |
| v382 OCR runtime gate negative probe | v382 disposable extraction under `C:\Users\cyo20\EIDP-v382-cc739c8-ocr-runtime-probe` ran `scripts\validate_windows_install.py . --require-ocr-runtime --json`; it returned `ok=false`, build commit `cc739c8704e45e37928a4ac55fa006766e5012dc`, `build_dirty=false`, and expected missing-file errors for `ocr-addon/tesseract/tesseract.exe` and `ocr-addon/tessdata/jpn.traineddata`; probe directory and uploaded v382 ZIP/sidecar were removed after capture |
| v382 OCR add-on runtime proof | smoke add-on `dist/eidp-ocr-addon-windows-v382-smoke.zip` was built from UB Mannheim Windows Tesseract `v5.4.0.20240606` plus local `jpn.traineddata`; verifier reported SHA256 `b39a07bb9367c2342c38d34fc1dddd06300d9ba7d5b5412f752b798008d1f431`, `entry_count=266`, `manifest_files=265`; disposable Windows extraction under `C:\Users\cyo20\EIDP-v382-cc739c8-ocr-addon-probe` returned `ok=true`, `ocr_tesseract_version="tesseract v5.4.0.20240606"`, and languages including `jpn` and `jpn_vert`; this proved runtime execution but not TSV OCR output parsing; probe directory and uploaded ZIPs were removed after capture |
| v383 package and OCR add-on verifier | v383 core ZIP `dist/eidp-windows-v383.zip` and latest alias share SHA256 `6faae698bffd8302e1352a538ff5f73064be7cde7d757d37a3f1ac5270e7dfe9`; `dist/eidp-ocr-addon-windows-v383-smoke.zip` includes `ocr-addon/tessdata/configs/tsv` and verifies as SHA256 `bd1e2c96dcd7ac17562d44c3338fbf8da0ac21a1b1e60386073c730775e8d853`, `entry_count=267`, `manifest_files=266`; `scripts/verify_windows_distribution.py ... --ocr-addon ... --require-demonstrated-discovery-patterns` returned `OK core` and `OK ocr-addon` for both the versioned ZIP and latest alias |
| v384 package and OCR add-on verifier | v384 core ZIP `dist/eidp-windows-v384.zip` and latest alias share SHA256 `2707def6337f3f35c63c9933a1805271dcf75d8bf7d8ece27c09ba8de72d31c0`; BUILD_INFO records commit `75732b057a115afcebe35f9a40b831fac0ffa6f6`, branch `sprint8-handoff-finalize`, and `git_dirty=false`; verifier returned `OK core` for v384 and latest alias plus `OK ocr-addon` for `dist/eidp-ocr-addon-windows-v383-smoke.zip` |
| v384 operator-PC setup and diagnostics proof | disposable Windows extraction under `C:\Users\cyo20\EIDP-v384-75732b0-setup-probe` expanded `dist/eidp-windows-v384.zip` after confirming the SHA256 sidecar; `scripts\first_setup.bat` returned `setup_rc=0`; `.\.venv\Scripts\python.exe scripts\validate_windows_install.py . --after-setup --json` returned `ok=true`, build commit `75732b057a115afcebe35f9a40b831fac0ffa6f6`, `build_dirty=false`, `wheel_count=78`, `school_count=2418`, `school_fiscal_year_status_count=2418`, and `sqlite_integrity_check=ok`; `EIDP-diagnose.bat` returned `diagnose_rc=0`; diagnostics `logs\diagnostics-20260514-020156.txt` included `validate_after_setup_rc=0`, FY2026 `operator_reviewable_schools=0`, FY2026 `excel_ready_schools=0`, FY2025 `is_retroactive_fiscal_year=true`, and `retroactive_ship_readiness_rc=0`; the harness observed `task_registered_to_v384=true`, then restored the original v380 `EIDP Weekly Run` task |
| v384 operator-PC UI service and browser render proof | disposable Windows extraction under `C:\Users\cyo20\EIDP-v384-75732b0-ui-probe` expanded and set up the same v384 core ZIP, then started Streamlit on Windows `127.0.0.1:8501`; remote health returned `status=200` / `body=ok`, local tunnel `127.0.0.1:18501 -> Windows 127.0.0.1:8501` returned HTTP `200 OK`, Browser/Playwright rendered title `EIDP Operator Console`, default page `① 学校別タスク`, target `2026年度（令和8年度）`, build `75732b0 / branch=sprint8-handoff-finalize`, `対象年度 要対応 2418`, `Excel出力可 0/2418 校`, and the initial acquisition warning; captured console messages reported `0` errors and `0` warnings; cleanup removed the v384 UI probe, stopped the service, confirmed `port_8501_listeners=0`, and left the scheduled task pointing at v380 |
| v384 operator-PC read-only quick-navigation proof | disposable Windows extraction under `C:\Users\cyo20\EIDP-v384-75732b0-ui-nav-probe` expanded and set up the same v384 core ZIP, then started Streamlit on Windows `127.0.0.1:8501` through the local tunnel; Browser/Playwright clicked only the five non-mutating quick navigation buttons: `PDF確認・手入力`, `③ 年度判定・修正`, `④ Excel プレビュー`, `⑤ 設定（年度・OCR・API）`, and back to `① 学校別タスク`; snapshots rendered `PDF確認・手入力`, `対象年度の判定・修正`, `Excel プレビュー` with `対象年度: 2026年度（令和8年度） / 対象範囲: 専門学校`, `設定` with the `バージョン`, `和暦 alias`, `OCR`, and `外部 API` sections, and the task page again; the Excel workbook-generation button remained disabled for empty FY2026 data; the settings save button was not clicked; incremental console capture reported `Total messages: 5 (Errors: 0, Warnings: 0)`; cleanup removed the v384 UI-nav probe, stopped the service, confirmed `port_8501_listeners=0`, and left the scheduled task pointing at v380 |
| v384 operator-PC retroactive FY2025 Excel preview/download proof | disposable Windows extraction under `C:\Users\cyo20\EIDP-v384-75732b0-r7-excel-probe` expanded and set up the same v384 core ZIP; Streamlit was started with process-scoped `EIDP_TARGET_FISCAL_YEAR=2025` and no `.env` write, then opened through the local tunnel; the `④ Excel プレビュー` page showed `対象年度: 2025年度（令和7年度）`, `抽出済み学校 2031`, and `Excel対象行 7150`; the `プレビュー workbook を生成` button generated the in-memory workbook and exposed `Excel ダウンロード`; browser download saved `eidp_master.xlsx` with size `3,728,651` bytes; the workbook opened with sheets `採録状況`, `対象比率`, `学科別`, and `在籍のみ抜粋`; `openpyxl` row counts were `2419`, `10023`, `9721`, and `9721` including headers, while Streamlit stdout export counts were `2418`, `10022`, `9719`, and `9719`; cleanup removed the probe and upload files, confirmed no `8501` listener remained, and left the scheduled task pointing at v380 |
| v384 operator-PC manual-entry browser save proof | disposable Windows extraction under `C:\Users\cyo20\EIDP-v384-75732b0-manual-entry-sandbox` expanded and set up the same v384 core ZIP, then used a copied DB from the v380 package-local `eidp db-backup` output; the seed inserted one FY2026 `parse_failed` document with source URL `https://example.com/eidp-v384-manual-entry-smoke.pdf`; Browser/Playwright opened `② PDF確認・手入力`, saw `表示 1 / 待機 1 件`, expanded the `日本工学院専門学校` row, filled `V384手入力学科` with capacity `40`, enrollment `35`, international students `2`, graduates `30`, advanced `5`, employed `24`, other `1`, previous enrollment `36`, dropouts `1`, dropout rate `0.0278`, duration `2`, and reason `v384 UI manual entry smoke`, then clicked `保存`; post-save UI showed the queue empty for that view; direct SQLite verification found the document `ingest_status="ingested"`, one `department_yearly` row with `revision=1`, `is_current=1`, `extraction_method="manual"`, `extraction_confidence=1`, `verified=1`, three `manual_entry` audit rows for `department`, `department_yearly`, and `document`, `support_recipient_rows_for_doc=0`, and zero matching marker rows in the real v380 runtime DB; cleanup removed the probe and confirmed `port_8501_listeners=0` |
| v384 operator-PC OCR runtime gate proof | disposable Windows extraction under `C:\Users\cyo20\EIDP-v384-75732b0-ocr-runtime-probe` expanded `dist/eidp-windows-v384.zip` plus `dist/eidp-ocr-addon-windows-v383-smoke.zip` after confirming the v384 core SHA256 sidecar; `runtime\python\python.exe scripts\validate_windows_install.py . --require-ocr-runtime --json` returned `ok=true`, build commit `75732b057a115afcebe35f9a40b831fac0ffa6f6`, `build_dirty=false`, `wheel_count=78`, packaged Tesseract path `C:\Users\cyo20\EIDP-v384-75732b0-ocr-runtime-probe\ocr-addon\tesseract\tesseract.exe`, version `tesseract v5.4.0.20240606`, and languages including `jpn` and `jpn_vert` |
| v383 OCR image + copied-DB write proof | disposable Windows extraction under `C:\Users\cyo20\EIDP-v383-effcd58-ocr-write-sandbox` generated `data\ocr-write-smoke.png`, ran packaged Tesseract through `run_tesseract_on_image(..., output_format="tsv")`, returned `ocr_full_text="V383 OCR WRITE SMOKE 2026"` with `ocr_avg_confidence=0.952`, then used `save_manual_entries(..., method="ocr_tesseract")` against a copied DB to write one `DepartmentYearly` row with `extraction_confidence=0.95`, `verified=true`, promote the document `ocr_pending -> ingested`, and emit three `manual_entry` audit rows; real v380 runtime DB marker counts were all `0`; probe directory and uploaded ZIPs were removed after capture |
| Post-v383 OCR ingest source propagation | focused unit coverage proves image-PDF ingest uses the packaged/system Tesseract TSV wrapper when available and records `ocr_tesseract` confidence breakdowns on both `DepartmentYearly` and `SupportRecipient`; this is code-level proof only, not an operator-PC real target-form OCR smoke |
| v384 UI health | remote `/_stcore/health` returned `200 ok`; tunneled local `/_stcore/health` returned HTTP `200 OK`; cleanup left `port_8501_listeners=0` |
| v384 Browser render | Browser/Playwright title `EIDP Operator Console`; default page `① 学校別タスク`; target `2026年度（令和8年度）`; build `75732b0`; console errors/warnings `0` |
| v384 read-only quick navigation | Browser/Playwright clicked the five non-mutating quick navigation buttons and rendered task, PDF manual-entry, fiscal-year override, Excel preview, and settings pages; no save/edit/write button was clicked |
| v384 manual-entry write | Browser/Playwright saved one `PDF確認・手入力` row in a disposable copied DB; post-save SQLite verification found one manual `DepartmentYearly` row, three `manual_entry` audit rows, and zero matching real-runtime marker rows |
| v384 FY2026 Excel disabled-state | Excel preview rendered `対象年度: 2026年度（令和8年度） / 対象範囲: 専門学校`; workbook-generation button remained disabled for empty current-year data |
| v384 FY2025/R7 Excel download | process-scoped R7 UI generated workbook, exposed `Excel ダウンロード`, and downloaded `eidp_master.xlsx` with size `3,728,651` bytes |
| SSH tunnel note | `ssh -o ClearAllForwardings=no` was required because local `Host win` clears command-line forwards |

## 4. Setup Result

| Step | Result | Evidence |
| --- | --- | --- |
| v384 disposable ZIP extraction | pass | `C:\Users\cyo20\EIDP-v384-75732b0-setup-probe`; core SHA256 sidecar matched |
| v384 `scripts\first_setup.bat` | pass | `setup_rc=0`; `school_count=2418`; `school_fiscal_year_status_count=2418`; `sqlite_integrity_check=ok`; `wheel_count=78` |
| v384 after-setup validator | pass | `ok=true`, no errors/warnings, build commit `75732b057a115afcebe35f9a40b831fac0ffa6f6`, `build_dirty=false` |
| v384 diagnostics | pass | `diagnose_rc=0`; `logs\diagnostics-20260514-020156.txt`; `validate_after_setup_rc=0`; `retroactive_ship_readiness_rc=0` |
| v384 scheduler restoration | pass | setup registered the task to the v384 probe during setup, then the harness restored the original task containing `EIDP-v380-f6a5e6d`; restored task did not contain `EIDP-v384-75732b0-setup-probe` |
| v384 `launch.bat` / Streamlit startup equivalent | pass | package-local Streamlit run returned remote and tunneled health `200 ok` |
| v384 `学校別タスク` initial page | pass | title `EIDP Operator Console`, build `75732b0`, target `2026年度（令和8年度）`, `対象年度 要対応 2418`, `Excel出力可 0/2418 校`, console errors/warnings `0` |
| v384 read-only quick navigation | pass | clicked only `PDF確認・手入力`, `③ 年度判定・修正`, `④ Excel プレビュー`, `⑤ 設定（年度・OCR・API）`, and back to `① 学校別タスク`; all pages rendered; incremental console capture had `0` errors and `0` warnings |
| v384 Excel preview disabled-state | pass | `Excel プレビュー` rendered target `2026年度（令和8年度）`; workbook-generation button stayed disabled for empty FY2026 data |
| v384 R7 Excel preview/download | pass | process-scoped `EIDP_TARGET_FISCAL_YEAR=2025`; `抽出済み学校 2031`; `Excel対象行 7150`; browser downloaded `eidp_master.xlsx` size `3,728,651` bytes |
| v384 manual-entry browser save | pass | disposable copied DB; UI saved `V384手入力学科`; document promoted `parse_failed -> ingested`; one manual `DepartmentYearly` row; three `manual_entry` audit rows; no real-runtime marker rows |
| ZIP extraction | pass | separate v380 directory created |
| `EIDP-setup.bat` | pass | setup completed |
| `.venv` creation | pass | package-local Python commands and Streamlit ran |
| DB bootstrap | pass | `data\eidp.sqlite3`, `sqlite_integrity_check=ok` |
| master import | pass | `school_count=2418` |
| fiscal-year task bootstrap | pass | `school_fiscal_year_status_count=2418` |
| Task Scheduler registration | pass | `EIDP Weekly Run` found in `Ready` state, action points at v380 `scripts\weekly_run.bat`, weekly trigger enabled |
| `launch.bat` / Streamlit startup | pass | health smoke and browser render passed |
| `学校別タスク` initial page | pass | title and target metrics rendered |
| `詳細 operator` collapsed by default | pass | read-only nav smoke observed detail expander behavior |

## 5. Four-Step E2E Mapping

### Step 1: PDF Collection

| Metric | Value |
| --- | ---: |
| Target schools | 2418 |
| Saitama sandbox crawled sites | 5 |
| Saitama sandbox candidate-found sites | 5 |
| Strict FY2026 PDFs downloaded | 0 |
| Discovery evidence lines | 2084 |
| RCA items | 5 |
| Runtime DB mutation | 0 matching runtime `school_site`, `review_item`, `document` rows from the sandbox smoke |

Notes: This proves bounded official-index discovery mechanics on the v380
Windows package. It does not prove the FY2026/R8 yield gate.

### Step 2: Target Fiscal-Year Judgment

| Metric | Value |
| --- | ---: |
| FY2026 strict target PDF schools | 0 |
| FY2026 operator-reviewable schools after fresh setup diagnostics | 0 |
| FY2025 retroactive extracted schools | 2031 |
| FY2025 retroactive extracted rate | 0.84 |
| Fiscal-year override browser flow | pass in sandboxed browser write smoke |

Notes: R7 retroactive evidence is valid as rolling-FY rehearsal evidence only.
It must not be counted as FY2026/R8 current-year ship yield.

Fiscal-year override browser example:

| Document | From | To | Result |
| --- | ---: | ---: | --- |
| `https://example.com/eidp-v380-fiscal-override-smoke.pdf` | 2025 | 2026 | UI submitted `年度を確定` with reason `v380 UI fiscal override smoke`; `Document.fiscal_year=2026`, `fiscal_year_override=2026`; source FY2025 `DepartmentYearly`, `SupportRecipient`, and `SchoolYearStatus` rows were demoted; new FY2026 current rows were inserted; real runtime DB had `0` matching document/department/audit rows |

### Step 3: Transcription / Manual Entry / OCR

| Metric | Value |
| --- | ---: |
| v384 manual-entry UI DepartmentYearly rows | 1 sandbox row |
| Manual-entry audit rows | 3 sandbox rows |
| SupportRecipient ingest revisions | 2 sandbox rows |
| OCR image execution | v383 sandbox image smoke returned `V383 OCR WRITE SMOKE 2026` |
| Latest package OCR runtime gate | v384 disposable operator-PC validator returned `ok=true` with packaged Tesseract `v5.4.0.20240606` and `jpn` / `jpn_vert` language support |
| OCR-sourced DepartmentYearly rows | 1 sandbox row in copied DB |
| OCR-sourced SupportRecipient confidence propagation | code-level unit proof; no operator-PC target-form smoke yet |
| DepartmentChange explicit registrations | 0 |
| Runtime DB mutation | 0 matching runtime rows for v384 manual-entry and SupportRecipient smoke markers |

Manual-entry example:

| Document | School | Row | Result |
| --- | --- | --- | --- |
| `https://example.com/eidp-v384-manual-entry-smoke.pdf` | `日本工学院専門学校` | `V384手入力学科` | `DepartmentYearly` `revision=1`, `is_current=1`, `extraction_method="manual"`, `extraction_confidence=1`, `verified=1`; document promoted `parse_failed -> ingested`; three `manual_entry` audit rows emitted |

SupportRecipient ingest example:

| Revision | annual_total | grand_total | is_current |
| ---: | ---: | ---: | --- |
| 1 | 100 | 100 | false |
| 2 | 120 | 120 | true |

OCR image write example:

| Document | OCR text | Row | Result |
| --- | --- | --- | --- |
| `https://example.com/eidp-v383-ocr-write-smoke.pdf` | `V383 OCR WRITE SMOKE 2026` | `V383 OCR WRITE SMOKE Department` | copied-DB `DepartmentYearly` wrote `extraction_method="ocr_tesseract"`, `extraction_confidence=0.95`, `verified=true`; document promoted `ocr_pending -> ingested`; three `manual_entry` audit rows emitted; real runtime DB marker counts remained `0` |

### Step 4: Excel Preview / Output

| Metric | Result |
| --- | --- |
| FY2026 Excel preview display | pass |
| FY2026 workbook generation | disabled as expected because current-year transcribed rows are `0` |
| FY2025/R7 retroactive workbook generation | pass on v384 |
| FY2025/R7 browser download | pass on v384; suggested `eidp_master.xlsx`, saved size `3,728,651` bytes |
| Downloaded workbook sheet counts | v384 `openpyxl`: `採録状況=2419`, `対象比率=10023`, `学科別=9721`, `在籍のみ抜粋=9721` including headers |
| Export sheet counts in Streamlit stdout | v384 stdout: `採録状況=2418`, `対象比率=10022`, `学科別=9719`, `在籍のみ抜粋=9719` |
| Excel file retained as release artifact | no; temp download was removed after verification |

## 6. KPI Result

| KPI | Target | Actual | Judgment |
| --- | ---: | ---: | --- |
| `ship_readiness_rc` | 0 | 1 | fail |
| strict target PDF auto acquisition | >= 60% | 0.0% on current Windows evidence | fail |
| estimated manual workload | <= 30% | 100% after fresh setup diagnostics | fail |
| FY2026 Excel ready | >= 60% | 0 | fail |
| retroactive FY marker | `is_retroactive_fiscal_year=true` | true | pass for rehearsal only |
| `retroactive_ship_readiness_rc` | record value | 0 | pass for rehearsal only |
| Stage 6 process completeness | 1 uninterrupted operator cycle | not yet captured | incomplete |

## 7. Audit / Outbox

| Item | Result |
| --- | --- |
| Audit log page display | pass in browser smoke |
| URL-candidate rejection audit | pass; one `url_candidate_rejected` row in sandbox |
| Manual-entry audit | pass on v384; three `manual_entry` rows in sandbox |
| Fiscal-year override audit | pass; four `fiscal_year_override` rows in sandbox for `department_yearly`, `support_recipient`, `school_year_status`, and `document` |
| JSONL outbox flush | pass; `exported=1 already_present=0 failed=0` in sandbox |
| Runtime DB mutation from sandbox tests | none observed for smoke markers |

## 8. Known Gaps

| Gap | Status |
| --- | --- |
| Real business operator one-cycle execution | missing |
| Owner sign-off | missing |
| Business operator sign-off | missing |
| FY2026/R8 yield gate | failing / publication-lag dependent |
| OCR add-on runtime proof on operator PC | latest v384 disposable validator proves packaged OCR add-on detection/runtime execution with `--require-ocr-runtime`; v383 adds TSV config packaging plus OCR image extraction and `ocr_tesseract` DepartmentYearly write proof in a disposable copied DB; post-v383 source proves `ocr_tesseract` confidence propagation to SupportRecipient in unit coverage; real target-form OCR extraction and operator-PC SupportRecipient OCR write remain unproven |
| Excel output file retained as signed artifact | missing |

## 9. Release Decision

| Decision item | Result |
| --- | --- |
| Stage 2-5c Windows VM gate | source/package evidence present, not re-audited here |
| Operator PC one cycle complete | no |
| KPI owner approval | no |
| Runbook corrections reflected | partial |
| Remaining P0/P1 bug | no new P0/P1 from these smokes; release gate still blocked by missing Stage 6 sign-off and FY2026/R8 yield |

Conclusion:

```text
no-go for v1.0 GA
beta / v1.0-rc evidence consolidation may continue
```

Owner sign-off:

```text
Name:
Date:
Decision:
```

Business operator sign-off:

```text
Name:
Date:
Decision:
```

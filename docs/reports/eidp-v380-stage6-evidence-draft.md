# EIDP v380 Stage 6 Evidence Draft

Updated: 2026-05-14
Status: **DRAFT / NOT COMPLETE**

This document maps the current v380 Windows evidence to
`docs/runbooks/eidp-operator-e2e-template.md`. It is an evidence consolidation
draft, not a completed Stage 6 sign-off. The current evidence was collected
through SSH / Playwright / disposable DB sandboxes, not by a business operator
running one uninterrupted production cycle.

## Gate Interpretation

| Gate | Current result | Evidence |
| --- | --- | --- |
| Process gate / v1.0-rc | partial | v380 setup, diagnostics, browser render, read-only nav, Excel preview, R7 Excel download, URL-candidate write, audit flush, manual-entry write, fiscal-year override write, SupportRecipient ingest smoke |
| FY2026/R8 yield gate / v1.0 GA | fail | `ship_readiness_rc=1`, `strict_target_pdf_schools=0`, `operator_reviewable_schools=0`, `excel_ready_schools=0`, `estimated_manual_workload_rate=1.0` |
| FY2025/R7 retroactive marker | pass for retroactive rehearsal only | `is_retroactive_fiscal_year=true`, `extracted_schools=2031`, `extracted_rate=0.84`, `retroactive_fiscal_year=2025`, `retroactive_ship_readiness_rc=0` |

## 1. Implementation Record

| Item | Record |
| --- | --- |
| Evidence date | 2026-05-13 to 2026-05-14 |
| Evidence host | Windows operator PC reachable as SSH host `win`; hostname observed as `JUNMING` |
| Operator | not yet captured |
| Owner attendance | not yet captured |
| EIDP package | `dist/eidp-windows-v380.zip` |
| Package commit | `f6a5e6d46db7b0b836b18399e5b401362575c38d` |
| Package SHA256 | `1fef8d468ba2e7d882f7a3a774ccbbf071d1e1ee362ae62b8c4e458c576e5361` |
| Windows extract path | `C:\Users\cyo20\EIDP-v380-f6a5e6d` |
| Latest package-level OCR evidence | v383 package commit `effcd58efa50c8b9478a7dc762947e030236d65e`, core SHA256 `6faae698bffd8302e1352a538ff5f73064be7cde7d757d37a3f1ac5270e7dfe9` |
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
| v383 OCR image + copied-DB write proof | disposable Windows extraction under `C:\Users\cyo20\EIDP-v383-effcd58-ocr-write-sandbox` generated `data\ocr-write-smoke.png`, ran packaged Tesseract through `run_tesseract_on_image(..., output_format="tsv")`, returned `ocr_full_text="V383 OCR WRITE SMOKE 2026"` with `ocr_avg_confidence=0.952`, then used `save_manual_entries(..., method="ocr_tesseract")` against a copied DB to write one `DepartmentYearly` row with `extraction_confidence=0.95`, `verified=true`, promote the document `ocr_pending -> ingested`, and emit three `manual_entry` audit rows; real v380 runtime DB marker counts were all `0`; probe directory and uploaded ZIPs were removed after capture |
| UI health | `/_stcore/health` returned `200 ok`; Streamlit `1.57.0`; cleanup `remaining_streamlit_processes=0` |
| Browser render | Playwright title `EIDP Operator Console`; default page `① 学校別タスク`; target `2026年度（令和8年度）`; build `f6a5e6d` |
| SSH tunnel note | `ssh -o ClearAllForwardings=no` was required because local `Host win` clears command-line forwards |

## 4. Setup Result

| Step | Result | Evidence |
| --- | --- | --- |
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
| v380 manual-entry UI DepartmentYearly rows | 1 sandbox row |
| Manual-entry audit rows | 3 sandbox rows |
| SupportRecipient ingest revisions | 2 sandbox rows |
| OCR image execution | v383 sandbox image smoke returned `V383 OCR WRITE SMOKE 2026` |
| OCR-sourced DepartmentYearly rows | 1 sandbox row in copied DB |
| DepartmentChange explicit registrations | 0 |
| Runtime DB mutation | 0 matching runtime rows for manual-entry and SupportRecipient smoke markers |

Manual-entry example:

| Document | School | Row | Result |
| --- | --- | --- | --- |
| `https://example.com/eidp-v380-manual-entry-smoke.pdf` | `日本工学院専門学校` | `V380手入力学科` | `DepartmentYearly` `revision=1`, `is_current=1`, `extraction_method="manual"`, `extraction_confidence=1`, `verified=1`; document promoted `parse_failed -> ingested` |

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
| FY2025/R7 retroactive workbook generation | pass |
| FY2025/R7 browser download | pass; suggested `eidp_master.xlsx`, saved size `3,728,651` bytes |
| Export sheet counts in Streamlit stdout | `採録状況=2418`, `対象比率=10022`, `学科別=9719`, `在籍のみ抜粋=9719` |
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
| Manual-entry audit | pass; three `manual_entry` rows in sandbox |
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
| OCR add-on runtime proof on operator PC | add-on detection/runtime execution proven in disposable v382 probe; v383 adds TSV config packaging plus OCR image extraction and `ocr_tesseract` DepartmentYearly write proof in a disposable copied DB; real target-form OCR extraction and SupportRecipient OCR write remain unproven |
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

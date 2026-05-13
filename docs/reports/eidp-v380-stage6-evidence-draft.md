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
| OCR add-on ZIP SHA256 | not captured in this evidence set |
| Playwright add-on ZIP SHA256 | not captured in this evidence set |
| Distribution verifier output file | not captured as a saved JSON artifact in this evidence set |

## 2. PC / Environment

| Item | Record |
| --- | --- |
| Windows version | not captured |
| Japanese locale | inferred from operator flow and source data; not explicitly captured |
| Console encoding | not captured for v380 evidence; prior commands used UTF-8 safeguards where needed |
| CPU cores | not captured |
| RAM | not captured |
| Free disk | not captured for this evidence draft |
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
| Task Scheduler registration | not captured | no v380-specific scheduler query included in this evidence set |
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
| OCR execution PDFs | not exercised in this evidence set |
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
| OCR add-on runtime proof on operator PC | missing in this evidence set |
| Task Scheduler registration query | missing in v380 evidence set |
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

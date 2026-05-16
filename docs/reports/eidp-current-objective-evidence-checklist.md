# EIDP Current Objective Evidence Checklist

Updated: 2026-05-17
Latest Mac/non-Windows package snapshot: `9a94226b243fba691936db46c1fc11ef7c9debbd`
Status: **NOT COMPLETE**

This checklist maps the long-term EIDP objective to concrete artifacts and gates.
It is intentionally explicit about lane boundaries: `dist/eidp-windows-v464.zip`
is the latest Mac/non-Windows release-gate-clean package from package snapshot
`9a94226` and includes explicit target-FY propagation into ingestion plus the
packaged Stage 6 return-artifact verifier. v463 remains the latest
Windows-transferred side-by-side target-FY override canary package: it was
SHA-checked, extracted to `C:\Users\cyo20\EIDP-v463-4de0aa8`,
setup-validated, and package-local FY override canary-proven. v462 remains the
latest Windows side-by-side shared-cache canary package. v460 remains the active
Windows scheduled-task, operator-cycle, companion handoff docs, disk-retention,
read-only UI-health, and browser-navigation lane at
`C:\Users\cyo20\EIDP-v460-01e4427`. v459 remains the latest
evidence-bundle-proven, default-launcher-proven, R7 browser Excel
generation/download-proven, bounded-weekly-smoked, and UI write/audit sandbox
support package. v456 and v454 remain historical support for broader UI
write/audit sandbox regression. The active owner/fallback Windows lane remains
v460 current plus v459 fallback; v462/v463 are side-by-side proof lanes, and
stale v454 package/deploy artifacts were pruned after v460 validation. v442
remains historical support for the fuller R7 parity workbook,
and v408 remains historical support for broader copied-DB UI write paths. The
real operator cycle is still missing, and the production R8 yield gate is still
not proven. A second v460 FY2026 weekly probe after URL bootstrap was stopped
after about 9h41m because shared corporation domains were re-crawled repeatedly;
it produced no new `last_run.json` and is a v1.1 performance finding, not
release evidence.

Package note: `dist/eidp-windows-v464.zip` was built from
`9a94226b243fba691936db46c1fc11ef7c9debbd` with SHA256
`6b95d9f3e06d70a0018119b2665070cf3af735e01b61920f6492234e174bd378`.
`logs/release-gate-v464.json` returned `ok=true`, including `1673 passed` full
unit, validator unit/mypy/Ruff, discovery-gold checks, package verification,
and demonstrated-pattern package verification. v463 remains the latest
retroactive-matrix package:
`logs/release-gate-v463-retroactive-matrix.json` returned `ok=true` for
FY2025/FY2024/FY2023 against old-package references regenerated from the frozen
v459 ZIP/wheel into `_temp/v459-reference2-fy2025/`,
`_temp/v459-reference2-fy2024/`, and `_temp/v459-reference2-fy2023/`; all three
v463 isolated exports matched with `missing_rows=0`, `extra_rows=0`, and
`differing_fields=0`. The current Windows staging execution pointer remains
v460 at `C:\Users\cyo20\EIDP-v460-01e4427`: v463 side-by-side
transfer/setup/FY-override canary passed, but v463 has not been weekly-smoked,
UI-health-smoked, evidence-bundled, or made the scheduled-task target.

## Objective Restatement

EIDP must let one Windows operator process 1,700+ Japanese vocational schools
each rolling fiscal year by discovering official school pages, finding true
target-FY institution-requirement confirmation PDFs in strict mode, extracting
only sufficiently confident rows, writing append-only database records, exporting
the Excel template, auditing all operator actions, and running offline from a ZIP
with double-click setup and browser UI.

Release success is not full automation. The shipping line is true target-form PDF
auto-acquisition of 60-70% and estimated operator manual work at 30% or lower.

## Prompt-To-Artifact Checklist

| Requirement | Current artifacts / evidence | Status |
| --- | --- | --- |
| 47 prefecture official lists seed school URLs | `scripts/verify_windows_distribution.py` verifier contract; `docs/reports/current-release-status.md` records 47 prefecture seeds and official-index bounded smokes; source HEAD preserves semantic trailing slashes for gold-set disclosure seed entrypoints while keeping normalized idempotency | Packaged in v407; live coverage remains partially proven |
| Strict target-FY PDF discovery excludes stale fallback from success | `src/eidp/scraper/pdf_discovery.py`; `src/eidp/scraper/discovery_evidence_summary.py`; `tests/unit/test_pdf_discovery.py`; v375 heading/update-date tests pass; source HEAD also guards romanized-only renewal-form hints in both strong application and weak form-shape detection, prioritizes yearless target-form evidence over older-year target evidence in RCA triage, inherits same-section support-system headings for year-only target-form links so they enter the download budget before generic `様式4` PDFs, and caches identical shared corporation-root HTTP GETs within one run without caching PDFs or per-school scoring decisions. v463 packages the cache and the explicit target-FY ingestion propagation fix, passed the non-Windows gate, and its Windows package-local FY override canary proved forecast scoped FY2027 and retroactive scoped FY2026 both write `Document.is_current_year=true` under intentionally opposite process settings. v462 remains the Windows package-local stub cache proof with `http_cache_hits=9`, `http_cache_misses=7`, and `shared_url_call_count=1` for two schools sharing one URL. | Mechanically guarded; cache behavior proven in Windows package; live yield gate still failing |
| PDF extraction uses pdfplumber / PyMuPDF / Tesseract and writes only confidence >= 0.70 | OCR/package verifier contracts; v384 OCR image/write smoke; unit coverage for confidence propagation; source HEAD names the default `0.70` review threshold via `DEFAULT_CONFIDENCE_REVIEW` and keeps Excel/exporter env-threshold tests green | Mechanically proven for smokes; no current strict target-form OCR workload evidence |
| DepartmentYearly / SupportRecipient append-only writes | Unit coverage plus v384 copied-DB UI/manual-entry, fiscal override, and SupportRecipient ingest smokes; v407 disposable operator-PC UI sandbox proved manual-entry write and fiscal-year override clones for DepartmentYearly, SupportRecipient, and SchoolYearStatus with prior FY2024 rows marked non-current; v408 disposable UI sandbox repeated the browser-write surface with one manual FY2025 `DepartmentYearly` row (`capacity=40`, `enrollment=28`, `extraction_method=manual`, `extraction_confidence=1.0`, `verified=true`) and one fiscal-year override that marked FY2024 `DepartmentYearly`, `SupportRecipient`, and `SchoolYearStatus` rows non-current while FY2025 current rows were present | Proven on sandboxed/copy DB paths including v408; real operator one-cycle proof still missing |
| Excel template export | v459 process-scoped FY2025 browser Excel smoke launched with `EIDP_TARGET_FISCAL_YEAR=2025`, rendered `④ Excel プレビュー` with `Excel出力可 2`, `Excel対象行 7177`, and `2025年度（令和7年度）`, clicked `プレビュー workbook を生成`, exposed `Excel ダウンロード`, and downloaded `output/playwright/v459-r7-excel-smoke/eidp_master.xlsx`; local `openpyxl` verified sheets `採録状況`, `対象比率`, `学科別`, `在籍のみ抜粋` with dimensions `2419x10`, `10025x22`, `9748x83`, `9748x19`; Win-side checks reported both checked v459 `.env` locations missing, so the retroactive FY was not persisted. v460 adds Mac-side hardening that serializes preview bytes and drops the workbook handle from Streamlit session state, but no v460 browser Excel run has been executed yet. v456, v454, and v442 remain historical browser support, while historical v408 R7 CLI/browser exports and v437 FY2025/FY2024/FY2023 non-Windows retroactive matrix remain regression support. Fresh v463 Mac retroactive matrix proof now passes FY2025/FY2024/FY2023 against references regenerated from the frozen v459 package, with zero missing/extra rows and zero differing fields. FY2026 export remains disabled on current setup evidence | Latest browser Excel proof is v459 R7 support; latest Mac algorithm regression proof is v463 three-year matrix; v460 full operator-cycle Excel output still pending |
| ManualActionLog audits every operator action | v384 manual-entry, fiscal override, URL-candidate reject, and audit outbox browser smokes; source HEAD dedups audit outbox archives by matching filename stem for both default and custom outbox paths and ignores archive symlinks; v407 disposable UI sandbox flushed seven operator actions with `exported=7 already_present=0 failed=0` and `jsonl_exported_at_present=true` for all seven rows; v408 disposable UI sandbox repeated the audit path through `監査ログ`, showing `JSONL outbox 未送信=7`, `Outbox を flush` result `exported=7 already_present=0 failed=0`, and seven rows with `jsonl_exported_at_present=true` in direct DB verification; current v459 disposable UI write/audit sandbox rejected seeded `review_item#37` in `URL候補レビュー` and flushed two pending audit rows, with `logs/win-v459-stage6/v459-ui-write-sandbox-result-final.json` reporting `ok=true`, `pending_outbox=0`, exported `stage6_v459_ui_audit_flush_smoke` and `url_candidate_rejected` rows, matching JSONL action IDs, no `SchoolSite` for the rejected URL, and real runtime DB marker counts all `0`. v460 adds Mac-side lock-held row-count control and stale manual-entry widget cleanup coverage, but no v460 real operator audit sequence has been run | Current v459 proves URL-candidate reject + audit-outbox flush on a disposable DB; broader manual-entry/fiscal-override UI write coverage remains historical v408/v384; real operator one-cycle proof still missing |
| ZIP distribution, double-click setup, browser UI offline operation | v460 ZIP/SHA was transferred to `C:\EIDP-staging`, matched sidecar SHA `ce5fa49b8c30900a33b31fd317c6846ffe5839053f2bdd1ffdeb8cca2113129c`, expanded to `C:\Users\cyo20\EIDP-v460-01e4427`, and `EIDP-setup.bat` completed with SQLite integrity, `school_fiscal_year_status_count=2418`, and `wheel_count=78`; independent `scripts\validate_install.bat --after-setup --json` returned `ok=true`. Recovery check with expected action `C:\Users\cyo20\EIDP-v460-01e4427\scripts\weekly_run.bat` returned `ok=true` and `action_matches_expected=true`, and Task Scheduler now points to the v460 weekly runner. A post-doc-refresh recovery check also returned `ok=true`, `action_matches_expected=true`, all residual paths `exists=false`, and was copied to `logs/win-v460-stage6/stage6-recovery-20260517-064336.json` with SHA256 `41dd47aee0a304371cab5633397017f45e4f1a1d090b186986d48c49cf38acf6`. Root `EIDP-diagnose.bat` wrote `C:\Users\cyo20\EIDP-v460-01e4427\logs\diagnostics-20260516-170035.txt`; Mac copy SHA256 is `6b4d566433db64c730737f925f0559e9b06582eed4cb0b6cd51f0623f153b445`. v460 direct Streamlit read-only browser smoke over `127.0.0.1:18506` clicked `① 学校別タスク`, `② PDF確認・手入力`, `④ Excel プレビュー`, and `⑤ 設定（年度・OCR・API）`; `output/playwright/v460-ui-smoke/summary.json` reports `hasV460Build=true`, `hasErrorTraceback=false`, and `navAllClicked=true`. A diagnostic v460 evidence bundle was created but correctly rejected with `ok=false`, `missing_required_labels=["last_run"]`, proving setup evidence cannot pass as Stage 6 release evidence. Plan A then ran `scripts\weekly_run.bat` on v460, wrote `last_run.json`, and produced verifier-accepted evidence ZIP `stage6-evidence-20260516-094432.zip` with `ok=true`; however the run selected no schools (`no_crawlable_url_school_count=2418`) and KPI stayed `not_measured`. A later URL bootstrap populated `school_site_count=1838`, `schools_with_url=1805`, and `schools_with_verified_url=1312`; the second FY2026 weekly probe after that ran about 9h41m, wrote `234238` rejection rows, produced no new `last_run.json`, and exposed repeated corporation-domain recrawls rather than KPI evidence. v463 was transferred side-by-side, SHA-checked, extracted to `C:\Users\cyo20\EIDP-v463-4de0aa8`, setup-validated with `ok=true`, and then the scheduled task was restored to v460; a package-local v463 FY override canary using a temp DB returned `ok=true`. v462 remains support for the package-local shared-cache canary. v460 20260516 companion docs were transferred, Windows hash-checked, and expanded under `C:\EIDP-staging\v460-operator-docs`; the 20260517 companion docs refresh was then transferred, Windows hash-checked, and expanded under `C:\EIDP-staging\v460-operator-docs-20260517`, superseding the 20260516 package for operator reading without changing the core v460 package, Windows app root, scheduled task, or release gate. A focused first-read audit over the Windows staging README, owner request, real-cycle card, E2E template, and 20260517 manifest found no `first_setup.bat` and no old `v460-operator-docs\` path; the expected `v460-operator-docs-20260517` paths were present. The short owner/operator request is mirrored in git as `docs/runbooks/eidp-v460-owner-request-20260516.txt` with SHA256 matching `dist/eidp-v460-owner-request-20260516.txt`. Post-v460 cleanup retained v460 current plus v459 fallback as the active owner/fallback lane, with disk health `warn_count=0` / `block_count=0`; later v462/v463 side-by-side proof directories are separate. v459 remains support for URL-only bootstrap, bounded weekly, evidence-bundle verification, default launcher, R7 browser Excel, and disposable UI write/audit sandbox. v456 remains historical R7 browser Excel and UI write/audit sandbox support; v408 remains historical copied-DB coverage for broader UI write paths. | Current v460 transfer/setup/validate/recovery/scheduler/docs/UI health/read-only nav/disk retention proven; v463 side-by-side transfer/setup/FY-override canary proven; v462 side-by-side cache canary proven; v460 Plan A evidence bundle proven but KPI not measured; real operator one-cycle missing |
| Stage 6 one operator-PC cycle | `docs/runbooks/eidp-operator-e2e-template.md`; `docs/reports/current-release-status.md` Stage 6 boundary | Missing |
| Ship gate: true target-form auto-acquisition 60-70% | v460 Plan A wrote `last_run.json` but recorded `target_pdf_auto_yield_pct=null` and `ship_gate_status=not_measured` because there were no crawlable URL schools in the fresh v460 DB. The second v460 FY2026 run after URL bootstrap did not complete and should not be used as KPI evidence; live R8 yield is record-only during the May publication-lag window, not the v1.0 algorithm-proof gate. v459 bounded real R7 weekly canary crawled 5 target-missing schools after URL-only bootstrap, found 5 candidate pages, downloaded 2 PDFs, ingested `new_document_ids=[1, 2]`, and recorded `target_pdf_auto_yield_pct=40.0`; this holds the v456/v454 strict yield while keeping reviewable target-form evidence visible. Current HEAD also prevents `ok_strict` from passing unless both `strict_target_pdf` and `excel_ready` meet the strict threshold | Failing; not a v1.0 algorithm verdict |
| Ship gate: estimated manual work <= 30% | v460 Plan A recorded `operator_reviewable_yield_pct=null` and diagnostics report `estimated_manual_workload_rate=1.0`; v459 bounded R7 canary recorded `operator_reviewable_count=5`, `operator_reviewable_yield_pct=100.0`, and `ship_gate_status=pass` on the 5-school bounded sample. Real operator sign-off and R8 production workload evidence remain missing | Failing |

## Current Release Boundary

- Latest v463 Mac/non-Windows package lane:
  package snapshot `4de0aa8c3021cb5a2ac2e29ba5fc36a24fcc6582`, SHA256
  `81ffabd2d538e5b9757d7096b383acba5b081c9ee82c389184bb59676e38e3e0`.
  `logs/release-gate-v463.json` returned `ok=true` with full unit
  `1669 passed`, validator package checks, mypy/Ruff, discovery-gold checks,
  package verification, and demonstrated-pattern verification. v463 adds
  explicit target-FY propagation through ingestion for retroactive/forecast
  weekly runs. Windows side-by-side transfer, SHA check, extraction to
  `C:\Users\cyo20\EIDP-v463-4de0aa8`, `EIDP-setup.bat`, and
  `scripts\validate_install.bat --after-setup --json` passed. The weekly
  scheduled task was restored to v460 afterward, and a v460 recovery check
  confirmed `action_matches_expected=true`. The v463 package-local FY override
  canary result is
  `logs/win-v463-fy-override-canary/fy-override-canary-result.json` with
  `ok=true`, forecast scoped FY2027 writing `document_fiscal_year=2027`, and
  retroactive scoped FY2026 writing `document_fiscal_year=2026`, both with
  `document_is_current_year=true`.
  The v463 retroactive Excel matrix
  `logs/release-gate-v463-retroactive-matrix.json` returned `ok=true` with
  `case_count=3`. Per-year logs
  `logs/release-gate-v463-retroactive-fy2025-reference.json`,
  `logs/release-gate-v463-retroactive-fy2024-reference.json`, and
  `logs/release-gate-v463-retroactive-fy2023-reference.json` each returned
  zero business-value diffs against references generated from the frozen v459
  package. The failed preflight that used raw `data/master.xlsx` was discarded
  as invalid reference selection, not an algorithm failure.

- Latest v462 side-by-side Windows cache lane:
  Windows side-by-side transfer, SHA check, extraction to
  `C:\Users\cyo20\EIDP-v462-e1da33f`, `EIDP-setup.bat`, and
  `scripts\validate_install.bat --after-setup --json` passed. The weekly
  scheduled task was restored to v460 afterward, and a v460 recovery check
  confirmed `action_matches_expected=true`. The v462 package-local stub cache
  canary result is `logs/win-v462-cache-canary/cache-canary-stub-result.json`
  with `ok=true`, `http_cache_hits=9`, and `shared_url_call_count=1`.
  This does not make v462 the owner-cycle execution candidate yet.

- Current v460 Mac/non-Windows and Windows setup/recovery lane: package
  snapshot `01e44279238aaef9127ed9b578e29dc8e0070499`, SHA256
  `ce5fa49b8c30900a33b31fd317c6846ffe5839053f2bdd1ffdeb8cca2113129c`.
  `scripts/run_non_windows_release_gates.py dist/eidp-windows-v460.zip
  --json --output logs/release-gate-v460.json` returned `ok=true` for SHA
  sidecar, package/source freshness, full unit `1665 passed`, validator
  distribution unit/mypy/Ruff, discovery-gold checks, package verify, and
  demonstrated-pattern package verify. v460 contains the Round 4 operator-cycle
  hardening for Excel preview session memory, lock-held manual-entry row-count
  controls, stale manual-entry widget cleanup, and evidence recorder closing.
  Windows transfer/setup/recovery, Task Scheduler pointer update, read-only UI
  health/browser navigation, companion docs transfer, diagnostic evidence-bundle
  rejection, and disk health all passed on
  `C:\Users\cyo20\EIDP-v460-01e4427`. The follow-up docs-only stale gate
  `logs/release-gate-v460-docs-only-stale-after-handoff-docs.json` returned
  `ok=true`, `docs_only_stale=true`, and changed paths limited to
  `docs/reports/current-release-status.md`,
  `docs/reports/eidp-v460-stage6-evidence-draft.md`, and
  `docs/runbooks/eidp-v460-real-cycle-card.md`.
  A later source-only `.env.example` documentation commit `2768f02` is outside
  the v460 ZIP and does not change the current Windows execution candidate.

- Current v459 bounded weekly/evidence support lane: URL-only bootstrap downloaded and
  aggregated all 47 prefecture seed artifacts, Step 2b reported seed URL
  `imported=48`, `school_override_inferred=6`, and `corporation_inferred=296`.
  Bounded R7 weekly with `EIDP_TARGET_FISCAL_YEAR=2025`,
  `EIDP_WEEKLY_LIMIT=5`, `EIDP_WEEKLY_BATCH_SIZE=5`,
  `EIDP_WEEKLY_RATE_LIMIT=0.5`, and `EIDP_WEEKLY_REQUEST_TIMEOUT=8` returned
  `run_id=20260516_060230`, `downloaded=2`, `new_document_ids=[1, 2]`,
  `target_pdf_auto_yield_pct=40.0`, `operator_reviewable_yield_pct=100.0`, and
  `ship_gate_status=pass`. `scripts\validate_install.bat --after-setup
  --after-weekly --json` returned `ok=true`. Root `EIDP-diagnose.bat` exited
  `0`, wrote `logs\diagnostics-20260516-160111.txt`, and the refreshed v459
  evidence bundle
  `C:\Users\cyo20\EIDP-v459-50152a5\logs\stage6-evidence-20260516-070115.zip`
  verified with `ok=true`, `entry_count=12`, and `missing_required_labels=[]`.
  Mac copy `logs/win-v459-stage6/stage6-evidence-20260516-070115.zip` also
  verified locally with `ok=true`; SHA256
  `c4e68ee5b5f8c1cb8b74938fb369edf4c53c00efdd5624bac3c05e51ab7caf28`.
  Windows `Get-FileHash` matched the Mac copy hashes for the ZIP, verifier JSON,
  and diagnostics file.
  Mac disk health reported `warn=0 block=0`, and Win disk health reported
  `warn_count=0 block_count=0`.

- Historical v456 browser/evidence lane: package snapshot
  `f33ffc0e6fd801782f3e49fad3315adc64081f6f`, SHA256
  `73b429bd21504b95b10cf7c45b5eda4e3bcd6bf9198cf8017f2740c89d0155d2`.
  `scripts/run_non_windows_release_gates.py dist/eidp-windows-v456.zip
  --output logs/release-gate-v456.json` returned `ok=true`, with
  package/source freshness at `f33ffc0`, SHA sidecar match, full unit
  `1637 passed`, validator/distribution tests returning `166 passed`,
  validator mypy/Ruff passing, discovery-gold expected predictions passing,
  and both package verifier modes passing. Mac cleanup then removed the failed
  v455 package/sidecar while retaining v456/v454/v453; `disk_health_check`
  reported `warn=0 block=0`. Windows transfer to `C:\EIDP-staging` matched the
  sidecar SHA, extraction to `C:\Users\cyo20\EIDP-v456-f33ffc0` succeeded,
  `EIDP-setup.bat` exited `0`, `validate_install --after-setup` returned
  `ok=true`, and packaged disk health returned `warn_count=0` / `block_count=0`.
  URL-only bootstrap downloaded/aggregated 47 prefecture seed artifacts, Step
  2b reported seed URL `imported=48`, and `school_domain_override` loaded
  `count=6` / inferred `6`. Bounded R7 weekly with `EIDP_WEEKLY_LIMIT=5`
  returned `downloaded=2`, `new_document_ids=[1, 2]`,
  `target_pdf_auto_yield_pct=40.0`, `operator_reviewable_yield_pct=100.0`, and
  `ship_gate_status=pass`; `validate_install --after-weekly` returned
  `ok=true`. The root-level packaged `EIDP-start.bat` also launched
  `scripts\launch.bat`, returned `_stcore/health=ok` and root HTTP `200` on
  Windows `127.0.0.1:8501`, and cleanup left no remaining `8501` listener.
  Browser read-only navigation through `output/playwright/v456-ui-smoke/`
  rendered `① 学校別タスク`, `② PDF確認・手入力`,
  `④ Excel プレビュー`, and `⑤ 設定（年度・OCR・API）`; summary JSON
  confirmed title `EIDP Operator Console`, build `f33ffc0`, and target FY
  `2026年度（令和8年度）`. Process-scoped R7 browser Excel also generated
  `output/playwright/v456-r7-excel-smoke/eidp-master.xlsx`, and
  `workbook-check.json` recorded sheets `採録状況`, `対象比率`, `学科別`,
  `在籍のみ抜粋` with dimensions `2419x10`, `10025x22`, `9748x83`, and
  `9748x19`; checked v456 `.env` paths were absent. The v456 bundle
  `logs/win-v456-stage6/stage6-evidence-20260516-034752.zip` verified on Mac
  with `ok=true`, `manifest_missing_patterns=[]`, and all required labels. The
  v456 disposable UI write/audit sandbox rejected `review_item#37`, flushed
  `exported=2 already_present=0 failed=0`, and saved
  `logs/win-v456-stage6/v456-ui-write-sandbox-result-final.json` with
  `ok=true`, `pending_outbox=0`, matching JSONL action IDs, and real runtime DB
  marker counts all `0`. A fresh v456 `scripts\diagnose.bat` preflight wrote
  `logs/win-v456-stage6/diagnostics-20260516-134458.txt` with
  `validate_core_rc=0`, `validate_after_setup_rc=0`, `stage6_recovery_rc=0`,
  `validate_after_weekly_rc=0`, `validate_after_weekly_ship_gate_rc=0`,
  `retroactive_ship_readiness_rc=0`, and current-year `ship_readiness_rc=1`.
  v456
  still lacks final operator real-cycle sign-off and does not prove the final R8
  strict target-PDF 60-70% gate. Windows cleanup removed 48 old loose home ZIP
  artifacts plus v453 staging/deploy artifacts. After v459 validation, the
  v456 deploy directory was pruned; after v460 validation, v454 staging/deploy
  artifacts were pruned and v460 current plus v459 fallback became the active
  owner/fallback Windows deploy directories before later v462/v463 side-by-side
  proof directories were added.
- Historical v454 fallback package/Windows setup lane: package snapshot
  `48a346bb626be749adb72d1aeb6a684903f22049`, SHA256
  `0bbed01d95fe320cee70b826c63e8c500303b8a62c42d325ef2481764660b2e3`.
  `scripts/run_non_windows_release_gates.py dist/eidp-windows-v454.zip
  --json --output logs/release-gate-v454.json` returned `ok=true`, with
  package/source freshness at `48a346b`, SHA sidecar match, full unit
  `1635 passed`, validator/distribution tests returning `164 passed`,
  validator mypy/Ruff passing, discovery-gold expected predictions matching
  `44/44`, and both package verifier modes passing. Windows evidence proves
  transfer/SHA, setup/import, SQLite integrity, URL-only bootstrap with six
  school-domain overrides, bounded R7 `scripts\weekly_run.bat` with
  `school_domain_override` included, `downloaded=2`,
  `target_pdf_auto_yield_pct=40.0`, independent
  `validate_install --after-setup --after-weekly` with `ok=true`,
  recovery action verification with `action_matches_expected=true`,
  evidence-bundle verification with `weekly_run_logs`, UI health,
  retained fallback UI write/audit sandbox proof through
  `output/playwright/v454-ui-write-sandbox/` and
  `logs/win-v454-stage6/v454-ui-write-sandbox-result-final.json`, and
  v454-current plus v453-fallback retention. v442 remains historical support for the fuller
  R7 parity workbook.
- Historical v437 Mac/non-Windows release-gate proof: v437, package snapshot
  `7553c7480a001a1ebec687dcb743c8bd9529d6d4`, SHA256
  `ed0d677fd2d36f7bd9f884185412180a6764beef9632543e5e36eb3c766ed33c`.
  `scripts/verify_windows_distribution.py dist/eidp-windows-v437.zip`
  returned `ok=true`, `git_dirty=false`, `wheel_count=78`, and
  `discovery_gold_set_entries=44`. `scripts/run_non_windows_release_gates.py
  dist/eidp-windows-v437.zip --json --output logs/release-gate-v437-full.json`
  returned `ok=true`, with `source_dirty=false`, `stale=false`,
  `unit_full` returning `1600 passed`, validator/distribution tests returning `164 passed`,
  validator/distribution mypy and Ruff passing, expected discovery-gold
  predictions matching `44/44`, and the demonstrated-pattern package verifier
  passing. The follow-up `logs/release-gate-v437-retroactive-matrix.json`
  matrix returned `ok=true` with `case_count=3` for FY2025, FY2024, and FY2023.
  The per-year outputs `logs/release-gate-v437-retroactive-fy2025-reference.json`,
  `logs/release-gate-v437-retroactive-fy2024-reference.json`, and
  `logs/release-gate-v437-retroactive-fy2023-reference.json` all returned
  `ok=true`, with fresh isolated exports under
  `_temp/non-windows-retroactive-fy2025-20260515-184145`,
  `_temp/non-windows-retroactive-fy2024-20260515-190026`, and
  `_temp/non-windows-retroactive-fy2023-20260515-190422`; all three produced
  the same four workbook row counts and zero business-value diffs against their
  stable references. v437 is not Windows-proven. v421 is explicitly superseded
  and must not be transferred because its package verifier rejected hard-coded
  v420 package/SHA fields in the packaged E2E template. v437 additionally
  verifies localhost launch, operator review lock, PDF annotation URI-safety,
  per-call Excel threshold, protected residual-cleanup, non-persistent
  `EIDP_TARGET_FISCAL_YEAR` settings, OCR provider method labeling,
  `Numeric(4,3)` confidence precision, and fiscal-year override
  collateral-demotion audit regressions. v437 also surfaces future/out-of-cap
  ingest fiscal-year annotations through `invalid_fiscal_year` stats/evidence,
  locks manual-entry `DepartmentYearly` revision reads before append, writes
  manual-entry `SchoolYearStatus` and `SupportRecipient` rows, aligns
  installed-wheel app-root/data-dir defaults, replays Stage 6 SQLite performance
  indexes, locks school URL crawl-evidence JSONL appends, and configures
  rotating structured JSONL logging for CLI, Streamlit, and the weekly runner.
  v437 also widens the CLI write-lock
  AST contract to cover every `cli_*.py` command module and attribute-form
  write helper calls.
- Post-v410 non-runtime hardening included in v415: Streamlit AppTest cold-start timeout
  budget was raised from `15s` to `30s` for UI smoke tests, with
  `uv run pytest tests/unit/test_review_school_year_tasks.py
  tests/unit/test_review_pdf_manual_entry.py -q` returning `100 passed`;
  optional Scrapling and OCR-runtime boundary tests now keep the local coverage
  line above the configured threshold; `[tool.coverage.report] fail_under = 80`
  is set in `pyproject.toml`; `uv run pytest --cov=src/eidp --cov-report=term`
  returned `1530 passed`, `TOTAL 14186 2837 80%`, and `Total coverage: 80.00%`;
  local runtime/tool artifacts are ignored narrowly via `.gitignore`.
- Historical Windows transfer/setup/UI-health proof: v408, commit
  `f0c2715833b54e60fea85259e16ad0a1d9e6c106`, SHA256
  `61fe233e41c08b8684560778b25c36f12ad0848135e8930ef07d8fa265fbbbe2`.
  v408 was Mac core-verifier-clean, SHA-checked on Windows, extracted to
  `C:\Users\cyo20\EIDP-v408-f0c27158`, setup-validated with
  `school_count=2418`, `school_fiscal_year_status_count=2418`,
  `sqlite_integrity_check=ok`, `wheel_count=78`, and required runtime tables,
  served Streamlit through a Mac tunnel `18508 -> 8508`, and its packaged
  `stage6_recovery_check.py` parsed the scheduled task XML successfully with
  `action_matches_expected=true` for the v408 weekly runner. v408 is not yet
  real-operator-cycle proven, but it has R7 CLI Excel export/diff parity with
  v407, R7 browser Excel download parity with the v408 CLI export, a disposable
  copied-DB UI write/audit sandbox proof, and a verifier-accepted non-Excel
  diagnostic evidence bundle.
- Supporting Windows evidence lane: v407, commit
  `0974b60fb3d404678828ddfa348c74f4dd740c79`, SHA256
  `af48ed37d65695c044b520da78aad5307ed89b4b4a38cf27c6dc7e2737f50940`.
- Historical packaged source-code evidence base through v437: `7553c748`, incorporating the
  `15c88348` post-v408 source-only coverage recovery plus Stage 6 safety fixes for recovery check,
  evidence bundle Excel exclusion, residual cleanup symlink/junction safety,
  clarified ship-readiness criteria semantics, audit outbox custom-archive
  dedup, stricter romanized renewal-form hint handling across strong and weak
  target-form hint paths, operator-facing PDF discovery reason labels in the
  school task-board detail panel, and typed fiscal-year
  override / PDF ingest / PDF OCR / Excel exporter / Excel import stats /
  manual audit / operator UI / bootstrap URL crawl / append-only audit-helper
  paths, including `invalid_fiscal_year` stats/evidence for out-of-cap ingest
  fiscal-year annotations, manual-entry row-lock coverage for
  `DepartmentYearly` append-only revision writes, locked school URL crawl
  evidence JSONL appends, target-fiscal-year non-persistence in operator
  settings, provider-specific OCR extraction methods, and `Numeric(4,3)`
  confidence precision, plus unit-test isolation for Streamlit AppTest's fake `__main__`
  module before multiprocessing spawn tests, restored source-wide `mypy src`
  coverage for all 83 source files, restored the documented local line
  coverage target (`uv run pytest --cov=src/eidp --cov-report=term-missing`
  -> `1520 passed`, `TOTAL 14186 2866 80%`), and a non-Windows
  release-gate guard that
  rejects ZIPs whose packaged `BUILD_INFO.json` commit differs from the current
  source HEAD, or whose current source tree has uncommitted tracked changes,
  unless `--allow-stale-package` is explicitly used for historical checks.
  The Windows package and install validators also reject packaged
  `BUILD_INFO.json` values where `git_dirty` is not `false`, and
  `scripts/build_windows_zip.py` now refuses to produce a Windows ZIP from
  uncommitted tracked source unless `--allow-dirty` is explicitly used for a
  diagnostic build. Discovery RCA triage now prioritizes explicit
  `target_fiscal_year_not_detected` target-form evidence over older-year target
  evidence for the same school so operator review queues do not bury
  yearless current candidates behind publication-lag labels. Gold-set seeding
  now preserves semantic directory trailing slashes for disclosure entrypoints,
  PDF discovery now attaches same-section support-system headings to year-only
  target-form links before candidate prioritization, audit-outbox archive
  dedup ignores symlinks, and the extraction-confidence default thresholds are
  exposed through per-call Excel export helpers so operator env changes do not
  desync ingest and export. The latest source lane also binds packaged
  Streamlit launchers to `127.0.0.1`, requires school-code, URL-candidate, and
  proposal-review write UIs to acquire the app lock before committing writes,
  filters PDF annotation URIs through the same absolute `http(s)` safety
  boundary used by text-cell URL extraction, and refuses to move
  `eidp.sqlite3`, `manual-actions.jsonl`, or `master.xlsx` during Stage 6
  residual cleanup. The packaged ZIP verifier now
  requires default Stage 6 tunnel guidance for `18501 -> 8501` in both the
  operator runbook and E2E evidence template. The non-Windows release gate also
  keeps `--allow-stale-package` dirty-safe: it can bypass a historical package
  commit mismatch, but still rejects uncommitted tracked source. The Windows
  install validator also rejects `last_run.json status=lock_busy` as weekly
  ship-gate evidence even if the payload claims `ship_gate_status=pass`. For
  bootstrap release-gate checks, progress-count mismatches against SQLite are
  fatal under `--require-ship-gate` while remaining warnings for structure-only
  validation. The latest source lane also scopes MEXT reconciliation and
  identity verification by configurable `school_type` while preserving
  `専門学校` as the v1 default.
- The v407 supporting lane contains all v407-era fixes through `0974b60f`, but
  the latest scheduled-task XML decode fix and current setup/UI validation are
  in v408. v401 remains a
  stale package: the latest recorded read-only rerun of the non-Windows package
  gate against v401 with the current verifier failed before downstream gates
  because `package_source_check` detected that packaged commit
  `2d9c9f690c6f955330ea49276ef1a87157ceb6cd` did not match the then-current
  source HEAD.
- Do not mark the goal complete until an active setup lane completes real
  operator-PC click-through evidence and the rolling FY yield gate.

## Current Local Verification

Latest v460 Mac/non-Windows release-gate, Windows transfer/setup/recovery,
companion-docs staging, disk-retention, and v459 bounded browser/evidence
support are summarized in `docs/reports/current-release-status.md`. The retained
detailed local checks below include historical source-code evidence base
`4a16363d` and later refreshes; they are not a substitute for the current v460
owner/operator real-cycle gate:

- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v437.zip --latest-alias`
  -> wrote `dist/eidp-windows-v437.zip`, refreshed `dist/eidp-windows.zip`,
  and wrote `dist/eidp-windows-v437.zip.sha256`.
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v437.zip --json --output logs/release-gate-v437-full.json`
  -> exited `0`: `unit_full` returned `1600 passed`, validator/distribution
  tests reported `164 passed`, validator/distribution mypy and Ruff passed,
  discovery-gold expected predictions were `44/44`, and package verification
  with `--require-demonstrated-discovery-patterns` passed.
- `uv run python scripts/run_retroactive_excel_matrix.py dist/eidp-windows-v437.zip --skip-full-unit --case 2025=_temp/v408-r7-cli-export.xlsx --case 2024=_temp/non-windows-retroactive-fy2024-20260515-125437/output/retroactive-fy2024-export.xlsx --case 2023=_temp/non-windows-retroactive-fy2023-20260515-125526/output/retroactive-fy2023-export.xlsx --output logs/release-gate-v437-retroactive-matrix.json`
  -> `ok=true`, `case_count=3`; per-year outputs
  `logs/release-gate-v437-retroactive-fy2025-reference.json`,
  `logs/release-gate-v437-retroactive-fy2024-reference.json`, and
  `logs/release-gate-v437-retroactive-fy2023-reference.json` all returned
  `ok=true`, validator/distribution tests reported `164 passed`, package
  verifiers passed, isolated exports wrote `採録状況=2418`,
  `対象比率=10022`, `学科別=9719`, and `在籍のみ抜粋=9719`, and
  `retroactive_excel_diff_reference` returned zero missing/extra rows and zero
  differing fields for every case.
- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v419.zip --latest-alias`
  -> wrote `dist/eidp-windows-v419.zip`, refreshed `dist/eidp-windows.zip`,
  and wrote `dist/eidp-windows-v419.zip.sha256`.
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v419.zip --retroactive-excel-reference _temp/v408-r7-cli-export.xlsx --retroactive-fiscal-year 2025 --json --output logs/release-gate-v419-retroactive.json`
  -> `ok=true`, SHA256
  `f1ce206e169a9f5ab2f1572c0528c47f0c59131af55750ef935aca906093c8e9`,
  packaged/source commit `45b9dffc3c02a844f792f3f0a3a31e98d46d1931`,
  `package_source_check.stale=false`, `tests/unit -q` reported `1545 passed`,
  validator/distribution tests reported `164 passed`, validator/distribution
  mypy and Ruff passed, discovery-gold expected predictions were `44/44`,
  package verification with `--require-demonstrated-discovery-patterns` passed,
  and `retroactive_excel_diff_reference` returned zero missing/extra rows and
  zero differing fields against `_temp/v408-r7-cli-export.xlsx`.
- `.github/workflows/ci.yml` now runs the Python CI gate with locked uv
  dependencies, scoped Ruff checks for `src` and release/Stage 6 scripts/tests,
  `uv run mypy src`, and `uv run pytest --cov=src/eidp --cov-report=term
  --cov-fail-under=80`. The local equivalent returned `1555 passed` and
  `Total coverage: 80.03%`.
- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v418.zip --latest-alias`
  -> wrote `dist/eidp-windows-v418.zip`, refreshed `dist/eidp-windows.zip`,
  and wrote `dist/eidp-windows-v418.zip.sha256`.
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v418.zip --retroactive-excel-reference _temp/v408-r7-cli-export.xlsx --retroactive-fiscal-year 2025 --json --output logs/release-gate-v418-retroactive.json`
  -> `ok=true`, SHA256
  `52529db8739f7fb431c4a74cbe88522381471604a7313b3debd0e273f066d71d`,
  packaged/source commit `5bddd499af26c0bbfe3c6d1f55d26cd61522fb8b`,
  `package_source_check.stale=false`, `tests/unit -q` reported `1539 passed`,
  validator/distribution tests reported `164 passed`, validator/distribution
  mypy and Ruff passed, discovery-gold expected predictions were `44/44`,
  package verification with `--require-demonstrated-discovery-patterns` passed,
  and `retroactive_excel_diff_reference` returned zero missing/extra rows and
  zero differing fields against `_temp/v408-r7-cli-export.xlsx`.
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v418.zip --skip-full-unit --allow-docs-only-stale-package --json --output logs/release-gate-v418-docs-only-stale-after-status-refresh.json`
  -> `ok=true`; SHA256 sidecar matched; `package_source_check` reported
  `stale=true`, `docs_only_stale=true`, `source_dirty=false`,
  `allowed_stale_reason=docs_only`, and changed paths limited to release/status
  documentation under `docs/`; validator/distribution tests reported
  `164 passed`, validator/distribution mypy and Ruff passed, discovery-gold
  expected predictions were `44/44`, and package verification with
  `--require-demonstrated-discovery-patterns` passed. This is a current-source
  evidence replay convenience, not a Windows transfer/setup proof.
- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v411.zip --latest-alias`
  -> wrote `dist/eidp-windows-v411.zip`, refreshed `dist/eidp-windows.zip`,
  and wrote `dist/eidp-windows-v411.zip.sha256`.
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v411.zip --retroactive-excel-reference _temp/v408-r7-cli-export.xlsx --retroactive-fiscal-year 2025 --json --output logs/release-gate-v411-retroactive.json`
  -> `ok=true`, SHA256
  `31f2074506eff699d2d1c9349e03f2b0e09b2bf1d9044f3d374211dc22b15200`,
  packaged/source commit `d673b020e2d702260aaeff78db4d59edf0a38aa7`,
  `package_source_check.stale=false`, `tests/unit -q` reported `1530 passed`,
  validator/distribution tests reported `161 passed`, validator/distribution
  mypy and Ruff passed, discovery-gold expected predictions were `44/44`,
  package verification with `--require-demonstrated-discovery-patterns` passed,
  and `retroactive_excel_diff_reference` returned zero missing/extra rows and
  zero differing fields against `_temp/v408-r7-cli-export.xlsx`.
- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v410.zip --latest-alias`
  -> wrote `dist/eidp-windows-v410.zip`, refreshed `dist/eidp-windows.zip`,
  and wrote `dist/eidp-windows-v410.zip.sha256`.
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v410.zip --retroactive-excel-reference _temp/v408-r7-cli-export.xlsx --retroactive-fiscal-year 2025 --json --output logs/release-gate-v410-retroactive.json`
  -> `ok=true`, SHA256
  `cf7c444c38e023fc534986e21eddb0502cead9721124dffd78406d357f544714`,
  packaged/source commit `98d9f792860b40e537ec61a8b470859be7bb70c0`,
  `package_source_check.stale=false`, `tests/unit -q` reported `1520 passed`,
  validator/distribution tests reported `161 passed`, validator/distribution
  mypy and Ruff passed, discovery-gold expected predictions were `44/44`,
  package verification with `--require-demonstrated-discovery-patterns` passed,
  and `retroactive_excel_diff_reference` returned zero missing/extra rows and
  zero differing fields against `_temp/v408-r7-cli-export.xlsx`.
- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v409.zip --latest-alias`
  -> wrote `dist/eidp-windows-v409.zip`, refreshed `dist/eidp-windows.zip`,
  and wrote `dist/eidp-windows-v409.zip.sha256`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v409.zip --json`
  -> `ok=true`, SHA256
  `3621947fc280412c30d056d77e3bd59af1410b0b07c55da21749ec75327e425e`,
  packaged commit `e0b3e3c26cfe6987187a035eaded6fc118e3bb0d`,
  `git_dirty=false`, `wheel_count=78`, `project_wheel_count=1`,
  `prefecture_seed_rows=47`, and `discovery_gold_set_entries=44`.
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v409.zip --json --output logs/release-gate-v409.json`
  -> `ok=true`, `package_source_check.stale=false`, `tests/unit -q`
  reported `1515 passed`, validator/distribution tests reported `161 passed`,
  validator/distribution mypy and Ruff passed, discovery-gold expected
  predictions were `44/44`, and package verification with
  `--require-demonstrated-discovery-patterns` passed.
- `uv run pytest tests/unit/test_stage6_recovery_check.py -q`
  -> `7 passed`.
- `uv run pytest tests/unit/test_stage6_recovery_check.py tests/unit/test_stage6_residual_cleanup.py tests/unit/test_stage6_evidence_bundle.py tests/unit/test_windows_packaging_spike.py tests/unit/test_windows_distribution_verifier.py -q`
  -> `205 passed`.
- `uv run ruff check scripts/stage6_recovery_check.py tests/unit/test_stage6_recovery_check.py`
  -> `All checks passed`.
- `uv run mypy scripts/stage6_recovery_check.py`
  -> `Success: no issues found in 1 source file`.
- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v408.zip --latest-alias`
  -> wrote `dist/eidp-windows-v408.zip`, refreshed `dist/eidp-windows.zip`,
  and wrote `dist/eidp-windows-v408.zip.sha256`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v408.zip --json`
  -> `ok=true`, SHA256
  `61fe233e41c08b8684560778b25c36f12ad0848135e8930ef07d8fa265fbbbe2`,
  `wheel_count=78`, `project_wheel_count=1`, `prefecture_seed_rows=47`,
  `discovery_gold_set_entries=44`, and packaged `BUILD_INFO.json` commit
  `f0c2715833b54e60fea85259e16ad0a1d9e6c106`, `git_dirty=false`.
- Windows v408 transfer/extract and packaged recovery check:
  SHA256 matched the sidecar, `C:\Users\cyo20\EIDP-v408-f0c27158` expanded
  cleanly, and the packaged recovery checker returned `task.exists=true`,
  `task.error=null`, and `action_matches_expected=true` for
  `C:\Users\cyo20\EIDP-v407-0974b60f\scripts\weekly_run.bat` before v408
  setup; overall
  `ok=false` remained solely because known v384 residual smoke artifacts still
  exist.
- Windows v408 setup/validate/recovery/UI-health:
  `EIDP-setup.bat` exited `0` and logged `OK install:
  C:\Users\cyo20\EIDP-v408-f0c27158`; `validate_windows_install.py
  C:\Users\cyo20\EIDP-v408-f0c27158 --after-setup --json` returned `ok=true`
  with `school_count=2418`, `school_fiscal_year_status_count=2418`,
  `sqlite_integrity_check=ok`, `sqlite_table_count=15`, and `wheel_count=78`;
  the scheduled task now points to
  `C:\Users\cyo20\EIDP-v408-f0c27158\scripts\weekly_run.bat`; a v408 packaged
  recovery check against that path returned `task.error=null` and
  `action_matches_expected=true`; Windows-local `/_stcore/health` on port
  `8508` and Mac-tunnel `/_stcore/health` on `18508 -> 8508` both returned
  `ok`, and the Streamlit root HTML shell was fetched.
- Windows v408 R7 retroactive CLI Excel proof:
  with process-local `EIDP_TARGET_FISCAL_YEAR=2025`, `eidp export-excel`
  wrote `data\output\v408-r7-retroactive-export.xlsx` with
  `採録状況=2418`, `対象比率=10022`, `学科別=9719`, and
  `在籍のみ抜粋=9719`; `diff-excel --business-values --original` against the
  proven v407 R7 export returned `missing_sheets=0`, `extra_sheets=0`,
  `missing_rows=0`, `extra_rows=0`, and `differing_fields=0`; `openpyxl`
  opened the v408 workbook at `3,673,084` bytes with dimensions `2419x10`,
  `10023x22`, `9721x83`, and `9721x19`. The packaged default
  `diff-excel --business-values` reference path still points to absent
  `sample\◆2025専門学校無償化情報公開まとめ.xlsx`, so explicit `--original` is
  required for now.
- Windows v408 R7 retroactive browser Excel proof:
  with process-local `EIDP_TARGET_FISCAL_YEAR=2025`, Streamlit served on
  Windows `127.0.0.1:8509`; Mac tunnel `127.0.0.1:18509 -> 127.0.0.1:8509`
  returned `/_stcore/health=ok`; Playwright opened `Excel プレビュー`, observed
  `対象年度: 2025年度（令和7年度）`, `抽出済み学校 2031`, and
  `Excel対象行 7150`, clicked `プレビュー workbook を生成`, and observed sheet
  counts `採録状況=2418`, `対象比率=10022`, `学科別=9719`, and
  `在籍のみ抜粋=9719`. The downloaded `_temp/v408-r7-browser-eidp_master.xlsx`
  suggested `eidp_master.xlsx`; `openpyxl` opened it at `3,673,083` bytes with
  dimensions `2419x10`, `10023x22`, `9721x83`, and `9721x19`. Comparing it to
  `_temp/v408-r7-cli-export.xlsx` with `diff-excel --business-values` returned
  `missing_sheets=0`, `extra_sheets=0`, `missing_rows=0`, `extra_rows=0`, and
  `differing_fields=0`. The Streamlit process and tunnel were stopped after the
  proof.
- Windows v408 disposable UI write/audit sandbox proof:
  with process-local `EIDP_TARGET_FISCAL_YEAR=2025`, copied DB sandbox
  `C:\Users\cyo20\EIDP-v408-f0c27158-ui-sandbox-20260515-02`, Streamlit served on
  Windows `127.0.0.1:8510`, and Mac tunnel `127.0.0.1:18510 ->
  127.0.0.1:8510`, Playwright saved one `PDF確認・手入力` manual entry and one
  `年度判定・修正` fiscal-year override. `監査ログ` showed `JSONL outbox 未送信=7`;
  `Outbox を flush` returned `exported=7 already_present=0 failed=0`. Direct DB
  verification wrote
  `C:\Users\cyo20\EIDP-v408-f0c27158-ui-sandbox-20260515-02\logs\diagnostics-v408-ui-sandbox-proof-20260515-034848.json`
  and confirmed all seven audit rows had `jsonl_exported_at_present=true`, the
  manual FY2025 `DepartmentYearly` row was verified, and the fiscal-year override
  cloned FY2025 current rows while demoting FY2024 rows. The Streamlit process
  and tunnel were stopped after the proof.
- Windows v408 non-Excel diagnostic evidence bundle:
  process-local FY2025 dry-run weekly wrote `data\output\last_run.json` with
  `status=success`, `dry_run=true`, `selection_mode=target_missing`,
  `new_document_ids=[]`, `ship_gate_status=not_measured`, and null yield
  percentages because the denominator was `0`; the log was
  `logs\run-v408-retroactive-dryrun-20260515-040053.log`. Packaged recovery
  wrote `logs\stage6-recovery-20260515-040010.json` with
  `action_matches_expected=true`; residual cleanup was dry-run only and wrote
  `logs\stage6-residual-cleanup-20260515-040034.json` with `existing_count=5`,
  `moved_count=0`, and `errors=[]`. Packaged collection produced
  `logs\stage6-evidence-20260514-190257.zip`, and packaged verification wrote
  `logs\stage6-evidence-verify-20260515-040322.json` with `ok=true`,
  `entry_count=8`, `forbidden_entries=[]`, `unsafe_entries=[]`,
  `missing_required_labels=[]`, and labels `build_info`, `diagnostics`,
  `last_run`, `stage6_recovery`, `stage6_residual_cleanup`, and
  `weekly_run_logs`. The manifest still lists missing `bootstrap_logs`,
  `bootstrap_progress`, and `discovery_rca`, so this remains diagnostic evidence.

- `uv run mypy src`
  -> `Success: no issues found in 83 source files`.
- `uv run ruff check src`
  -> `All checks passed`.
- `uv run pytest tests/unit -q`
  -> `1459 passed, 5 warnings in 34.55s`.
- `uv run pytest tests/unit/test_review_school_year_tasks.py::test_discovery_evidence_table_rows_show_candidate_reason_and_source tests/unit/test_review_school_year_tasks.py::test_discovery_rejection_reason_summary_labels_top_reasons tests/unit/test_review_school_year_tasks.py::test_bootstrap_progress_detail_lines_include_rejection_reason_counts -q`
  -> first run reproduced the raw-code detail-table bug with `1 failed`; after
  the fix, the focused reason-label set returned `3 passed in 0.38s`.
- `uv run pytest tests/unit/test_review_school_year_tasks.py -q`
  -> `59 passed in 1.16s`.
- `uv run ruff check src/eidp/review/_pages/school_year_tasks.py tests/unit/test_review_school_year_tasks.py && uv run mypy src/eidp/review/_pages/school_year_tasks.py`
  -> `All checks passed`; `Success: no issues found in 1 source file`.
- `uv run pytest tests/unit/test_pdf_discovery.py::test_pre_download_does_not_treat_romanized_renewal_form_alone_as_target -q`
  -> first run reproduced the weak-hint bug with `1 failed`; after the fix,
  the focused nearby renewal/priority set returned `4 passed in 1.37s`.
- `uv run pytest tests/unit/test_pdf_discovery.py -q`
  -> `164 passed, 5 warnings in 11.00s`.
- `uv run ruff check src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py && uv run mypy src/eidp/scraper/pdf_discovery.py`
  -> `All checks passed`; `Success: no issues found in 1 source file`.
- `uv run pytest tests/unit/test_discovery_evidence_summary.py -q`
  -> `14 passed in 0.36s`.
- `uv run pytest tests/unit/test_discovery_evidence_summary.py tests/unit/test_school_fiscal_year_status.py::test_rebuild_marks_publication_lag_evidence_as_review_state tests/unit/test_school_fiscal_year_status.py::test_rebuild_marks_target_form_without_year_evidence_as_review_state -q`
  -> `16 passed in 0.43s`.
- `uv run pytest tests/unit/test_cli_discovery_rca_packet.py -q`
  -> `24 passed in 0.60s`.
- `uv run pytest tests/unit/test_pdf_discovery.py tests/unit/test_cli_pdf_discovery_strict.py tests/unit/test_discovery_gold_set_seed.py tests/unit/test_url_normalization.py -q`
  -> `183 passed, 5 warnings in 12.42s`.
- `uv run pytest tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_summary.py tests/unit/test_cli_discovery_gold_set.py tests/unit/test_cli_eval_discovery_gold.py tests/unit/test_discovery_gold_set_eval.py tests/unit/test_discovery_gold_set_seed.py -q`
  -> `49 passed in 1.84s`.
- `uv run ruff check src/eidp/scraper/pdf_discovery.py src/eidp/scraper/discovery_gold_set.py tests/unit/test_pdf_discovery.py tests/unit/test_discovery_gold_set_seed.py tests/unit/test_url_normalization.py`
  -> `All checks passed`.
- `uv run mypy src/eidp/scraper/pdf_discovery.py src/eidp/scraper/discovery_gold_set.py`
  -> `Success: no issues found in 2 source files`.
- `uv run ruff check src/eidp/scraper/discovery_evidence_summary.py tests/unit/test_discovery_evidence_summary.py`
  -> `All checks passed`.
- `uv run mypy src/eidp/scraper/discovery_evidence_summary.py`
  -> `Success: no issues found in 1 source file`.
- Isolated live strict-discovery sample using temporary app root
  `_temp/live-discovery-ae835a1c-20260514-163155`:
  `uv run eidp db-bootstrap --sqlite`; `uv run eidp seed-discovery-gold-sites --gold-set-dir data/discovery-gold-set --apply`;
  `uv run eidp discover-pdfs --storage-dir "$run_dir/pdfs" --batch-size 10 --rate-limit 0.2 --request-timeout 12 --discovery-method discovery_gold_set --school-id 318 --school-id 1361 --school-id 758 --school-id 3205 --school-id 18 --school-id 74 --school-id 554 --school-id 757 --school-id 1532 --school-id 1533 --evidence-log "$run_dir/output/live-discovery-rejections.jsonl"`
  -> `crawled=10`, `found=10`, `downloaded=0`, `failed=1`, `skipped=185`,
  `rejection_reason_fiscal_year_mismatch=28`, and
  `rejection_reason_target_fiscal_year_not_detected=11`.
  Follow-up scoped summary after the RCA triage fix reported
  `publication_lag_or_old_target_pdf=6`, `target_form_without_year_evidence=3`,
  `non_target_candidates_only=1`, `no_evidence=34` across the 44 seeded
  gold-set sites; rebuild + ship-readiness on the same isolated DB reported
  `operator_reviewable_schools=9/44`, `operator_reviewable_rate=0.2045`,
  `strict_target_pdf_rate=0.0`, `excel_ready_schools=0`, and
  `ok_operator_review=false`.
- Isolated central-animal follow-up after the entrypoint/context fix using
  temporary app root `_temp/live-discovery-chuo-target-context-a17702f8-20260514-170031`:
  `uv run eidp db-bootstrap --sqlite`; `uv run eidp seed-discovery-gold-sites --gold-set-dir data/discovery-gold-set --apply`;
  `uv run eidp discover-pdfs --storage-dir "$run_dir/pdfs" --batch-size 1 --rate-limit 0.2 --request-timeout 12 --discovery-method discovery_gold_set --school-id 3205 --evidence-log "$run_dir/output/discovery.jsonl"`
  -> `crawled=1`, `found=1`, `downloaded=0`, `failed=0`,
  `rejection_reason_fiscal_year_mismatch=1`, and
  `rejection_reason_classified_non_target=10`. The first evidence row is
  `confirmation_2.pdf` with anchor text
  `2025年度 高等教育の修学支援新制度 申請書様式第2号`, score `7.5`, reason
  `fiscal_year_mismatch:2025`, and `pdf_type=target`; scoped summary reports
  `publication_lag_or_old_target_pdf=1` and `no_evidence=43`.
- `uv run ruff check scripts/build_windows_zip.py tests/unit/test_windows_packaging_spike.py`
  -> `All checks passed`.
- `uv run mypy scripts/build_windows_zip.py`
  -> `Success: no issues found in 1 source file`.
- `uv run pytest tests/unit/test_windows_packaging_spike.py -q`
  -> `78 passed in 0.55s`.
- `uv run pytest tests/unit/test_non_windows_release_gates.py tests/unit/test_windows_distribution_verifier.py tests/unit/test_windows_install_validator.py -q`
  -> `165 passed in 9.35s`.
- `uv run ruff check scripts/run_non_windows_release_gates.py tests/unit/test_non_windows_release_gates.py`
  -> `All checks passed`.
- `uv run mypy scripts/run_non_windows_release_gates.py`
  -> `Success: no issues found in 1 source file`.
- `uv run pytest tests/unit/test_non_windows_release_gates.py -q`
  -> `15 passed in 0.06s`.
- `uv run ruff check scripts/verify_windows_distribution.py scripts/validate_windows_install.py tests/unit/test_windows_distribution_verifier.py tests/unit/test_windows_install_validator.py`
  -> `All checks passed`.
- `uv run mypy scripts/verify_windows_distribution.py scripts/validate_windows_install.py`
  -> `Success: no issues found in 2 source files`.
- `uv run pytest tests/unit/test_windows_distribution_verifier.py tests/unit/test_windows_install_validator.py -q`
  -> `150 passed in 6.83s`.
- `uv run pytest tests/unit/test_windows_distribution_verifier.py::test_verify_core_zip_requires_current_operator_runbook_guidance tests/unit/test_windows_distribution_verifier.py::test_verify_core_zip_requires_retroactive_fy_e2e_template_fields tests/unit/test_windows_distribution_verifier.py::test_verify_core_zip_requires_stage6_recovery_e2e_template_fields tests/unit/test_windows_distribution_verifier.py::test_verify_core_zip_requires_default_stage6_tunnel_guidance -q`
  -> `4 passed`.
- `uv run ruff check scripts/verify_windows_distribution.py tests/unit/test_windows_distribution_verifier.py`
  -> `All checks passed`.
- `uv run mypy scripts/verify_windows_distribution.py`
  -> `Success: no issues found in 1 source file`.
- `uv run ruff check src/eidp/extraction_confidence.py tests/unit/test_extraction_confidence.py tests/unit/test_ingest_confidence_gating.py tests/unit/test_ocr_tesseract_wrapper.py tests/unit/test_review_confidence_panels.py`
  -> `All checks passed`.
- `uv run mypy src/eidp/extraction_confidence.py src/eidp/pipeline/ingest.py src/eidp/review/confidence_panels.py src/eidp/pdf/ocr.py`
  -> `Success: no issues found in 4 source files`.
- `uv run pytest tests/unit/test_extraction_confidence.py tests/unit/test_ingest_confidence_gating.py tests/unit/test_ocr_tesseract_wrapper.py tests/unit/test_review_confidence_panels.py -q`
  -> `127 passed in 5.79s`.
- `uv run ruff check src/eidp/ocr/tesseract.py tests/unit/test_ocr_tesseract_wrapper.py`
  -> `All checks passed`.
- `uv run mypy src/eidp/ocr/tesseract.py src/eidp/pdf/ocr.py`
  -> `Success: no issues found in 2 source files`.
- `uv run pytest tests/unit/test_ocr_tesseract_wrapper.py tests/unit/test_pdf_ocr_tesseract_provider.py -q`
  -> `21 passed in 0.69s`.
- `uv run ruff check src/eidp/pdf/eval_harness.py src/eidp/db/session.py src/eidp/scraper/discovery_rca_packet.py src/eidp/scraper/firecrawl_discovery.py src/eidp/matcher/reconciler.py tests/unit/test_eval_harness.py tests/unit/test_cli_discovery_rca_packet.py tests/unit/test_cli_write_lock_contract.py`
  -> `All checks passed`.
- `uv run mypy src/eidp/pdf/eval_harness.py src/eidp/db/session.py src/eidp/scraper/discovery_rca_packet.py src/eidp/scraper/firecrawl_discovery.py src/eidp/matcher/reconciler.py`
  -> `Success: no issues found in 5 source files`.
- `uv run pytest tests/unit/test_eval_harness.py tests/unit/test_cli_discovery_rca_packet.py tests/unit/test_cli_write_lock_contract.py -q`
  -> `54 passed in 1.94s`.
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v401.zip --skip-full-unit --json --output _temp/v401-non-windows-release-gates-stale-current-0e7e66d.json`
  -> `ok=false`; SHA256 sidecar matched
  `ff54f3a4c6a498ab9af89890e1ee614b31e57a87066277f1323f8f37d6f1bcf5`;
  `package_source_check` failed before downstream gates with packaged commit
  `2d9c9f690c6f955330ea49276ef1a87157ceb6cd`, source commit
  `0e7e66d25a9e77193962c4385e06e9744ab9f09f`, `source_dirty=false`,
  `stale=true`, and `results=[]`.
  This current rerun confirms v401 is not a current package; it is not evidence
  that the latest code-affecting source base `4a16363d` has been packaged.
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v401.zip --skip-full-unit --allow-stale-package --json --output _temp/v401-non-windows-release-gates-allow-stale-current-bb621daa.json`
  -> `ok=false`; SHA256 sidecar matched; `package_source_check` was allowed
  through with `stale=true`, but package verification then failed because v401
  lacks the current verifier's Stage 6 recovery, evidence Excel opt-in,
  residual cleanup symlink/junction safety, operator-coverage ship gate,
  audit-outbox archive matching, and default `18501 -> 8501` tunnel guidance
  tokens.
- `uv run pytest tests/unit/test_non_windows_release_gates.py::test_verify_package_source_commit_allow_stale_still_rejects_dirty_source tests/unit/test_non_windows_release_gates.py::test_verify_package_source_commit_can_allow_stale_zip_for_history tests/unit/test_non_windows_release_gates.py::test_verify_package_source_commit_rejects_dirty_tracked_source tests/unit/test_non_windows_release_gates.py::test_main_allows_stale_package_when_explicitly_requested -q`
  -> first run reproduced the bug with `1 failed, 3 passed`; after the fix,
  the same focused set returned `4 passed in 0.12s`.
- `uv run pytest tests/unit/test_non_windows_release_gates.py -q`
  -> `16 passed in 0.07s`.
- `uv run ruff check scripts/run_non_windows_release_gates.py tests/unit/test_non_windows_release_gates.py`
  -> `All checks passed`.
- `uv run mypy scripts/run_non_windows_release_gates.py`
  -> `Success: no issues found in 1 source file`.
- `uv run pytest tests/unit/test_windows_install_validator.py::test_validate_after_weekly_release_gate_rejects_lock_busy_even_if_payload_says_pass -q`
  -> first run reproduced the bug with `1 failed`; after the fix, the focused
  weekly ship-gate set returned `4 passed in 0.13s`.
- `uv run pytest tests/unit/test_windows_install_validator.py -q`
  -> `46 passed in 1.43s`.
- `uv run ruff check scripts/validate_windows_install.py tests/unit/test_windows_install_validator.py`
  -> `All checks passed`.
- `uv run mypy scripts/validate_windows_install.py`
  -> `Success: no issues found in 1 source file`.
- `uv run pytest tests/unit/test_windows_install_validator.py::test_validate_after_bootstrap_release_gate_rejects_progress_count_mismatch_even_when_sqlite_passes -q`
  -> first run reproduced the bug with `1 failed`; after the fix, the focused
  bootstrap ship-gate set returned `4 passed in 0.09s`.
- `uv run pytest tests/unit/test_windows_install_validator.py -q`
  -> `47 passed in 0.74s`.
- `uv run ruff check scripts/validate_windows_install.py tests/unit/test_windows_install_validator.py`
  -> `All checks passed`.
- `uv run mypy scripts/validate_windows_install.py`
  -> `Success: no issues found in 1 source file`.
- `uv run mypy src/eidp/db/audit.py src/eidp/db/audit_outbox.py src/eidp/db/current_helpers.py src/eidp/db/locking.py src/eidp/pipeline/manual_entry.py src/eidp/pipeline/ingest.py src/eidp/pipeline/ingest_evidence.py src/eidp/review/_pages/audit_log.py src/eidp/review/_pages/pdf_manual_entry.py`
  -> `Success: no issues found in 9 source files`.
- `uv run ruff check src/eidp/db/audit.py src/eidp/db/audit_outbox.py src/eidp/db/current_helpers.py src/eidp/db/locking.py src/eidp/pipeline/manual_entry.py src/eidp/pipeline/ingest.py src/eidp/pipeline/ingest_evidence.py src/eidp/review/_pages/audit_log.py src/eidp/review/_pages/pdf_manual_entry.py tests/unit/conftest.py tests/unit/test_manual_entry_contract.py tests/unit/test_review_pdf_manual_entry.py tests/unit/test_review_pdf_manual_entry_confidence.py tests/unit/test_review_audit_log.py tests/unit/test_review_audit_log_dashboard.py tests/unit/test_audit_outbox.py tests/unit/test_locking.py tests/unit/test_ingest_confidence_gating.py tests/unit/test_normal_ingest_appendonly.py tests/unit/test_ingest_evidence.py tests/unit/test_cli_ingest.py`
  -> `All checks passed`.
- `uv run pytest tests/unit/test_manual_entry_contract.py tests/unit/test_review_pdf_manual_entry.py tests/unit/test_review_pdf_manual_entry_confidence.py tests/unit/test_review_audit_log.py tests/unit/test_review_audit_log_dashboard.py tests/unit/test_audit_outbox.py tests/unit/test_locking.py tests/unit/test_ingest_confidence_gating.py tests/unit/test_normal_ingest_appendonly.py tests/unit/test_ingest_evidence.py tests/unit/test_cli_ingest.py -q`
  -> `143 passed, 5 warnings in 11.15s`.
- `uv run ruff check tests/unit/conftest.py tests/unit/test_locking.py`
  -> `All checks passed`.
- `uv run pytest tests/unit/test_review_pdf_manual_entry.py tests/unit/test_locking.py -q`
  -> `48 passed, 5 warnings in 7.77s`; confirms the PDF manual-entry AppTest
  no longer leaks a fake `__main__` module into subsequent multiprocessing
  spawn-based lock tests.
- `uv run mypy src/eidp/scraper/url_discovery.py src/eidp/scraper/school_url_pipeline.py src/eidp/scraper/school_url_persistence.py src/eidp/scraper/pdf_discovery.py scripts/bootstrap_pdf_pipeline.py scripts/run_weekly_target_year_discovery.py src/eidp/cli.py`
  -> `Success: no issues found in 7 source files`.
- `uv run ruff check src/eidp/scraper/url_discovery.py src/eidp/scraper/school_url_pipeline.py src/eidp/scraper/school_url_persistence.py src/eidp/scraper/pdf_discovery.py scripts/bootstrap_pdf_pipeline.py scripts/run_weekly_target_year_discovery.py src/eidp/cli.py tests/unit/test_url_discovery.py tests/unit/test_school_url_pipeline.py tests/unit/test_school_url_persistence.py tests/unit/test_cli_crawl_school_urls.py tests/unit/test_pdf_discovery.py tests/unit/test_cli_pdf_discovery_strict.py tests/unit/test_bootstrap_pdf_pipeline.py tests/unit/test_run_weekly_target_year_discovery.py`
  -> `All checks passed`.
- `uv run pytest tests/unit/test_url_discovery.py tests/unit/test_school_url_pipeline.py tests/unit/test_school_url_persistence.py tests/unit/test_cli_crawl_school_urls.py tests/unit/test_pdf_discovery.py tests/unit/test_cli_pdf_discovery_strict.py tests/unit/test_bootstrap_pdf_pipeline.py tests/unit/test_run_weekly_target_year_discovery.py -q`
  -> `264 passed, 5 warnings in 15.45s`.
- `uv run mypy src/eidp/review/app.py src/eidp/review/operator_pages.py src/eidp/review/school_scope.py src/eidp/review/target_year_status.py src/eidp/review/confidence_panels.py src/eidp/review/_pages/school_year_tasks.py src/eidp/review/_pages/url_candidate_review.py src/eidp/review/_pages/settings_page.py src/eidp/review/_pages/prefecture_remarks.py`
  -> `Success: no issues found in 9 source files`.
- `uv run ruff check src/eidp/review/app.py src/eidp/review/operator_pages.py src/eidp/review/school_scope.py src/eidp/review/target_year_status.py src/eidp/review/confidence_panels.py src/eidp/review/_pages/school_year_tasks.py src/eidp/review/_pages/url_candidate_review.py src/eidp/review/_pages/settings_page.py src/eidp/review/_pages/prefecture_remarks.py tests/unit/test_review_app.py tests/unit/test_review_school_scope.py tests/unit/test_review_school_year_tasks.py tests/unit/test_review_url_candidate_review.py tests/unit/test_review_confidence_panels.py tests/unit/test_review_prefecture_remarks.py`
  -> `All checks passed`.
- `uv run pytest tests/unit/test_review_app.py tests/unit/test_review_school_scope.py tests/unit/test_review_school_year_tasks.py tests/unit/test_review_url_candidate_review.py tests/unit/test_review_confidence_panels.py tests/unit/test_review_prefecture_remarks.py -q`
  -> `104 passed in 2.12s`.
- `uv run mypy scripts/validate_windows_install.py scripts/verify_windows_distribution.py scripts/run_non_windows_release_gates.py`
  -> `Success: no issues found in 3 source files`.
- `uv run ruff check scripts/validate_windows_install.py scripts/verify_windows_distribution.py scripts/run_non_windows_release_gates.py tests/unit/test_windows_install_validator.py tests/unit/test_windows_distribution_verifier.py tests/unit/test_non_windows_release_gates.py`
  -> `All checks passed`.
- `uv run pytest tests/unit/test_windows_install_validator.py tests/unit/test_non_windows_release_gates.py -q`
  -> `52 passed in 1.16s`.
- `uv run pytest tests/unit/test_windows_distribution_verifier.py tests/unit/test_windows_packaging_spike.py -q`
  -> `180 passed in 3.99s`.
- `uv run mypy src/eidp/scraper/prefecture_aggregator.py src/eidp/scraper/discovery_gold_set.py scripts/verify_windows_distribution.py`
  -> `Success: no issues found in 3 source files`.
- `uv run ruff check src/eidp/scraper/prefecture_aggregator.py src/eidp/scraper/discovery_gold_set.py scripts/verify_windows_distribution.py tests/unit/test_discovery_gold_set_seed.py tests/unit/test_windows_distribution_verifier.py`
  -> `All checks passed`.
- `uv run pytest tests/unit/test_discovery_gold_set_seed.py tests/unit/test_windows_distribution_verifier.py -q`
  -> `111 passed in 4.56s`.
- `uv run mypy src/eidp/scraper/prefecture_aggregator.py scripts/download_prefecture_artifacts.py`
  -> `Success: no issues found in 2 source files`.
- `uv run ruff check src/eidp/scraper/prefecture_aggregator.py scripts/download_prefecture_artifacts.py tests/unit/test_prefecture_aggregator.py tests/unit/test_prefecture_artifact_bootstrap.py tests/unit/test_cli_prefecture_aggregate_safety.py tests/unit/test_review_prefecture_remarks.py`
  -> `All checks passed`.
- `uv run pytest tests/unit/test_prefecture_aggregator.py tests/unit/test_prefecture_artifact_bootstrap.py tests/unit/test_cli_prefecture_aggregate_safety.py tests/unit/test_review_prefecture_remarks.py -q`
  -> `47 passed, 5 warnings in 1.44s`.
- `uv run mypy src/eidp/pdf/extractor.py src/eidp/pdf/ocr.py src/eidp/pdf/schema.py src/eidp/pipeline/ingest.py`
  -> `Success: no issues found in 4 source files`.
- `uv run ruff check src/eidp/pdf/extractor.py src/eidp/pdf/ocr.py src/eidp/pdf/schema.py src/eidp/pipeline/ingest.py tests/unit/test_pdf_parser_regression.py tests/unit/test_pdf_ocr_tesseract_provider.py tests/unit/test_ingest_confidence_gating.py`
  -> `All checks passed`.
- `uv run pytest tests/unit/test_pdf_parser_regression.py tests/unit/test_pdf_ocr_tesseract_provider.py tests/unit/test_ingest_confidence_gating.py -q`
  -> `37 passed in 6.16s`.
- `uv run mypy src/eidp/excel/importer.py src/eidp/cli.py`
  -> `Success: no issues found in 2 source files`.
- `uv run ruff check src/eidp/excel/importer.py src/eidp/cli.py tests/unit/test_cli_pdf_discovery_strict.py tests/unit/test_importer_idempotency.py`
  -> `All checks passed`.
- `uv run pytest tests/unit/test_cli_pdf_discovery_strict.py::test_import_excel_surfaces_invalid_year_warning tests/unit/test_importer_idempotency.py::test_taisho_hiritu_skips_unrealistic_future_fiscal_year tests/unit/test_importer_idempotency.py::test_parse_fiscal_year_rejects_unrealistic_future_era_label -q`
  -> `3 passed in 0.57s`.
- `uv run pytest tests/unit/test_importer_idempotency.py tests/unit/test_cli_pdf_discovery_strict.py -q`
  -> `13 passed in 0.78s`.
- `uv run mypy src/eidp/review/_pages/pdf_manual_entry.py src/eidp/review/_pages/excel_preview.py src/eidp/review/_pages/fiscal_year_override.py`
  -> `Success: no issues found in 3 source files`.
- `uv run ruff check src/eidp/review/_pages/pdf_manual_entry.py src/eidp/review/_pages/excel_preview.py src/eidp/review/_pages/fiscal_year_override.py tests/unit/test_review_pdf_manual_entry.py tests/unit/test_review_excel_preview.py tests/unit/test_review_fiscal_year_override.py`
  -> `All checks passed`.
- `uv run pytest tests/unit/test_review_pdf_manual_entry.py tests/unit/test_review_excel_preview.py tests/unit/test_review_fiscal_year_override.py -q`
  -> `63 passed, 5 warnings in 2.40s`.
- `uv run mypy src/eidp/pipeline/manual_entry.py src/eidp/review/_pages/audit_log.py`
  -> `Success: no issues found in 2 source files`.
- `uv run ruff check src/eidp/pipeline/manual_entry.py src/eidp/review/_pages/audit_log.py tests/unit/test_manual_entry_contract.py tests/unit/test_review_pdf_manual_entry.py tests/unit/test_review_audit_log.py tests/unit/test_review_audit_log_dashboard.py`
  -> `All checks passed`.
- `uv run pytest tests/unit/test_manual_entry_contract.py tests/unit/test_review_pdf_manual_entry.py tests/unit/test_review_audit_log.py tests/unit/test_review_audit_log_dashboard.py -q`
  -> `78 passed, 5 warnings in 2.67s`.
- `uv run ruff check src/eidp/excel/exporter.py tests/unit/test_excel_exporter.py tests/unit/test_review_excel_preview.py`
  -> `All checks passed`.
- `uv run mypy src/eidp/excel/exporter.py`
  -> `Success: no issues found in 1 source file`.
- `uv run pytest tests/unit/test_excel_exporter.py tests/unit/test_review_excel_preview.py -q`
  -> `14 passed in 1.07s`.
- `uv run ruff check src/eidp/pipeline/ingest.py tests/unit/test_ingest_confidence_gating.py tests/unit/test_ingest_alias_consultation.py tests/unit/test_normal_ingest_appendonly.py`
  -> `All checks passed`.
- `uv run mypy src/eidp/pipeline/ingest.py`
  -> `Success: no issues found in 1 source file`.
- `uv run pytest tests/unit/test_ingest_confidence_gating.py tests/unit/test_ingest_alias_consultation.py tests/unit/test_normal_ingest_appendonly.py -q`
  -> `36 passed in 1.76s`.
- `uv run pytest tests/unit/test_ingest_confidence_gating.py -q`
  -> `27 passed in 0.96s`; confirms low-confidence DepartmentYearly /
  SupportRecipient revisions are append-only but parked out of current Excel
  surfaces until operator review.
- `uv run pytest tests/unit/test_manual_entry_contract.py tests/unit/test_review_pdf_manual_entry.py tests/unit/test_fiscal_year_override.py tests/unit/test_review_audit_log.py tests/unit/test_review_audit_log_dashboard.py tests/unit/test_excel_exporter.py tests/unit/test_review_excel_preview.py -q`
  -> `101 passed, 5 warnings in 3.32s`; covers manual-entry append-only writes,
  fiscal-year override audit rows, audit-log/outbox helpers, and Excel export /
  preview surfaces at unit level.
- `uv run ruff check src/eidp/pipeline/fiscal_year_override.py tests/unit/test_fiscal_year_override.py tests/unit/test_review_fiscal_year_override.py`
  -> `All checks passed`.
- `uv run mypy src/eidp/pipeline/fiscal_year_override.py`
  -> `Success: no issues found in 1 source file`.
- `uv run pytest tests/unit/test_fiscal_year_override.py tests/unit/test_review_fiscal_year_override.py -q`
  -> `20 passed in 0.95s`.
- `uv run eidp discovery-gold-set --json`
  -> `44` entries, `10` strict target-year successes, `17` publication-lag
  entries, and `undemonstrated_pattern_sources=[]`.
- `uv run eidp eval-discovery-gold --predictions data/discovery-gold-set/expected-predictions.jsonl --fail-on-regression --json`
  -> `44` exact matches, `0` failed predictions, `0` missing entries, and `0`
  unexpected predictions.
- `uv run pytest tests/unit/test_pdf_discovery.py -q -k "renewal or koushin or english_renewal or target_form or pre_download"`
  -> `38 passed, 124 deselected, 5 warnings`.
- `uv run ruff check src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py`
  -> `All checks passed`.
- `uv run mypy src/eidp/scraper/pdf_discovery.py`
  -> `Success: no issues found in 1 source file`.
- `uv run pytest tests/unit/test_audit_outbox.py tests/unit/test_windows_distribution_verifier.py::test_verify_core_zip_requires_manual_action_audit_contract tests/unit/test_discovery_gold_set_seed.py tests/unit/test_cli_pdf_discovery_strict.py::test_import_excel_surfaces_invalid_year_warning tests/unit/test_importer_idempotency.py::test_taisho_hiritu_skips_unrealistic_future_fiscal_year tests/unit/test_importer_idempotency.py::test_parse_fiscal_year_rejects_unrealistic_future_era_label -q`
  -> `24 passed`.
- `uv run ruff check src/eidp/db/audit_outbox.py scripts/verify_windows_distribution.py tests/unit/test_audit_outbox.py tests/unit/test_windows_distribution_verifier.py`
  -> `All checks passed`.
- `uv run mypy src/eidp/db/audit_outbox.py scripts/verify_windows_distribution.py`
  -> `Success: no issues found in 2 source files`.
- `uv run pytest tests/unit/test_reports.py tests/unit/test_cli_reports.py tests/unit/test_ship_gate_contract.py tests/unit/test_bootstrap_pdf_pipeline.py::test_bootstrap_target_pdf_yield_metrics_marks_gate_status tests/unit/test_run_weekly_target_year_discovery.py::test_weekly_yield_metrics_count_review_candidate_statuses_as_operator_reviewable -q`
  -> `40 passed in 0.92s`.
- `uv run ruff check scripts/ship_gate_contract.py src/eidp/reports/ship_readiness.py src/eidp/cli_reports.py tests/unit/test_reports.py tests/unit/test_cli_reports.py tests/unit/test_ship_gate_contract.py`
  -> `All checks passed`.
- `uv run mypy scripts/ship_gate_contract.py src/eidp/reports/ship_readiness.py src/eidp/cli_reports.py`
  -> `Success: no issues found in 3 source files`.
- `uv run pytest tests/unit/test_stage6_recovery_check.py tests/unit/test_stage6_residual_cleanup.py tests/unit/test_stage6_evidence_bundle.py tests/unit/test_windows_packaging_spike.py tests/unit/test_windows_distribution_verifier.py -q`
  -> `197 passed`.
- `uv run mypy scripts/collect_stage6_evidence.py scripts/verify_stage6_evidence.py scripts/stage6_residual_cleanup.py scripts/stage6_recovery_check.py scripts/verify_windows_distribution.py`
  -> `Success: no issues found in 5 source files`.
- `uv run ruff check scripts/collect_stage6_evidence.py scripts/verify_stage6_evidence.py scripts/stage6_residual_cleanup.py scripts/stage6_recovery_check.py scripts/verify_windows_distribution.py tests/unit/test_stage6_evidence_bundle.py tests/unit/test_stage6_residual_cleanup.py tests/unit/test_stage6_recovery_check.py tests/unit/test_windows_packaging_spike.py`
  -> `All checks passed`.
- `uv run pytest tests/unit/test_pdf_discovery.py -q -k "heading_year or intervening_non_year_block or update_date or publication_date or western_year_anchor or reiwa_year_anchor"`
  -> `9 passed, 152 deselected, 5 warnings`.
- `uv run pytest tests/unit/test_audit_outbox.py -q`
  -> `14 passed`.
- `uv run pytest tests/unit/test_extraction_confidence.py tests/unit/test_ingest_confidence_gating.py::test_env_override_promotes_borderline_row_to_current tests/unit/test_excel_exporter.py::test_excel_exporter_confidence_thresholds_follow_central_env -q`
  -> `59 passed`.
- `uv run pytest tests/unit/test_discovery_gold_set_seed.py::test_seed_discovery_gold_sites_rejects_unsafe_site_url_before_writing tests/unit/test_discovery_gold_set_seed.py::test_seed_discovery_gold_sites_fails_fast_on_semantically_invalid_entry tests/unit/test_discovery_gold_set_seed.py::test_seed_discovery_gold_sites_checks_normalized_site_url -q`
  -> `3 passed`.
- `uv run pytest tests/unit/test_review_pdf_manual_entry.py::test_manual_queue_summary_and_table_explain_next_actions tests/unit/test_review_pdf_manual_entry.py::test_discovery_trace_summary_explains_pdf_route_to_operator tests/unit/test_review_pdf_manual_entry.py::test_fiscal_year_evidence_summary_distinguishes_pdf_text_and_link_hints -q`
  -> `3 passed`.
- `uv run pytest tests/unit/test_pdf_discovery.py::test_pre_download_does_not_treat_romanized_renewal_form_alone_as_target tests/unit/test_pdf_discovery.py::test_pre_download_does_not_treat_english_renewal_form_alone_as_target tests/unit/test_pdf_discovery.py::test_pre_download_does_not_treat_english_renewal_form_with_english_support_hint_as_target -q`
  -> `3 passed`.
- `uv run ruff check src/eidp/extraction_confidence.py tests/unit/test_extraction_confidence.py src/eidp/db/audit_outbox.py tests/unit/test_audit_outbox.py`
  -> `All checks passed`.
- `uv run mypy src/eidp/extraction_confidence.py src/eidp/db/audit_outbox.py`
  -> `Success: no issues found in 2 source files`.

Known non-goal-wide lint boundary:

- `uv run ruff check .` currently scans untracked `_temp/` extractions and
  historical one-off scripts; it reported existing lint debt and is not a
  reliable current-source release gate.
- `git ls-files -z '*.py' | xargs -0 uv run ruff check` also currently reports
  historical lint debt outside `src/`, mainly Alembic revision style, old
  one-off analysis scripts, and Japanese test function names. Tracked source
  package linting is clean via `uv run ruff check src`; goal-relevant changed
  surfaces above were checked with targeted Ruff/Mypy/tests.
- `uv run mypy src` is now a usable source-wide gate for the tracked source
  tree. This is still Mac-side evidence only;
  it does not prove the real Windows operator-PC Stage 6 one-cycle or the
  rolling FY yield gate. The v459 browser navigation, v459 UI write/audit
  sandbox, and v459 R7 browser Excel proof are real browser evidence, but they
  are still Codex-driven validation, not the owner/operator real-cycle
  sign-off.

## Next Concrete Gate

SSH-Win is available and v460 is already transferred, SHA-verified, extracted,
set up, after-setup validated, recovery-checked, Task Scheduler-pointed,
disk-retention-checked, read-only UI-smoked, and companion-docs-staged. v459
remains the latest bounded evidence/weekly/R7 Excel/write support lane, but the
active owner/operator execution lane is v460. The v460 real-cycle card now contains the
owner/operator request and return-material list. The next gate is not another
audit; it is an owner/operator Stage 6 real-cycle sign-off on the current v460
lane, plus the later R8 production yield measurement.

Current v460 package:

```text
Package snapshot: 01e44279238aaef9127ed9b578e29dc8e0070499
Expected SHA256: ce5fa49b8c30900a33b31fd317c6846ffe5839053f2bdd1ffdeb8cca2113129c
Extract path: C:\Users\cyo20\EIDP-v460-01e4427
Evidence bundle: pending for v460 real-cycle
Real-cycle card: docs/runbooks/eidp-v460-real-cycle-card.md
Companion docs: C:\EIDP-staging\v460-operator-docs-20260517
```

The v460 package gate returned `ok=true`; if additional docs-only status edits
are made after this point, run the docs-only stale package gate before treating
those docs as release-status current. The post-package `.env.example` update is
not docs-only for package freshness purposes and requires a future rebuild if it
must be included in a Windows ZIP.

For Mac-driven remote UI verification, start the operator UI tunnel after
Windows setup/validation has passed:

```bash
ssh -N -o ClearAllForwardings=no -o ExitOnForwardFailure=yes -L 127.0.0.1:18501:127.0.0.1:8501 win
```

Complete the Stage 6 click-through against the real v460 operator cycle or an
approved full-cycle copy: manual PDF entry write if needed, fiscal-year override
write if needed, Excel preview/download for the active cycle, audit log/outbox
flush, diagnostics capture, evidence verify, and sign-off fields. Do not treat
the Codex-driven bounded launcher, browser navigation, UI-write sandbox, or R7
Excel proof as the final operator sign-off.

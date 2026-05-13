# EIDP Current Release Status

Updated: 2026-05-14
Branch: `sprint8-handoff-finalize`
Current Mac-verifier-clean package: `dist/eidp-windows-v393.zip`
Package commit: `a992ef6f37589f26db640c602d790711e5f740dd`
Package SHA256: `3ab58cca9494940ac85c7018aed2faeebc20d1784370d7203b8642b5623a32e8`
Latest full non-Windows release-gate package: `dist/eidp-windows-v393.zip`
Latest Windows-core-validated package: `dist/eidp-windows-v393.zip`
Latest Windows-OCR-runtime-proven package: `dist/eidp-windows-v384.zip`
Latest Windows-OCR-image-write-proven package: `dist/eidp-windows-v384.zip`
Latest Windows-setup-proven package: `dist/eidp-windows-v384.zip`
Latest Windows-bounded-backend-smoke package: `dist/eidp-windows-v384.zip`
Latest Windows-bounded-bootstrap-proven package: `dist/eidp-windows-v384.zip`
Latest historical Windows-validated package: `dist/eidp-windows-v376.zip`
Current Stage 6 evidence draft: `docs/reports/eidp-v380-stage6-evidence-draft.md`

## Verdict

Status: **NOT COMPLETE**

The current Mac-verifier-clean ZIP snapshot is v393. It packages commit
`a992ef6`, which adds a root-level `EIDP-stage6-evidence.bat` launcher, the
Windows-local `scripts\collect_stage6_evidence.bat` wrapper, and the stdlib
`scripts/collect_stage6_evidence.py` helper so a non-technical operator can
create `logs\stage6-evidence-*.zip` without browsing into `scripts\`. The
evidence bundle refreshes diagnostics, includes build/run/recovery/bootstrap/
Excel/RCA evidence plus a manifest, and deliberately excludes the runtime DB,
WAL/SHM files, PDFs, wheelhouse, and runtime directories. v393 preserves the
v391 root `EIDP-stage6-recovery.bat` launcher and the v390 Stage 6 operator E2E
template contract requiring `[stage6 recovery check]` diagnostics evidence:
`stage6_recovery_rc`, scheduled-task execute path, expected action,
action-match status, residual interrupted-smoke paths, recommendations,
optional `logs\stage6-recovery-*.json`, and now optional
`logs\stage6-evidence-*.zip` attachment. It keeps the read-only
`scripts/stage6_recovery_check.py` helper in the Windows ZIP, includes the
Windows-local `scripts\stage6_recovery_check.bat` wrapper for SSH-unavailable
recovery, defaults that wrapper to the current extracted package's
`scripts\weekly_run.bat`, and keeps the `[stage6 recovery check]` section in
`scripts\diagnose.bat`, so ordinary diagnostics capture scheduled-task action
and interrupted-smoke residue status. It preserves the v384 image-PDF ingest
path that routes through the packaged/system Tesseract TSV wrapper when
available and records OCR provenance in DB confidence breakdowns. The v393
versioned ZIP and latest alias both pass
`scripts/verify_windows_distribution.py --json`; the latest alias also passes
with the v383 OCR add-on and v106 Playwright add-on. The v393 core SHA256 is
`3ab58cca9494940ac85c7018aed2faeebc20d1784370d7203b8642b5623a32e8`, with
`44` discovery gold-set entries, `17` publication-lag cases, `47` prefecture
seeds, `entry_count=3070`, and `undemonstrated_pattern_sources=[]`. The latest
full non-Windows release gate is now v393 with `1418` unit tests, `44` exact
discovery gold-set predictions, and both package verifier modes passing
against SHA256
`3ab58cca9494940ac85c7018aed2faeebc20d1784370d7203b8642b5623a32e8`.
The latest Windows setup proof is now v384: the versioned ZIP was transferred
to the operator PC, its SHA256 sidecar matched
`2707def6337f3f35c63c9933a1805271dcf75d8bf7d8ece27c09ba8de72d31c0`, and it
was extracted to
`C:\Users\cyo20\EIDP-v384-75732b0-setup-probe`. In that disposable extraction,
`scripts\first_setup.bat` returned `setup_rc=0`, the after-setup validator
returned `ok=true` with `school_count=2418`,
`school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`,
`wheel_count=78`, build commit
`75732b057a115afcebe35f9a40b831fac0ffa6f6`, and `build_dirty=false`, and
`EIDP-diagnose.bat` returned `diagnose_rc=0` with
`validate_after_setup_rc=0` and `retroactive_ship_readiness_rc=0`. The setup
probe confirmed that `first_setup.bat` registered `EIDP Weekly Run` to the
v384 probe during setup, then restored the original operator task afterward:
the restored task contains `EIDP-v380-f6a5e6d` and does not contain
`EIDP-v384-75732b0-setup-probe`. The v384 browser UI service, initial render,
and read-only quick navigation are now also proven in disposable operator-PC
extractions. The initial render probe ran under
`C:\Users\cyo20\EIDP-v384-75732b0-ui-probe`: the local tunnel
`127.0.0.1:18501 -> Windows 127.0.0.1:8501` returned
`/_stcore/health` as HTTP `200 OK`, Browser/Playwright rendered
`http://127.0.0.1:18501/` with title `EIDP Operator Console`, the snapshot
showed the default `① 学校別タスク` page, target
`2026年度（令和8年度）`, build `75732b0`, `対象年度 要対応 2418`,
`Excel出力可 0/2418 校`, and the initial acquisition warning, and captured
console messages reported `0` errors and `0` warnings. A follow-up
`C:\Users\cyo20\EIDP-v384-75732b0-ui-nav-probe` run clicked only the five
non-mutating quick navigation buttons for `PDF確認・手入力`,
`対象年度の判定・修正`, `④ Excel プレビュー`, `⑤ 設定（年度・OCR・API）`,
and back to `① 学校別タスク`; each page rendered, the Excel page showed
`対象年度: 2026年度（令和8年度） / 対象範囲: 専門学校`, and the workbook
generation button remained disabled for empty FY2026 data. The incremental
console capture for that navigation reported `5` messages with `0` errors and
`0` warnings. Both v384 UI probes were then stopped and removed; cleanup
confirmed no `8501` listener remained and the restored `EIDP Weekly Run` task
still points at v380. This v384 proof covers setup, diagnostics, service
health, initial browser rendering, read-only quick navigation, the FY2026
Excel disabled-state display, and the retroactive FY2025/R7 Excel
preview/download browser path. The v384 R7 probe ran with process-scoped
`EIDP_TARGET_FISCAL_YEAR=2025`, showed `抽出済み学校 2031` and
`Excel対象行 7150`, generated the in-memory workbook, exposed
`Excel ダウンロード`, downloaded `eidp_master.xlsx` at `3,728,651` bytes,
and the downloaded workbook opened with sheets `採録状況`, `対象比率`,
`学科別`, and `在籍のみ抜粋`. The workbook row counts observed through
`openpyxl` were `採録状況=2419`, `対象比率=10023`, `学科別=9721`,
and `在籍のみ抜粋=9721`, including header rows; the Streamlit stdout export
counts were `採録状況=2418`, `対象比率=10022`, `学科別=9719`, and
`在籍のみ抜粋=9719`. The R7 probe was then stopped and removed; cleanup
confirmed no `8501` listener remained and the scheduled task still points at
v380. v384 now also has a sandboxed `PDF確認・手入力` browser save proof:
a disposable copied-DB extraction under
`C:\Users\cyo20\EIDP-v384-75732b0-manual-entry-sandbox` seeded one FY2026
`parse_failed` document, the tunneled UI saved one `V384手入力学科` row with
reason `v384 UI manual entry smoke`, and post-UI SQLite verification found
the document promoted to `ingested`, one manual `DepartmentYearly` row, three
`manual_entry` audit rows, zero SupportRecipient rows for that document, and
zero matching marker rows in the real runtime DB. v384 now also has a
sandboxed URL-candidate reject browser proof: the UI opened `詳細 operator`
-> `URL候補レビュー`, rejected one seeded
`https://example.com/eidp-v384-url-candidate-smoke` candidate with reason
`v384 UI reject smoke`, resolved the `ReviewItem`, emitted one
`url_candidate_rejected` audit row, created no `SchoolSite` row, and left the
real runtime DB with zero matching marker rows. v384 now also has a sandboxed
audit-outbox browser flush proof: the UI opened `詳細 operator` -> `監査ログ`, verified
`JSONL outbox 未送信` pending count `1`, clicked `Outbox を flush`, observed
`exported=1 already_present=0 failed=0`, and post-UI verification found the
seeded `stage6_v384_ui_audit_flush_smoke` row stamped as exported, one matching
JSONL row, pending count `0`, and zero matching marker rows in the real runtime
DB. v384 now also has a sandboxed `③ 年度判定・修正` browser write proof:
the UI submitted `年度を確定` with reason
`v384 UI fiscal override smoke`, moved one seeded FY2025 ingested document to
FY2026, demoted the old current `DepartmentYearly`, `SupportRecipient`, and
`SchoolYearStatus` rows, demoted a pre-existing FY2026 `DepartmentYearly` row,
inserted new FY2026 current rows, and emitted four `fiscal_year_override`
audit rows without mutating the real runtime DB. v384 now also has persistent
operator-PC environment capture, scheduler query / restore evidence, and a
package-local `eidp db-backup` smoke: the v384 sandbox reported host `JUNMING`,
Windows 11 Pro build `26200`, i9-13900HK, 32 GB visible RAM, `C:` free
`964.4` GB, `db_backup_rc=0`, backup `integrity=ok`, `sqlite_objects=35`,
`school_count=2418`, and restored `EIDP Weekly Run` back to the v380 runtime
task. v384 now also has the package-local SupportRecipient
backend ingest smoke: the v384 package runtime seeded two FY2026 target
documents, monkeypatched only the package parser boundary, called
`ingest_document` twice, and verified SupportRecipient revisions `1` and `2`
with only revision `2` current while the real runtime DB marker counts stayed
zero. v380 was transferred to the operator PC, hash-checked, extracted into a
separate directory, set up with `EIDP-setup.bat`, diagnosed, and smoke-tested
through `eidp db-backup`.
v380 also has
read-only operator-PC
environment and scheduler
evidence: host `JUNMING` is `Microsoft Windows 11 Pro` build `26200`, with a
13th Gen Intel Core i9-13900HK, about 32 GB visible RAM, `C:` free space
`1058.8` GB, and an `EIDP Weekly Run` scheduled task in `Ready` state pointing
at `C:\Users\cyo20\EIDP-v380-f6a5e6d\scripts\weekly_run.bat`. v380 also proves
the retroactive FY2025/R7 Excel preview/download browser path
with the same package. v380 has the older sandboxed URL-candidate reject
browser write path and audit-outbox browser flush path against disposable
copied databases.
v380 also has the older
`PDF確認・手入力` browser save path and `③ 年度判定・修正` browser write path
for disposable copied databases. v384 now also has a sandboxed bounded backend
bootstrap smoke for the 5-site Saitama official-index path: it downloaded the
Saitama artifact, added `51` prefecture-aggregator SchoolSite rows, crawled `5`
sites, wrote `2084` discovery evidence lines, generated an RCA batch with `5`
items, rebuilt `2418` status rows, and left the real runtime DB unchanged.
These observations are consolidated in
`docs/reports/eidp-v380-stage6-evidence-draft.md` as a draft, not a completed
operator sign-off. OCR add-on runtime proof is now stronger but still bounded:
the v380 operator install has no `ocr-addon` directory and
`detect_ocr_availability` correctly reports `can_run=false`; v381 carried the
Windows RAM-detection fix and a runtime-only probe on the operator PC returned
`cpu_count=20`, `free_ram_mb=16242`, and `ocr_auto_enable=true`; v382 added the
stricter `--require-ocr-runtime` validator gate that executes packaged
`tesseract.exe --version` and `tesseract.exe --list-langs`; and v383 adds the
TSV config file required by the OCR wrapper's TSV path. A v383 smoke OCR add-on
ZIP built from UB Mannheim Windows Tesseract `v5.4.0.20240606` plus local
`jpn.traineddata` verifies as SHA256
`bd1e2c96dcd7ac17562d44c3338fbf8da0ac21a1b1e60386073c730775e8d853`,
`entry_count=267`, and `manifest_files=266`. In a disposable operator-PC v384
extraction with the add-on, the OCR image smoke generated
`ocr_full_text="V384 OCR WRITE SMOKE 2026"` from a PNG,
`ocr_conf_values=[93,94,96,96,96]`, `ocr_avg_confidence=0.95`, inserted one
`DepartmentYearly` row through `save_manual_entries` with
`extraction_method="ocr_tesseract"`, `extraction_confidence=0.95`, and
`verified=true`, promoted the copied-DB document from `ocr_pending` to
`ingested`, and emitted three `manual_entry` audit rows for `department`,
`department_yearly`, and `document`. The real v380 runtime DB had `0` matching
marker rows after the smoke, the disposable v384 probe directory and uploads
were removed, and the weekly task was confirmed restored to the v380 runtime
path. This proves packaged add-on runtime execution, TSV output parsing, and an
OCR-sourced DepartmentYearly write in a copied DB on the latest v384 package.
Post-v383 source now also routes image-PDF ingest through the
packaged/system Tesseract TSV wrapper when available and propagates
`ocr_tesseract` confidence breakdowns to both `DepartmentYearly` and
`SupportRecipient` rows in focused unit coverage. A disposable operator-PC v384
extraction under
`C:\Users\cyo20\EIDP-v384-75732b0-ocr-runtime-probe` then expanded the v384
core ZIP plus the v383 smoke OCR add-on and ran
`runtime\python\python.exe scripts\validate_windows_install.py . --require-ocr-runtime --json`;
it returned `ok=true`, build commit
`75732b057a115afcebe35f9a40b831fac0ffa6f6`, `build_dirty=false`,
`wheel_count=78`, packaged Tesseract
`C:\Users\cyo20\EIDP-v384-75732b0-ocr-runtime-probe\ocr-addon\tesseract\tesseract.exe`,
version `tesseract v5.4.0.20240606`, and languages including `jpn` and
`jpn_vert`. This proves the latest v384 package can detect and execute the OCR
add-on on the operator PC. A follow-up disposable v384 copied-DB smoke under
`C:\Users\cyo20\EIDP-v384-75732b0-ocr-write-sandbox` used the same v384 core
ZIP plus the v383 OCR add-on, generated `data\ocr-write-smoke.png`, ran
packaged Tesseract through `run_tesseract_on_image(...)`, and returned
`ocr_full_text="V384 OCR WRITE SMOKE 2026"`, `ocr_usable_word_count=5`,
`ocr_conf_values=[93,94,96,96,96]`, and `ocr_avg_confidence=0.95`; then
`save_manual_entries(..., method="ocr_tesseract")` wrote one copied-DB
`DepartmentYearly` row with `extraction_method="ocr_tesseract"`,
`extraction_confidence=0.95`, and `verified=true`, promoted the marker
document from `ocr_pending` to `ingested`, and emitted three `manual_entry`
audit rows for `department`, `department_yearly`, and `document`. The real v380
runtime DB had `0` matching marker rows, cleanup removed the v384 OCR sandbox
and uploads, and a follow-up query confirmed `EIDP Weekly Run` was `Ready` with
action `C:\Users\cyo20\EIDP-v380-f6a5e6d\scripts\weekly_run.bat`. It still does
not prove
operator-PC real target-form OCR extraction, operator-PC SupportRecipient OCR
writes, or a full Stage 6 operator cycle. The latest bounded bootstrap proof is
the v384 Saitama 5-site sandbox; the broader 50-site bootstrap evidence remains
v342.

Release gate interpretation:

- **Process gate / v1.0-rc evidence**: a real operator-PC Stage 6 cycle proves
  setup, diagnostics, UI navigation, audit logging, Excel preview/download, and
  bounded write behavior on the handed-off Windows package. FY2025/R7
  retroactive validation may support this process evidence because it tests the
  rolling-fiscal-year mechanics against a more complete disclosure season.
- **Yield gate / v1.0 GA evidence**: current target-FY FY2026/R8 readiness must
  still reach the shipping line: true target confirmation PDFs are acquired or
  operator-reviewable at a rate sufficient for estimated manual workload
  `<=30%`. Retroactive FY2025 evidence must not be counted as FY2026/R8
  current-year yield or Excel readiness.

v376 fixes a Windows-only diagnostics bug in the retroactive fiscal-year
snapshot: the v375 ZIP passed token-based package verification, but real
Windows batch execution skipped the FY2025 `ship-readiness --fy` call because
the batch-side Python-output capture was too fragile. The v376 package moves
that logic into Python and records the retroactive JSON plus
`retroactive_ship_readiness_rc=0` in `EIDP-diagnose.bat`.
v341 keeps the v326 strict-mode fix for opaque WordPress Download
Manager wrappers, the v328 cross-school candidate rejection, the v329
actionable RCA counts, the v330 raw-control-character URL guard, and the v331
one-retry guard for transient registered-page timeouts plus structured
`discovery_error` evidence (`error_code`, `retryable`). It adds the v332
HAL東京/NKZ embed-subpage discovery demonstration and the v333 strict-year
correction: prefecture-index freshness is source/crawl evidence only and no
longer fills missing PDF/link fiscal-year evidence. v334 aligns the discovery
gold-set with that strict-year correction by reclassifying two former
prefecture-index-only auto successes as operator-review candidates. v335
tightens Codex/manual RCA outcome validation so `needs_operator_review` must
name a concrete candidate PDF and target-form evidence. v336 adds a real
Saitama CMCC RCA demonstration for a readable target-form PDF that still lacks
PDF/link FY2026 evidence. v337 adds a paired 埼玉自動車大学校 demonstration
that prevents incidental `令和8` committee-term text from becoming target-FY
evidence. v338 adds a Central Information College demonstration showing that
page update dates and officer-term dates are not target-FY evidence. v339 fixes
the ship/operator-reviewable metric so `target_year_unverified` rows (年度未確認候補)
are counted together with `publication_lag` rows instead of disappearing from
bootstrap, weekly, ship-readiness, and Windows validator calculations. Windows
setup, SQLite initialization, diagnostics, and a bounded 50-site Saitama
bootstrap have been rerun through v342 and confirm the metric fix: the current
sample now reports `operator_reviewable_count=46` from `publication_lag=38`
plus `target_year_unverified=8`. The product goal is
still not complete: browser UI read-only quick navigation now renders, but
operator-action click-through is missing, and the measured
operator-reviewable coverage / Excel readiness remain far below the shipping
line. v340 adds a demonstration-backed ARS/アルスコンピュータ publication-lag
case: current-year R8 PDFs on that page are syllabus/course-plan PDFs, while
the latest target confirmation form remains R7. This improves discovery
reproducibility. Windows v340 setup and bounded 50-site Saitama bootstrap have
been rerun and preserve the same status counts while moving the ARS R8 syllabus
PDFs into pre-download rejection evidence. v341 fixes a demonstrated Kanto
disclosure-card context leak: a visible `様式第2号` link was previously polluted
by the previous card's `事業報告書` / `財務諸表` / `役員名簿` text and ranked below
generic links. The v341 Windows package now ranks that target-form candidate
first, while strict download still routes it to review as
`image_only` / `fiscal_year_mismatch:2024`. v342 preserves demonstrated evidence
contexts that were still weak after v341: WordPress Download Manager package
titles such as 入間看護専門学校 `様式２（R6年度分申請）` now flow into the
candidate context, and image-only old-year `j2024_05a` / `様式第2号` evidence is
treated as operator-reviewable rather than dropped as generic non-target noise.
The v342 Windows bounded bootstrap confirms both fixes in packaged runtime:
current Saitama evidence evaluates as `16` exact gold-set predictions with
`0` failures, while the bootstrap remains correctly below ship gate because no
current-FY target PDFs were downloaded in the bounded 50-site sample. A separate
Tokyo official-index probe on the same v342 Windows package confirms the same
failure mode at a different prefecture boundary: the Tokyo official artifact
matched `232` school URLs and a 30-site PDF discovery sample found candidates on
all `30` sites, but still downloaded `0` strict current-FY target PDFs. v343
packages those Tokyo observations as three new source-side discovery gold-set
entries, raising the packaged gold-set from `28` to `31` entries. v344 keeps the
same discovery evidence package and removes the remaining Excel preview
confidence-threshold label drift by reading the same centralized thresholds as
the workbook exporter. v345 tightens the Tokyo gold-set regression contract by
requiring the actual observed candidate `pattern_type` for those entries
(`direct` or `wordpress`), so future replays cannot silently change the source
classification while preserving the same PDF URL. v347 moves the six
synthetic-only extractor sources (`data_attribute`, `form_action`,
`input_control`, `meta_refresh`, `onclick`, `select_option`) behind the
explicit `EIDP_PDF_DISCOVERY_EXPERIMENTAL_EXTRACTORS` flag, so the default
release surface only includes production-tracked sources that have gold-set
demonstrations. v348 adds a package verifier token gate for that default-off
experimental extractor setting, preventing future package builds from silently
turning those synthetic-only patterns back on. v349 packages the source-side
Tokyo Sanko publication-lag regression from the v348 Tokyo 20-site strict smoke,
raising the packaged discovery gold-set to `32` entries while keeping strict
target-PDF auto-success unchanged at `4`. v350 rebuilds the same runtime/data
package after the seed-count test contract update and remains clean under the
broadened rolling-FY package verifier guard. v351 rebuilds the package after
keeping the Windows validator/distribution verifier typing gate clean; runtime
discovery data is unchanged from v350. v352 packages the source-side `db-info`
readiness guard so an uninitialized SQLite file exits cleanly with `rc=2`
instead of printing a Python traceback; runtime discovery data is unchanged
from v351. v353 adds a manual-web demonstrated 聖十字看護専門学校 pattern where a
修学支援 section states `令和8年度より` target-school status immediately before a
確認申請書様式 第2号 PDF link. The default crawler now preserves that nearby
support-year context and downloads the target PDF in strict mode. The packaged
discovery gold-set rises to `33` entries and `5` strict target-year successes.
v354 adds a second manual-web accepted target case for 更生看護専門学校. Its news
definition list puts the `令和8年4月から修学支援新制度` evidence in the preceding
`dd` block and the actual PDF link in the next `dd`. The crawler now keeps that
definition-list context local, accepts April support-system start-month evidence
only when paired with target-form context, and avoids page-wide news archive
pollution. The packaged discovery gold-set rises to `34` entries and `6` strict
target-year successes.
v355 adds a manual-web demonstrated 専門学校中央情報大学校 case where the
information page lists multiple 修学支援制度 confirmation-form PDFs by fiscal
year. The existing crawler correctly chooses the `令和８年度` link over older
令和７年度/令和６年度 forms and downloads the WordPress-hosted target PDF. The
packaged discovery gold-set rises to `35` entries and `7` strict target-year
successes.
v356 adds a manual-web demonstrated 君津中央病院附属看護学校 case where a stale
empty anchor appears immediately before the visible `令和８年度` target-form
anchor. The crawler now keeps visible sibling anchor text local to the visible
anchor instead of assigning it to the empty stale PDF link. The replay now
downloads the correct `2026sinseisyo.pdf` target form. The packaged discovery
gold-set rises to `36` entries and `8` strict target-year successes.
v357 tightens HTML extraction accuracy for current Tokyo Anime public-info
pages: PDF links inside HTML comments are no longer treated as visible
publication candidates. The current page keeps an old
`07_study_support_application.pdf` link inside a comment while exposing visible
`11_confirmation_application.pdf` / `12_kakunin.pdf` links. v357 ignores the
commented stale link without changing the discovery gold-set count, preserving
historical v342 evidence replay compatibility.
v358 separates the operator-review ship gate from strict data diagnostics:
`report ship-readiness --fail-on-missing-goal` now gates on
operator-reviewable coverage / estimated manual workload, while `excel_ready`
continues to appear as `ok_strict` diagnostic output. This keeps the May
publication-lag period from being blocked by the long-term strict data metric
while preserving the strict readiness signal for later release decisions.
v359 starts the `cli.py` size-debt cleanup by moving the report subcommand tree
to `src/eidp/cli_reports.py`. The external CLI remains unchanged
(`eidp report coverage|extraction|gaps|ship-readiness`), the package verifier
now requires the new module, and `cli.py` drops from `1713` lines to `1405`.
v360 continues that cleanup by moving read-only discovery gold-set and RCA
commands to `src/eidp/cli_discovery.py`; the DB-writing
`seed-discovery-gold-sites` command stays in `cli.py` so the existing write-lock
AST gate still covers it. `cli.py` now sits at `997` lines, still above the
`800`-line target but materially reduced from the v358 baseline.
v361 finishes the current `cli.py` size-debt pass by moving read-only/tool
commands (`verify-identity`, `db-info`, `review-ui`, `operator-ui`,
`export-excel`, `export-competition-excel`, `diff-excel`, and `eval-pdf`) to
`src/eidp/cli_tools.py`. DB-writing commands remain in `cli.py` under the
write-lock AST gate. `cli.py` now sits at `753` lines, below the `800`-line
target, and the package verifier requires the new module.
v362 hardens the discovery demonstration baseline: `load_discovery_gold_entries`
now validates each committed entry against `data/discovery-gold-set/schema.json`
before constructing `DiscoveryGoldEntry` objects. The schema now rejects
unknown fields, includes the existing `windows_v320_jsonl` source kind, and the
Windows package verifier requires both the schema-validation code path and the
runtime `jsonschema` dependency. A new retroactive fiscal-year validation
runbook documents how FY2025/R7 can be used for Stage 6 rehearsal and rolling-FY
proof without counting it as FY2026/R8 yield.
v363 marks retroactive fiscal-year readiness reports explicitly. `eidp report
ship-readiness --fy 2025 --json` now emits `configured_target_fiscal_year`,
`calendar_current_fiscal_year`, `is_configured_target_fiscal_year`, and
`is_retroactive_fiscal_year`, and the text output labels retroactive runs as
retroactive validation evidence. This makes R7/FY2025 experiments safe for
pipeline and operator-flow proof while preventing those numbers from being
misreported as R8/FY2026 current-year ship yield.
v364 adds the same rolling-year proof to packaged Windows diagnostics:
`scripts\diagnose.bat` now computes the configured target FY minus one and
runs `eidp report ship-readiness --fy <previous> --json` into the diagnostics
log, recording `retroactive_fiscal_year` and `retroactive_ship_readiness_rc`.
The package verifier now rejects a ZIP whose diagnostics script omits that
retroactive FY snapshot.
v365 carries the retroactive-FY proof through to the packaged Stage 6 evidence
template. `docs/runbooks/eidp-operator-e2e-template.md` now asks the operator
to record `retroactive_fiscal_year`, `is_retroactive_fiscal_year`, and
`retroactive_ship_readiness_rc`, and the package verifier rejects ZIPs whose
template omits those fields.
v366 adds a manual-web / official-index-linked accepted target case for
愛北看護専門学校. The Aichi official-index artifact already links to the school's
support-system news page; that page states the school is a support target from
`令和8年度` and links a `確認申請書様式第2号` PDF whose filename remains
`youshiki2-r7.pdf`. This records the important production pattern where target
FY evidence is supplied by the school page context rather than by the PDF
filename. The packaged discovery gold-set rises to `37` entries and `9` strict
target-year successes, with `wordpress` pattern coverage rising to `5`.
v367 adds a manual-web / official-index-linked publication-lag case for
岩手医科大学医療専門学校. The Iwate official-index artifact links to a dense Wix
information page whose target confirmation-form section exposes links only
through `令和７年度`, while a later non-target syllabus section already contains
`令和8年度` text. The gold-set now records this as latest-public target-form
evidence that must stay visible to the operator without being counted as strict
FY2026 success. Packaged coverage rises to `38` entries and `12`
publication-lag cases, with `direct` pattern coverage rising to `6`.
v368 rebuilds the clean v367 state after the documentation update and refreshes
the operator-facing latest alias. `dist/eidp-windows-v368.zip` and
`dist/eidp-windows.zip` now have the same SHA256
`833d500360456b4b827583d0927480173d20e41700d7db88675691aa084645ad`, so the
versioned package and the default runbook package refer to the same contents.
v369 adds a manual-web / official-index-linked accepted target case for
専門学校浜松工科自動車大学校. The Shizuoka official-index artifact links to
`https://kohka-h.ac.jp/disclose`, whose WordPress disclosure page labels the
target PDF as `令和８年度 様式第２号`. The PDF body contains
`専門学校浜松工科自動車大学校`, `様式第２号`, and `修学支援`, but does not repeat
`令和8年度`; this records the production pattern where local anchor text supplies
the target-FY evidence while same-block generic documents such as 学校情報 /
学生便覧 / 組織図 / 役員名簿 must not outrank the target form. Packaged
discovery gold-set coverage rises to `39` entries, `10` strict target-year
successes, and `wordpress=6`.
v370 adds a manual-web / official-index-linked publication-lag case for
長野県公衆衛生専門学校. The Nagano official-index artifact links directly to a
prefecture-hosted support-system page. That page was updated in 2025 and lists
`令和７年度` / `令和６年度` target-form PDFs, but no `令和８年度` target-form
section. The linked `2025shinseisho2go.pdf` body contains
`長野県公衆衛生専門学校`, `様式第２号`, and `修学支援`, but does not contain
`令和8年度`; this preserves the public-school pattern where the latest public
target-form PDF must remain operator-reviewable publication-lag evidence rather
than strict FY2026 success. Packaged discovery gold-set coverage rises to `40`
entries, `13` publication-lag cases, and `direct=7`; strict target-year
successes remain `10`.
v371 preserves preceding fiscal-year heading context for paragraph and
definition-list PDF links. For Nagano-style public-school pages, a preceding
`<h3>令和７年度</h3>` now travels with the following `申請書 様式第２号` PDF link,
while the page-level update date remains excluded. The stale-year evidence is
therefore recognized as FY2025 publication-lag context and does not become
strict FY2026 success. Packaged discovery gold-set coverage remains `40`
entries, `10` strict target-year successes, `13` publication-lag cases, and
`undemonstrated_pattern_sources=[]`.
v372 adds a manual-web / official-index-linked publication-lag case for
愛生会看護専門学校. The Aichi official-index artifact links to the school's
support page, which lists `令和6年9月公表` and `令和7年9月公表` target-form
sections but no `令和8年度` target-form PDF. The latest
`support_system_2025.pdf` body contains `愛生会看護専門学校` and `様式第２号`,
while the adjacent `subject_2025.pdf` is a subject-list PDF and must not become
the target confirmation form. Packaged discovery gold-set coverage rises to
`41` entries, `14` publication-lag cases, and `direct=8`; strict target-year
successes remain `10`.
v373 adds a manual-web / official-index-linked publication-lag case for
あいち福祉医療専門学校. The Aichi official-index artifact links to a public
documents page whose `2026年度` section exposes syllabus and curriculum-map PDFs,
but no current-year target confirmation-form PDF. The latest target form remains
`2025_kakuninshinsei.pdf` under the `2025年度` section. This records the
production pattern where current-year syllabus PDFs must not outrank or replace
the latest previous-year target confirmation form. Packaged discovery gold-set
coverage rises to `42` entries, `15` publication-lag cases, and `direct=9`;
strict target-year successes remain `10`.
v374 turns that Aichi production pattern into a code-level candidate-ordering
regression guard. A page with current-year syllabus/curriculum PDFs ahead of a
previous-year target confirmation-form PDF must still rank the target form
(`2025_kakuninshinsei.pdf`) first for operator-reviewable publication-lag
handling. Packaged discovery gold-set coverage remains `42` entries, `15`
publication-lag cases, `direct=9`, and `10` strict target-year successes.
v375 closes the remaining fiscal-year-context edge introduced by the v371
heading-context repair: strong fiscal-year headings now require an explicit
fiscal-year label, weak update/publication dates no longer suppress heading
fallback, and preceding heading context is not carried across an intervening
non-year block. It also adds a manual-web / official-index-linked
尚美ミュージックカレッジ専門学校 case where the public-info page lists historical
R1-R7 support forms and the crawler must keep the latest public R7 target form
visible for FY2026 publication-lag handling. Packaged discovery gold-set
coverage rises to `43` entries, `16` publication-lag cases, `direct=10`, and
`10` strict target-year successes.
v376 preserves the v375 discovery code and package contents while fixing the
Windows diagnostics capture for retroactive FY validation. It was extracted to
`C:\Users\cyo20\EIDP-v376-d2402dc`, `EIDP-setup.bat` completed, standalone
after-setup validation returned `ok=true`, and `EIDP-diagnose.bat` wrote
`logs\diagnostics-20260513-211539.txt` with `school_count=2418`,
`sqlite_integrity_check=ok`, `ship_readiness_rc=1` for FY2026, and a successful
FY2025 retroactive section with `is_retroactive_fiscal_year=true`,
`extracted_schools=2031`, `extracted_rate=0.84`, and
`retroactive_ship_readiness_rc=0`. A separate Windows service-level UI smoke
started Streamlit headless from the v376 virtualenv on `127.0.0.1:8501`,
received `200 ok` from `/_stcore/health`, and then stopped the smoke process
without leaving a Streamlit process behind. This proves app server startup, not
operator browser click-through.

Post-v376 source-branch note: commit `e65021e` adds the manual-web / official-
index-linked 中央動物専門学校 publication-lag case. Commits `044d188`,
`4b872b0`, and `82570d9` then add safe data-migration guidance plus package
verifier gates that reject mutable runtime data and stale runbook guidance.
The current source checkout therefore reports `44` discovery gold-set entries,
`10` strict target-year successes, `17` publication-lag cases, `15`
operator-review entries, and `undemonstrated_pattern_sources=[]`, while also
enforcing a stricter ZIP hygiene contract. That source/package evidence is now
packaged in `dist/eidp-windows-v384.zip`; v381 proved the Windows runtime can
detect free RAM without `psutil`, v382 adds a packaged `--require-ocr-runtime`
gate that executes Tesseract runtime probes when an OCR add-on is present, and
v383 adds the Tesseract `configs/tsv` file required by the wrapper's TSV
parsing path. A disposable operator-PC v382 extraction without the add-on
correctly failed that gate on missing `ocr-addon` files. A disposable
operator-PC v383 extraction with the smoke add-on first proved image OCR plus a
copied-DB DepartmentYearly write via `extraction_method="ocr_tesseract"`.
The same OCR image/write path has now been repeated on v384 with core SHA256
`2707def6337f3f35c63c9933a1805271dcf75d8bf7d8ece27c09ba8de72d31c0`, returning
`ocr_full_text="V384 OCR WRITE SMOKE 2026"`, `ocr_avg_confidence=0.95`, one
copied-DB `DepartmentYearly` row, three `manual_entry` audit rows, and zero
matching real-runtime marker rows. Post-v383 source adds code-level
coverage that image-PDF ingest uses the Tesseract TSV wrapper and stores
`ocr_tesseract` confidence breakdowns on both `DepartmentYearly` and
`SupportRecipient` rows. The latest operator-PC setup and read-only UI evidence
is now v384: v384 was transferred to Windows, hash-checked, set up in
disposable probes, diagnosed, served through Streamlit, rendered in a tunneled
browser, clicked through the five non-mutating quick navigation buttons, and
showed the FY2026 Excel workbook-generation button disabled for empty current
data. v384 is now the latest package with package-local `eidp db-backup`,
Windows environment / Task Scheduler capture, URL-candidate reject,
audit-outbox browser flush, `③ 年度判定・修正` fiscal-year override,
SupportRecipient package ingest, and `PDF確認・手入力` manual-entry browser save
proof on disposable copied databases. v384 also has a sandboxed 5-site Saitama
backend bootstrap smoke that exercises official artifact download,
official-index SchoolSite writes, strict PDF discovery, ingest, and status
rebuild without mutating the real runtime DB.
Stage 6 operator workflow evidence still remains incomplete, as listed below.

## Objective Checklist

| Requirement | Current evidence | Status |
| --- | --- | --- |
| 47 prefecture official indexes seed school public URLs | v342 verifier: `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`, `prefecture_seed_school_rows_total=2148`; Windows v384 sandboxed Saitama 5-site backend smoke downloaded the current official artifact (`saitama.pdf` plus `.url` sidecar), added `51` `SchoolSite` rows with `prefecture_aggregator`, and left the real runtime DB at `0` `SchoolSite` marker rows; Windows v342 broader Saitama run also downloaded the official artifact and added `51` `SchoolSite` rows from `58` extracted / `51` matched rows | Evidence present |
| Discover and download current target-FY PDFs in strict mode | v380 package verifier clean by default; packaged discovery gold-set `44` entries / `10` strict target-year successes / `17` publication-lag cases; v384 sandboxed Saitama 5-site backend smoke crawled `5`, downloaded `0` strict FY2026 target PDFs, produced `2084` discovery evidence lines, processed `0` PDFs, rebuilt `2418` status rows, and reported `operator_reviewable_count=5`, `operator_reviewable_yield_pct=0.2`, `target_pdf_auto_yield_pct=0.0`, `excel_ready=0`, `ship_gate_status=below_gate`, one RCA batch file with `5` items / `5` total candidates, and real runtime counts `school_site=0`, `review_item=0`, `document=0`, `status_rows=2418`; v375 fixes the heading/update-date fiscal-year context edge and adds a 尚美 historical-support-form ordering case where the latest public R7 target form stays visible for FY2026 publication-lag handling; v374 adds a code-level guard that current-year syllabus/curriculum PDFs do not outrank the previous-year target confirmation form in Aichi-style publication-lag pages; source-side 聖十字 replay crawled `1`, found `1`, downloaded `1`, and gold-set evidence replay matched the accepted target PDF exactly; source-side 更生 replay crawled `1`, found `1`, downloaded `1`, and gold-set evidence replay matched the accepted target PDF exactly; source-side 中央情報 replay crawled `1`, found `1`, downloaded `1`, and gold-set evidence replay matched the accepted target PDF exactly; source-side 君津 replay crawled `1`, found `1`, downloaded `1`, and gold-set evidence replay matched the accepted target PDF exactly; manual-web / official-index-linked 愛北 evidence records a support-system news page with `令和8年度` context linking `youshiki2-r7.pdf` as the target confirmation form; manual-web / official-index-linked 愛生会 evidence records a support page where the latest target-form PDF is still `令和7年9月公表` and the adjacent subject-list PDF must not be treated as the target form; manual-web / official-index-linked あいち福祉医療 evidence records a public-documents page where the `2026年度` section contains syllabus PDFs but the latest target-form PDF remains `2025年度`; manual-web / official-index-linked 尚美 evidence records a public-info page where the historical support-form list currently runs through R7/FY2025 and the latest target form must remain publication-lag evidence; manual-web / official-index-linked 中央動物 evidence records a disclosure page where R8 non-target operation-plan / professional-practice PDFs coexist with a support-system `申請書様式第2号` link still labeled `2025年度`; manual-web / official-index-linked 浜松工科 evidence records an official Shizuoka index route to a WordPress disclosure page whose `令和８年度 様式第２号` anchor supplies target-FY evidence for a PDF body that contains the school name, `様式第２号`, and `修学支援` but not the fiscal-year string; manual-web / official-index-linked 長野県公衆衛生 evidence records a prefecture-hosted support page whose latest public target-form PDF is still under the `令和７年度` section and must remain publication-lag evidence; v375 additionally preserves preceding heading-year context without crossing intervening non-year blocks or treating update dates as fiscal-year evidence; manual-web / official-index-linked 岩手医科大学医療専門学校 evidence records a dense Wix page where the target confirmation-form section is still `令和７年度` even though a later syllabus section has `令和8年度`; current Tokyo Anime HTML probe ignores the commented-out old `07_study_support_application.pdf` link while keeping visible confirmation-form links; Windows v342 Saitama 50-site run crawled `50` official-index sites, found candidates on `49`, downloaded `0`, processed `0`, and produced `0` Excel-ready schools after removing false-positive prefecture-index year fill; Windows v342 Tokyo 30-site probe found candidates on all `30` sites and downloaded `0`; a source-side v348 Tokyo 20-site repeat crawled `20`, found candidates on all `20`, downloaded `0`, and reproduced the same publication-lag / stale-year / no-year target-form distribution; Windows v342 evidence proves Kanto/Iruma context fixes without accepting old-year PDFs as current-FY success | Mechanically proven, strict yield still failing at workload scale |
| Exclude stale-year fallback from auto-success | Ship gate uses operator-reviewable coverage, while strict auto-yield remains diagnostic; v380 package gold-set includes `17` publication-lag cases; Windows v333/v339/v340 evidence records prior false-success or stale-year URLs as `target_fiscal_year_not_detected` / `fiscal_year_mismatch:*` instead of `accepted_downloaded`; malformed raw URLs are recorded as `unsafe_url` instead of aborting the batch | Evidence present |
| Extract with pdfplumber/PyMuPDF/Tesseract and write only confidence >= 0.70 rows | Unit/package gates cover OCR runtime presence and confidence contracts; Windows v340 Saitama 50-site run produced no strict target PDFs, so no PDF-derived yearly rows were written; this avoids v332's false-positive `18` current rows. v383 adds package-verifier enforcement for the OCR add-on TSV config and a disposable operator-PC image smoke. v384 repeats the OCR image/write proof on the latest core package: Tesseract returned `ocr_full_text="V384 OCR WRITE SMOKE 2026"` with `ocr_conf_values=[93,94,96,96,96]` and `ocr_avg_confidence=0.95`; `save_manual_entries` wrote one copied-DB `DepartmentYearly` row with `extraction_method="ocr_tesseract"`, `extraction_confidence=0.95`, and `verified=true`, promoted the document to `ingested`, emitted three `manual_entry` audit rows, and left the real runtime DB with `0` matching marker rows. Post-v383 source coverage proves image-PDF ingest uses the Tesseract TSV wrapper and records `ocr_tesseract` confidence breakdowns on both `DepartmentYearly` and `SupportRecipient` rows when OCR TSV confidence is present | Mechanically proven for OCR runtime/TSV parsing and copied-DB DepartmentYearly write on v384, plus code-level SupportRecipient OCR confidence propagation; no current strict target-form OCR data |
| Append-only DepartmentYearly / SupportRecipient writes | Fresh full unit suite passed; source audits and targeted tests cover demote-plus-new-revision paths in ingest, manual entry, and fiscal-year override; Windows v384 `PDF確認・手入力` browser save smoke inserted one manual `DepartmentYearly` revision with `document_id=1`, `fiscal_year=2026`, `revision=1`, `is_current=1`, `extraction_method="manual"`, `extraction_confidence=1`, and `verified=1` in a disposable copied DB, promoted the document from `parse_failed` to `ingested`, emitted three `manual_entry` audit rows, and verified the real runtime DB had `0` matching document/department/yearly/audit rows. The same smoke confirmed this UI path does not write SupportRecipient rows (`support_recipient_rows_for_doc=0`). Windows v384 `③ 年度判定・修正` browser write smoke moved one seeded FY2025 ingested document to FY2026, demoted the FY2025 current `DepartmentYearly`, `SupportRecipient`, and `SchoolYearStatus` rows plus the pre-existing FY2026 target `DepartmentYearly` row, inserted new FY2026 current `DepartmentYearly`, `SupportRecipient`, and `SchoolYearStatus` rows, set `Document.fiscal_year=2026` and `fiscal_year_override=2026`, emitted four `fiscal_year_override` audit rows, and verified the real runtime DB had `0` matching document/school/department/audit rows. Windows v384 package-local backend ingest smoke then seeded two FY2026 target documents in a copied DB, monkeypatched the package parser boundary to return deterministic SupportRecipient annotations, called `ingest_document` twice, and verified two SupportRecipient rows: revision `1` demoted to `is_current=false` with `annual_total=100`, `grand_total=100`, and `extraction_confidence=0.94`; revision `2` current with `annual_total=120`, `grand_total=120`, and `extraction_confidence=1.0`; the real runtime DB had `0` matching documents, schools, and support-recipient rows. | DepartmentYearly Win UI E2E proven on v384; fiscal-year override Win UI E2E proven on v384; SupportRecipient Win package backend append-only proven on v384 |
| Excel template output | v384 FY2026 Excel preview correctly keeps workbook generation disabled when current-year transcribed rows are `0`; v384 retroactive FY2025/R7 browser smoke generated the in-memory workbook and downloaded `eidp_master.xlsx` with size `3,728,651` bytes after showing `抽出済み学校 2031` and `Excel対象行 7150`; the downloaded workbook opened with sheets `採録状況`, `対象比率`, `学科別`, and `在籍のみ抜粋`, and `openpyxl` reported row counts `2419`, `10023`, `9721`, and `9721` including headers; v342 package verifier also includes Excel/export contracts and centralized confidence threshold contract | Partially proven for current FY, browser download proven for R7 retroactive on latest v384 |
| ManualActionLog audit for operator actions | v384 sandboxed URL-candidate reject browser write smoke created one `url_candidate_rejected` audit row in a disposable copied database, resolved the `ReviewItem` as rejected, created no `SchoolSite` row, and verified the real runtime DB was not mutated; v384 sandboxed audit-outbox browser flush smoke exported one seeded `stage6_v384_ui_audit_flush_smoke` row to JSONL, stamped `jsonl_exported_at`, cleared pending count to `0`, and verified the real runtime DB was not mutated; v384 `PDF確認・手入力` browser save smoke emitted three `manual_entry` audit rows for `department`, `department_yearly`, and `document`; v384 `③ 年度判定・修正` browser write smoke emitted four `fiscal_year_override` audit rows for `department_yearly`, `support_recipient`, `school_year_status`, and `document`; v342 package verifier also includes audit contracts and outbox checks | Browser operator-action audit proven for URL-candidate, audit flush, manual-entry, and fiscal-year override paths |
| ZIP distribution, double-click setup, browser UI offline operation | v393 ZIP verifies clean on macOS packaging gate, includes root-level `EIDP-stage6-evidence.bat` and `EIDP-stage6-recovery.bat`, includes `scripts/collect_stage6_evidence.py`, `scripts\collect_stage6_evidence.bat`, `scripts/stage6_recovery_check.py`, and `scripts\stage6_recovery_check.bat`, packages the Windows-local Stage 6 recovery runbook path, makes the operator E2E template require recovery evidence and optional `logs\stage6-evidence-*.zip` attachment, and packages a read-only evidence-bundle helper that excludes `data/eidp.sqlite3`, WAL/SHM files, PDFs, runtime, and wheelhouse; the latest disposable operator-PC setup proof remains v384: SHA256 sidecar matched, `scripts\first_setup.bat` returned `setup_rc=0`, after-setup validation returned `ok=true`, `school_count=2418`, `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`, and `EIDP-diagnose.bat` returned `diagnose_rc=0`; the proof restored the original v380 `EIDP Weekly Run` scheduled task after setup. v384 also has environment capture, Task Scheduler query / restore proof, package-local backup CLI proof, UI service, initial browser-render, read-only quick-navigation, FY2026 Excel disabled-state, retroactive FY2025/R7 Excel preview/download proof, URL-candidate reject proof, audit-outbox flush proof, fiscal-year override proof, and `PDF確認・手入力` manual-entry browser save proof: disposable v384 Streamlit services returned HTTP `200 OK` on `/_stcore/health`, the tunneled browser rendered title `EIDP Operator Console`, default page `① 学校別タスク`, target `2026年度（令和8年度）`, build `75732b0`, `対象年度 要対応 2418`, `Excel出力可 0/2418 校`, and console errors/warnings `0`; a follow-up v384 probe clicked the five non-mutating quick navigation buttons, rendered `PDF確認・手入力`, `対象年度の判定・修正`, `Excel プレビュー`, `設定`, and `① 学校別タスク`, and confirmed the FY2026 Excel workbook-generation button stayed disabled for empty current data; a separate process-scoped R7 v384 probe generated and downloaded `eidp_master.xlsx` through the browser; v384 disposable copied-DB probes rejected one URL candidate, flushed one audit-outbox row, moved one fiscal-year override fixture, saved a manual-entry row, and proved SupportRecipient append-only ingest, leaving the real runtime DB unchanged. A v384 backup/env probe captured Windows 11 Pro build `26200`, host `JUNMING`, `13th Gen Intel(R) Core(TM) i9-13900HK`, `32453` MB visible RAM, `C:` free `964.4` GB, `EIDP Weekly Run` task state `Ready`, v384 `db_backup_rc=0`, backup `integrity=ok`, `sqlite_objects=35`, `school_count=2418`, and `school_year_status_count=17696`; cleanup removed probes and restored the scheduled task to v380. Full Stage 6 operator-action click-through remains unverified | Backend Win setup/diagnostics, app-server startup, initial browser render, read-only navigation, Excel preview disabled-state, R7 Excel download, URL-candidate write, audit-outbox flush, fiscal-year override write, manual-entry write, SupportRecipient ingest, environment capture, Task Scheduler query / restore, backup CLI proof, and Stage 6 evidence-bundle package proof present; full operator workflow still missing |
| Shipping threshold: operator-reviewable coverage sufficient for operator manual work <=30%, with strict Excel readiness retained as diagnostic output | v358 `ship-readiness` now reports `ok_operator_review` separately from `ok_strict`; Windows v342 50-site diagnostics report `target_pdf_auto_yield_pct=0.0`, `operator_reviewable_yield_pct=1.9`, `excel_ready=0`, `ship_gate_status=below_gate`, and `validate_after_bootstrap_ship_gate_rc=1` | Failing on latest Windows evidence |

## Current Non-Windows Evidence

Runbooks: `docs/runbooks/eidp-non-windows-release-gates.md`;
`docs/runbooks/eidp-retroactive-fy-validation.md`.

Latest v393 package-verifier commands:

- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v393.zip --latest-alias`
  -> wrote `dist/eidp-windows-v393.zip` and refreshed `dist/eidp-windows.zip`;
  both have SHA256
  `3ab58cca9494940ac85c7018aed2faeebc20d1784370d7203b8642b5623a32e8`.
- `uv run python scripts/verify_windows_distribution.py --json dist/eidp-windows-v393.zip`
  -> `ok=true`, commit `a992ef6f37589f26db640c602d790711e5f740dd`,
  `build_dirty=false`, `entry_count=3070`, `wheel_count=78`,
  root-level `EIDP-stage6-evidence.bat` and `EIDP-stage6-recovery.bat`, and
  `scripts/collect_stage6_evidence.py`, `scripts\collect_stage6_evidence.bat`,
  `scripts/stage6_recovery_check.py`, plus `scripts\stage6_recovery_check.bat`
  included in the core ZIP contract; the packaged operator E2E template also
  requires `stage6_recovery_rc`, scheduled-task recovery evidence fields, and
  optional `logs\stage6-evidence-*.zip` attachment.
- `uv run python scripts/build_ocr_addon_zip.py --tesseract-dir _temp/ocr-addon-src/7z-extract --tessdata-dir /opt/homebrew/share/tessdata --out-zip dist/eidp-ocr-addon-windows-v383-smoke.zip`
  built an add-on from UB Mannheim Windows Tesseract `v5.4.0.20240606` plus
  local `jpn.traineddata` and the required `tessdata/configs/tsv` file;
  package verifier reported `OK ocr-addon`, SHA256
  `bd1e2c96dcd7ac17562d44c3338fbf8da0ac21a1b1e60386073c730775e8d853`,
  `entry_count=267`, and `manifest_files=266`.
- `uv run python scripts/verify_windows_distribution.py --json dist/eidp-windows.zip --ocr-addon dist/eidp-ocr-addon-windows-v383-smoke.zip --playwright-addon dist/eidp-playwright-addon-windows-v106.zip`
  -> `OK core`, `OK ocr-addon`, and `OK playwright-addon`, with matching v393
  core SHA256, `44` packaged discovery gold-set entries, `17`
  publication-lag cases, `47` prefecture seeds,
  `undemonstrated_pattern_sources=[]`, Stage 6 evidence/recovery roots, and
  the Stage 6 evidence/recovery helper scripts; the packaged Windows runbook
  includes `db-backup --output $dbBackup`, `VACUUM INTO`,
  `PRAGMA wal_checkpoint(TRUNCATE)`, and `logs\stage6-evidence-*.zip`.
- Windows v381 runtime-only OCR RAM probe:
  disposable extraction under
  `C:\Users\cyo20\EIDP-v381-da29fee-runtime-probe` returned
  `{"app_root": "C:\\Users\\cyo20\\EIDP-v381-da29fee-runtime-probe", "cpu_count": 20, "free_ram_mb": 16242, "ocr_auto_enable": true}`;
  the probe directory and uploaded v381 ZIP/sidecar were removed after capture.
- Windows v382 OCR runtime gate negative probe:
  disposable extraction under
  `C:\Users\cyo20\EIDP-v382-cc739c8-ocr-runtime-probe` ran
  `runtime\python\python.exe scripts\validate_windows_install.py . --require-ocr-runtime --json`;
  it returned `ok=false`, build commit
  `cc739c8704e45e37928a4ac55fa006766e5012dc`, `build_dirty=false`, and the
  expected missing-file errors for `ocr-addon/tesseract/tesseract.exe` and
  `ocr-addon/tessdata/jpn.traineddata`; the probe directory and uploaded v382
  ZIP/sidecar were removed after capture.
- Windows v384 OCR image plus copied-DB write proof:
  disposable extraction under
  `C:\Users\cyo20\EIDP-v384-75732b0-ocr-write-sandbox` with the v383 smoke OCR add-on
  generated `data\ocr-write-smoke.png`, executed the packaged Tesseract binary
  through `run_tesseract_on_image(...)`, and returned
  `ocr_full_text="V384 OCR WRITE SMOKE 2026"`, `ocr_usable_word_count=5`,
  `ocr_conf_values=[93,94,96,96,96]`, and `ocr_avg_confidence=0.95`.
  The same smoke copied the real v380 DB with
  `eidp db-backup`, seeded a marker document in the copied DB, and called
  `save_manual_entries(..., method="ocr_tesseract")`; it wrote one
  `DepartmentYearly` row with `extraction_confidence=0.95` and `verified=true`,
  promoted the document from `ocr_pending` to `ingested`, and emitted three
  `manual_entry` audit rows for `department`, `department_yearly`, and
  `document`. A follow-up query against the real v380 runtime DB returned
  `0` matching marker documents, departments, and audit rows. The disposable
  v384 probe directory and uploaded ZIPs were removed after capture, and the
  scheduled task was confirmed `Ready` with action
  `C:\Users\cyo20\EIDP-v380-f6a5e6d\scripts\weekly_run.bat`.
- Windows v384 OCR runtime gate positive probe:
  disposable extraction under
  `C:\Users\cyo20\EIDP-v384-75732b0-ocr-runtime-probe` expanded
  `dist/eidp-windows-v384.zip` plus
  `dist/eidp-ocr-addon-windows-v383-smoke.zip` after confirming the v384 core
  SHA256 sidecar. It ran
  `runtime\python\python.exe scripts\validate_windows_install.py . --require-ocr-runtime --json`
  and returned `ok=true`, build commit
  `75732b057a115afcebe35f9a40b831fac0ffa6f6`, `build_dirty=false`,
  `wheel_count=78`, `ocr_tessdata_dir` under the disposable extraction,
  packaged Tesseract version `tesseract v5.4.0.20240606`, and language support
  including `jpn` and `jpn_vert`.
- Windows v384 setup and diagnostics proof:
  disposable extraction under
  `C:\Users\cyo20\EIDP-v384-75732b0-setup-probe` expanded
  `dist/eidp-windows-v384.zip` after confirming the SHA256 sidecar. It ran
  `scripts\first_setup.bat` with `setup_rc=0`; then
  `.\.venv\Scripts\python.exe scripts\validate_windows_install.py . --after-setup --json`
  returned `ok=true`, build commit
  `75732b057a115afcebe35f9a40b831fac0ffa6f6`, `build_dirty=false`,
  `wheel_count=78`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, and `sqlite_integrity_check=ok`.
  `EIDP-diagnose.bat` returned `diagnose_rc=0`; the latest diagnostics file was
  `logs\diagnostics-20260514-020156.txt` and included
  `validate_after_setup_rc=0`, FY2026 `operator_reviewable_schools=0`,
  FY2026 `excel_ready_schools=0`, FY2025
  `is_retroactive_fiscal_year=true`, and `retroactive_ship_readiness_rc=0`.
  During setup, the harness observed `task_registered_to_v384=true`, then
  restored the pre-existing `EIDP Weekly Run` scheduled task; the restored task
  contains `EIDP-v380-f6a5e6d` and does not contain
  `EIDP-v384-75732b0-setup-probe`.
- Windows v384 UI service and initial browser render proof:
  disposable extraction under
  `C:\Users\cyo20\EIDP-v384-75732b0-ui-probe` expanded and set up the same v384
  core ZIP, then started Streamlit on Windows `127.0.0.1:8501`. The remote
  service returned `health_status=200` and `health_body=ok`; a local SSH tunnel
  `127.0.0.1:18501 -> Windows 127.0.0.1:8501` also returned HTTP `200 OK` from
  `/_stcore/health`. Browser/Playwright rendered
  `http://127.0.0.1:18501/` with page title `EIDP Operator Console`; the
  accessibility snapshot showed `今週のやること`, `① 学校別タスク`,
  `対象年度: 2026年度（令和8年度）`, build
  `75732b0 / branch: sprint8-handoff-finalize`, `対象年度 要対応 2418`,
  `Excel出力可 0/2418 校`, and the initial acquisition warning. Captured console
  messages reported `Total messages: 0 (Errors: 0, Warnings: 0)`. Cleanup
  stopped the service, removed the v384 UI probe and upload files, confirmed
  `port_8501_listeners=0`, and confirmed the scheduled task still contains
  `EIDP-v380-f6a5e6d` and does not contain
  `EIDP-v384-75732b0-ui-probe`.
- Windows v384 read-only quick-navigation proof:
  a second disposable extraction under
  `C:\Users\cyo20\EIDP-v384-75732b0-ui-nav-probe` expanded and set up the same
  v384 core ZIP, started Streamlit on Windows `127.0.0.1:8501`, and used the
  same local SSH tunnel. Browser/Playwright clicked only the five non-mutating
  quick navigation buttons: `PDF確認・手入力`, `③ 年度判定・修正`,
  `④ Excel プレビュー`, `⑤ 設定（年度・OCR・API）`, and back to
  `① 学校別タスク`. The snapshots rendered `PDF確認・手入力`,
  `対象年度の判定・修正`, `Excel プレビュー` with
  `対象年度: 2026年度（令和8年度） / 対象範囲: 専門学校`, `設定` with the
  `バージョン`, `和暦 alias`, `OCR`, and `外部 API` sections, and the task
  page again. The Excel page's workbook-generation button remained disabled for
  empty FY2026 data, and the settings save button was not clicked. Incremental
  console capture reported `Total messages: 5 (Errors: 0, Warnings: 0)`.
  Cleanup stopped the service, removed the v384 UI-nav probe and upload files,
  confirmed `port_8501_listeners=0`, and confirmed the scheduled task still
  contains `EIDP-v380-f6a5e6d` and does not contain
  `EIDP-v384-75732b0-ui-nav-probe`.
- Windows v384 retroactive FY2025 Excel preview/download smoke:
  a third disposable extraction under
  `C:\Users\cyo20\EIDP-v384-75732b0-r7-excel-probe` expanded and set up the
  same v384 core ZIP. Streamlit was started with process-scoped
  `EIDP_TARGET_FISCAL_YEAR=2025` and no `.env` write, then opened through the
  SSH tunnel. The `④ Excel プレビュー` page showed
  `対象年度: 2025年度（令和7年度）`, `抽出済み学校 2031`, and `Excel対象行 7150`.
  The `プレビュー workbook を生成` button was enabled, generated the in-memory
  workbook, and exposed `Excel ダウンロード`; the browser download saved
  `eidp_master.xlsx` with size `3,728,651` bytes. The downloaded workbook
  opened with sheets `採録状況`, `対象比率`, `学科別`, and `在籍のみ抜粋`;
  `openpyxl` reported row counts `2419`, `10023`, `9721`, and `9721`
  including headers. Streamlit stdout recorded export counts
  `採録状況=2418`, `対象比率=10022`, `学科別=9719`, and `在籍のみ抜粋=9719`.
  The downloaded workbook and Playwright snapshots were removed after
  verification. Cleanup stopped the service, removed the v384 R7 Excel probe
  and upload files, confirmed no `8501` listener remained, and confirmed the
  scheduled task still points at `EIDP-v380-f6a5e6d`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v379.zip --require-demonstrated-discovery-patterns`
  now fails under the current verifier because v379 predates the
  `db-backup --output $dbBackup` runbook contract.

Latest Windows setup and backup-smoke commands:

- Windows v384 environment, Task Scheduler, and `db-backup` smoke:
  a disposable
  `C:\Users\cyo20\EIDP-v384-75732b0-backup-env-sandbox` expanded the v384
  core ZIP after confirming SHA256
  `2707def6337f3f35c63c9933a1805271dcf75d8bf7d8ece27c09ba8de72d31c0`.
  Environment capture reported host `JUNMING`, `Microsoft Windows 11 Pro`
  version `10.0.26200` build `26200`, `AMD64`, culture/UI culture `zh-CN`,
  timezone `Tokyo Standard Time`, CPU `13th Gen Intel(R) Core(TM) i9-13900HK`
  with `14` cores / `20` logical processors, `32453` MB visible RAM, and
  `C:` size `1888.7` GB / free `964.4` GB. `scripts\first_setup.bat` returned
  `setup_rc=0`; the task created by setup pointed at
  `"C:\Users\cyo20\EIDP-v384-75732b0-backup-env-sandbox\scripts\weekly_run.bat"`
  with state `Ready`, next run `05/18/2026 02:00:00`, last run
  `05/11/2026 02:00:00`, and last result `0`. The harness restored the task
  to `C:\Users\cyo20\EIDP-v380-f6a5e6d\scripts\weekly_run.bat`. The v384
  package-local command
  `.\.venv\Scripts\python.exe -m eidp.cli db-backup --output data\eidp-v384-backup-smoke.sqlite3`
  returned `db_backup_rc=0`; verification opened the backup and reported
  `backup_size=9015296`, `integrity=ok`, `sqlite_objects=35`,
  `school_count=2418`, and `school_year_status_count=17696`. Cleanup removed
  the sandbox, uploaded ZIP/sidecar, and verify script (`remaining=false` for
  all tracked probe paths).
- Windows v380 package transfer and extraction:
  transferred `dist/eidp-windows-v380.zip` and its sidecar to
  `C:\Users\cyo20\EIDP-transfer`; Windows SHA256 matched
  `1fef8d468ba2e7d882f7a3a774ccbbf071d1e1ee362ae62b8c4e458c576e5361`;
  expanded into `C:\Users\cyo20\EIDP-v380-f6a5e6d`. The packaged
  `BUILD_INFO.json` records commit
  `f6a5e6d46db7b0b836b18399e5b401362575c38d`, branch
  `sprint8-handoff-finalize`, and `git_dirty=false`.
- Windows v380 setup:
  `EIDP-setup.bat` completed, imported the master workbook, and rebuilt
  school-year tasks for FY2026 with `rebuilt=2418` and `excel_ready=0`.
  The package-local validator reported `OK install`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`,
  required tables present, `document_unique_indexes` including
  `uq_document_file_hash`, and `wheel_count=78`.
- Windows v380 after-setup validator:
  `runtime\python\python.exe scripts\validate_windows_install.py . --after-setup --json`
  returned `ok=true`, no errors or warnings, the same v380 build commit,
  `master_xlsx_present=true`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`, and all
  required SQLite tables.
- Windows v380 diagnostics:
  `EIDP-diagnose.bat` wrote
  `logs\diagnostics-20260513-231923.txt`. FY2026 readiness remained below gate
  with `ship_readiness_rc=1`, `strict_target_pdf_schools=0`,
  `operator_reviewable_schools=0`, `excel_ready_schools=0`, and
  `estimated_manual_workload_rate=1.0`. The retroactive FY2025 section recorded
  `is_retroactive_fiscal_year=true`, `extracted_schools=2031`,
  `extracted_rate=0.84`, `retroactive_fiscal_year=2025`, and
  `retroactive_ship_readiness_rc=0`. Because this was a fresh setup without
  discovery/bootstrap progress, both FY2026 and FY2025 operator-reviewable
  readiness remained `0`.
- Windows v380 `db-backup` smoke:
  `.\.venv\Scripts\python.exe -m eidp.cli db-backup --output data\eidp-backup-smoke.sqlite3`
  wrote a package-local backup; a Python SQLite check opened that backup and
  reported `backup_objects=35` and `integrity=ok`; the temporary smoke backup
  was removed afterward (`backup_removed=True`).
- Windows v380 UI service health smoke:
  a PowerShell harness started Streamlit from
  `C:\Users\cyo20\EIDP-v380-f6a5e6d` on `127.0.0.1:8501`,
  received `/_stcore/health` as `status=200 body=ok`, reported
  `Streamlit, version 1.57.0`, and then stopped the process. The stdout tail
  included `URL: http://127.0.0.1:8501`; stderr recorded
  `Uvicorn server started on 127.0.0.1:8501`. A follow-up process check
  returned `remaining_streamlit_processes=0` for v380. This proves app-server
  health only; browser rendering, navigation, and operator-action click-through
  still require separate evidence.
- Windows v380 browser render smoke:
  with remote Streamlit held open in the same SSH session as the tunnel,
  `ssh -o ClearAllForwardings=no -o ExitOnForwardFailure=yes
  -L 127.0.0.1:18501:127.0.0.1:8501 win ...` exposed the Windows UI to the
  Mac. The explicit `ClearAllForwardings=no` override is required because the
  local `Host win` SSH config clears command-line forwards by default. Local
  `curl http://127.0.0.1:18501/_stcore/health` returned `ok`; Playwright
  rendered `http://127.0.0.1:18501/` with title `EIDP Operator Console`, page
  heading `① 学校別タスク`, target year `2026年度（令和8年度）`, build
  `f6a5e6d`, `対象校 2418`, `Excel出力可 0/2418 校`, `URLなし 2418`, and
  the initial acquisition warning. This proves initial browser rendering on
  the current v380 package.
- Windows v380 read-only Excel preview smoke:
  the same tunneled Playwright session clicked only the non-mutating sidebar
  button `④ Excel プレビュー`. The page rendered with heading
  `Excel プレビュー`, `対象年度: 2026年度（令和8年度） / 対象範囲: 専門学校`,
  a warning that current-year transcribed rows are `0`, and the
  `プレビュー workbook を生成` button present but disabled, preventing old-year
  or empty workbook output. The temporary Playwright screenshot
  `eidp-v380-excel-preview.png` and generated snapshot files were removed
  afterward. The local tunnel was stopped, and a follow-up Windows process
  cleanup reported `streamlit_after_cleanup=0` for v380.
- Windows v380 retroactive FY2025 Excel preview/download smoke:
  the same v380 package was started with process-scoped
  `EIDP_TARGET_FISCAL_YEAR=2025` (no `.env` write) and opened through the SSH
  tunnel. The `④ Excel プレビュー` page showed `対象年度: 2025年度`,
  `抽出済み学校 2031`, and `Excel対象行 7150`. The
  `プレビュー workbook を生成` button was enabled, generated the in-memory
  workbook, and exposed `Excel ダウンロード`; the browser download suggested
  `eidp_master.xlsx` and saved
  `_temp/eidp-v380-r7-retroactive-download.xlsx` with size `3,728,651` bytes.
  Browser warning/error/pageerror events were empty. The Streamlit stdout
  recorded sheet exports `採録状況=2418`, `対象比率=10022`, `学科別=9719`,
  and `在籍のみ抜粋=9719`. The downloaded workbook, Playwright download copy,
  and temporary Streamlit launcher were removed afterward; cleanup reported
  `run_script_exists_after_cleanup=False` and
  `remaining_v380_streamlit_processes=0`, and the local tunnel had no listener.
- Windows v380 read-only quick-navigation click-through:
  the same tunnel pattern was rerun against v380 and Playwright clicked only
  the five non-mutating quick navigation buttons:
  `① 学校別タスク`, `② PDF確認・手入力`, `③ 年度判定・修正`,
  `④ Excel プレビュー`, and `⑤ 設定（年度・OCR・API）`. Each page rendered
  the expected heading or key text with no missing assertions:
  `① 学校別タスク` with `週次URL/PDF再取得` / `次に進める作業`,
  `PDF確認・手入力`, `対象年度の判定・修正`, `Excel プレビュー` with
  `プレビュー workbook を生成`, and `設定` with `バージョン` / `OCR` /
  `外部 API`. The script did not click acquisition, save, export, flush, or
  any data-mutating action. Captured browser console output contained only
  Chrome `VERBOSE` DOM messages about password fields, not warning/error or
  page-error events. The local tunnel was stopped, and a follow-up Windows
  process cleanup reported `streamlit_after_cleanup=0` for v380.
- Windows v384 browser UI URL-candidate review write smoke:
  a disposable `C:\Users\cyo20\EIDP-v384-75732b0-url-review-sandbox` was
  created from the v384 core ZIP and a copied runtime DB produced by the v380
  package-local `eidp db-backup` command. It seeded one pending
  `url_candidate` review item for `日本工学院専門学校` with candidate URL
  `https://example.com/eidp-v384-url-candidate-smoke`. The v384 Streamlit UI
  ran from the disposable extraction, and the tunneled browser opened
  `詳細 operator` -> `URL候補レビュー`, verified `確認待ち 1 件`, entered
  reject reason `v384 UI reject smoke`, clicked `却下`, and observed
  `確認待ちのURL候補はありません。`. Direct post-UI DB verification reported
  the marker review item as `status=resolved`, `resolution=rejected`,
  `notes="v384 UI reject smoke"`, one `ManualActionLog` row with
  `action_type="url_candidate_rejected"`, `target_table="review_item"`, and
  `target_id=1`, and zero `SchoolSite` rows for the candidate URL. The real
  v380 runtime DB reported zero matching review-item, audit, and school-site
  marker rows. Cleanup removed the v384 sandbox and uploaded probe files and
  confirmed `port_8501_listeners=0`.
- Windows v380 browser UI URL-candidate review write smoke:
  a disposable `C:\Users\cyo20\EIDP-v380-url-review-sandbox` was created from
  the v380 runtime database through the package-local `eidp db-backup`
  command. It seeded one pending `url_candidate` review item for
  `日本工学院専門学校` with candidate URL
  `https://example.com/eidp-v380-url-candidate-smoke`. The v380 Streamlit UI
  ran with `EIDP_APP_ROOT` pointed at that sandbox, and the tunneled browser
  opened `詳細 operator` -> `URL候補レビュー`, verified `確認待ち 1 件`,
  entered reject reason `v380 UI reject smoke`, clicked `却下`, and then
  observed `確認待ちのURL候補はありません。` with no warning/error/pageerror
  events. Direct post-UI DB verification reported `review_items=1`,
  `pending_items=0`, `resolved_rejected_items=1`, `audit_rows=1`,
  `audit_action_types=["url_candidate_rejected"]`, and
  `audit_reasons=["v380 UI reject smoke"]`; the real v380 runtime DB reported
  `runtime_matching_audit_rows=0`. The local tunnel was stopped, residual
  sandbox Streamlit processes were removed by exact PID/command-line match, and
  `sandbox_exists_after_cleanup=False` / `remaining_matching_processes=0`
  confirmed cleanup.
- Windows v384 browser UI audit-outbox flush smoke:
  a disposable `C:\Users\cyo20\EIDP-v384-75732b0-audit-sandbox` was created
  from the v384 core ZIP and a copied runtime DB produced by the v380
  package-local `eidp db-backup` command. Existing copied-runtime pending
  audit rows were stamped as already exported, then the seed inserted one
  unexported `stage6_v384_ui_audit_flush_smoke` `ManualActionLog` row with
  actor `codex-v384-ui-smoke` and reason `v384 UI audit flush smoke`. The
  v384 Streamlit UI ran from the disposable extraction, and the tunneled
  browser opened `詳細 operator` -> `監査ログ`, verified
  `JSONL outbox 未送信` with pending count `1`, clicked `Outbox を flush`,
  and observed `exported=1 already_present=0 failed=0` with the seeded action
  and actor visible. Direct post-UI DB/JSONL verification reported
  `pending_count=0`, `matching_db_rows=1`,
  `jsonl_exported_at_present=true`, `jsonl_export_error_null=true`,
  `jsonl_path=C:\Users\cyo20\EIDP-v384-75732b0-audit-sandbox\data\audit\manual-actions.jsonl`,
  `matching_outbox_rows=1`, `outbox_lines=1`,
  `outbox_action_types=["stage6_v384_ui_audit_flush_smoke"]`, and
  `outbox_actors=["codex-v384-ui-smoke"]`; the real v380 runtime DB reported
  `matching_db_rows=0` for the same marker. Cleanup removed the v384 sandbox
  and uploaded probe files and confirmed `port_8501_listeners=0`.
- Windows v380 browser UI audit-outbox flush smoke:
  a disposable `C:\Users\cyo20\EIDP-v380-ui-audit-sandbox` was created from
  the v380 runtime database through the package-local `eidp db-backup`
  command. It seeded one unexported
  `stage6_v380_ui_audit_flush_smoke` `ManualActionLog` row with actor
  `codex-v380-ui-smoke` and reason `v380 UI audit flush smoke`. The v380
  Streamlit UI ran with `EIDP_APP_ROOT` pointed at that sandbox, and the
  tunneled browser opened `詳細 operator` -> `監査ログ`, verified
  `JSONL outbox 未送信` with pending count `1`, clicked `Outbox を flush`,
  and observed `exported=1 already_present=0 failed=0` with the seeded action
  and actor visible. Browser warning/error/pageerror events were empty. Direct
  post-UI verification using `settings.data_dir` reported
  `jsonl_path=C:\Users\cyo20\EIDP-v380-ui-audit-sandbox\data\audit\manual-actions.jsonl`,
  `pending=0`, `matching_db_rows=1`, `jsonl_exported_at_present=true`,
  `matching_outbox_rows=1`, `outbox_lines=1`,
  `outbox_action_types=["stage6_v380_ui_audit_flush_smoke"]`, and
  `outbox_actors=["codex-v380-ui-smoke"]`; the real v380 runtime DB reported
  `runtime_matching_db_rows=0`. The local tunnel was stopped, residual sandbox
  Streamlit processes were removed by exact PID/command-line match, and
  `sandbox_exists_after_cleanup=False` / `remaining_matching_processes=0`
  confirmed cleanup.
- Windows v384 browser UI PDF manual-entry save smoke:
  a disposable `C:\Users\cyo20\EIDP-v384-75732b0-manual-entry-sandbox` was
  created from the v384 core ZIP and a copied runtime DB produced by the v380
  package-local `eidp db-backup` command. It seeded one FY2026 `parse_failed`
  document with source URL
  `https://example.com/eidp-v384-manual-entry-smoke.pdf`. The v384 Streamlit
  UI ran from the disposable extraction, and the tunneled browser opened
  `② PDF確認・手入力`, verified `表示 1 / 待機 1 件` with one save-eligible
  queue row for `日本工学院専門学校`, filled one department row
  (`V384手入力学科`, capacity `40`, enrollment `35`, international students
  `2`, graduates `30`, advanced `5`, employed `24`, other `1`, previous
  enrollment `36`, dropouts `1`, dropout rate `0.0278`, duration `2`) with
  reason `v384 UI manual entry smoke`, and submitted `保存`. After the
  Streamlit rerun the page showed no documents for that view. Direct post-UI
  SQLite verification reported the seeded document promoted to `ingested`, one
  `department` row, one `department_yearly` row with `document_id=1`,
  `fiscal_year=2026`, `revision=1`, `is_current=1`,
  `extraction_method="manual"`, `extraction_confidence=1`, `verified=1`, and
  three `manual_entry` audit rows targeting `department`, `department_yearly`,
  and `document`. The same check confirmed `support_recipient_rows_for_doc=0`
  and the real v380 runtime DB reported `0` matching document, department,
  yearly, audit, and support-recipient marker rows. Cleanup removed the v384
  sandbox and uploaded probe files and confirmed `port_8501_listeners=0`.
- Windows v380 browser UI PDF manual-entry save smoke:
  a disposable `C:\Users\cyo20\EIDP-v380-manual-entry-sandbox` was created
  from the v380 runtime database through the package-local `eidp db-backup`
  command. It seeded one FY2026 `parse_failed` document with source URL
  `https://example.com/eidp-v380-manual-entry-smoke.pdf`. The v380 Streamlit
  UI ran with `EIDP_APP_ROOT` pointed at that sandbox, and the tunneled browser
  opened `② PDF確認・手入力`, verified a single save-eligible queue row for
  `日本工学院専門学校`, filled one department row (`V380手入力学科`, capacity
  `40`, enrollment `35`, international students `2`, graduates `30`, advanced
  `5`, employed `24`, other `1`, previous enrollment `36`, dropouts `1`,
  dropout rate `0.0278`, duration `2`) with reason
  `v380 UI manual entry smoke`, and submitted the form. After the Streamlit
  rerun the page showed the queue empty for that view. Direct post-UI DB
  verification reported the seeded document promoted to `ingested`, one new
  `department` row, one `department_yearly` row with `document_id=1`,
  `fiscal_year=2026`, `revision=1`, `is_current=1`, `extraction_method="manual"`,
  `extraction_confidence=1`, `verified=1`, and three `manual_entry` audit rows
  targeting `department`, `department_yearly`, and `document`. The same check
  confirmed `sandbox_support_recipient_smoke_rows=0`, because this UI page does
  not write SupportRecipient records, and the real v380 runtime DB reported
  `runtime_matching_documents=0`, `runtime_matching_departments=0`,
  `runtime_matching_department_yearly=0`, and
  `runtime_matching_manual_actions=0`. The local tunnel was stopped, the
  sandbox was removed, and cleanup reported
  `sandbox_exists_after_cleanup=False`, `port_8501_open=False`, and
  `remaining_matching_processes=0`.
- Windows v384 browser UI fiscal-year override write smoke:
  a disposable
  `C:\Users\cyo20\EIDP-v384-75732b0-fiscal-override-sandbox` was created from
  the v384 core ZIP and a copied runtime DB produced by the v380
  package-local `eidp db-backup`. It seeded one FY2025 `ingested` document
  with source URL
  `https://example.com/eidp-v384-fiscal-override-smoke.pdf`, one current
  FY2025 `DepartmentYearly`, one current FY2025 `SupportRecipient`, one
  current FY2025 `SchoolYearStatus`, and one pre-existing FY2026 current
  `DepartmentYearly` for the same department. The v384 UI opened
  `③ 年度判定・修正`, selected doc#1, kept target `2026`, filled reason
  `v384 UI fiscal override smoke`, and clicked `年度を確定`; the rerun showed
  the candidate changed to
  `2026年度（令和8年度）(修正済み→2026年度（令和8年度）)`. Direct DB verification
  reported `Document.fiscal_year=2026` and `fiscal_year_override=2026`;
  source FY2025 rows were demoted; the pre-existing FY2026 `DepartmentYearly`
  was demoted; a new FY2026 current `DepartmentYearly` revision `2` was
  inserted with `document_id=1`, `capacity=40`, `enrollment=35`, and
  `extraction_method="manual"`; a new FY2026 current `SupportRecipient` was
  inserted with `annual_total=22` and `recipient_rate=0.6286`; a new FY2026
  current `SchoolYearStatus` was inserted with `status="excel_ready"`; and
  four `fiscal_year_override` audit rows targeted `department_yearly`,
  `support_recipient`, `school_year_status`, and `document`. The real v380
  runtime DB reported `matching_documents=0`, `matching_schools=0`,
  `matching_departments=0`, and `matching_audit_rows=0`. Cleanup removed the
  sandbox and upload files, left `port_8501_listeners=0`, and restored the
  scheduled task to v380.
- Windows v380 browser UI fiscal-year override write smoke:
  a disposable `C:\Users\cyo20\EIDP-v380-fiscal-override-sandbox` was created
  from the v380 runtime database through the package-local `eidp db-backup`
  command. It seeded one FY2025 `ingested` document with source URL
  `https://example.com/eidp-v380-fiscal-override-smoke.pdf`, one current
  FY2025 `DepartmentYearly` row, one current FY2025 `SupportRecipient` row,
  one current FY2025 `SchoolYearStatus` row, and one pre-existing FY2026
  current `DepartmentYearly` row for the same department. The v380 Streamlit UI
  ran with `EIDP_APP_ROOT` pointed at that sandbox, and the tunneled browser
  opened `③ 年度判定・修正`, filled reason `v380 UI fiscal override smoke`,
  and clicked `年度を確定`. Direct post-UI DB verification reported
  `Document.fiscal_year=2026` and `fiscal_year_override=2026`; the source
  FY2025 yearly, support-recipient, and school-year-status rows were demoted
  to `is_current=0`; the pre-existing FY2026 `DepartmentYearly` row was
  demoted to `is_current=0`; and new FY2026 current rows were inserted for
  `DepartmentYearly`, `SupportRecipient`, and `SchoolYearStatus`. The same
  check reported four `fiscal_year_override` audit rows targeting
  `department_yearly`, `support_recipient`, `school_year_status`, and
  `document`, all with reason `v380 UI fiscal override smoke`. The real v380
  runtime DB reported `runtime_matching_documents=0`,
  `runtime_matching_departments=0`, and `runtime_matching_audit_rows=0`. The
  local tunnel was stopped, the sandbox was removed, and cleanup observed
  `sandbox_exists=0` and only a remote `TIME_WAIT` connection for port `8501`.
- Windows v384 package-local SupportRecipient ingest append-only smoke:
  a disposable
  `C:\Users\cyo20\EIDP-v384-75732b0-support-recipient-sandbox` was created
  from the v384 core ZIP and a copied runtime DB produced by the v380
  package-local `eidp db-backup`. The smoke seeded two FY2026 target documents
  for `V384 SupportRecipient Smoke School`, pointed `EIDP_APP_ROOT` at the
  sandbox, and called the packaged `ingest_document` path twice while
  monkeypatching only the package parser boundary (`parse_pdf`) to return
  deterministic annotations containing one department row and
  SupportRecipient totals. Both ingest calls returned `support_recipient=1`,
  `support_recipient_current=1`, `yearly_upserted=1`, and `yearly_current=1`.
  Direct SQLite verification found two SupportRecipient rows:
  revision `1` had `annual_total=100`, `grand_total=100`,
  `extraction_confidence=0.94`, and `is_current=false`; revision `2` had
  `annual_total=120`, `grand_total=120`, `extraction_confidence=1.0`, and
  `is_current=true`. The smoke observed `support_recipient_count=2` and
  `current_smoke_support_recipient_count=1`. The real v380 runtime DB reported
  `matching_documents=0`, `matching_schools=0`, and
  `matching_support_recipients=0`. Cleanup restored `EIDP Weekly Run` to
  `C:\Users\cyo20\EIDP-v380-f6a5e6d\scripts\weekly_run.bat` and removed the
  sandbox, backup, uploaded ZIP/sidecar, Python smoke, PowerShell runner, and
  result JSON.
- Windows v380 sandboxed Saitama 5-site bounded backend smoke:
  a disposable `C:\Users\cyo20\EIDP-v380-backend-sandbox` was created from the
  v380 runtime database through the package-local `eidp db-backup` command.
  The package-local `scripts\bootstrap_pdf_pipeline.py` then ran with
  `EIDP_APP_ROOT` pointed at that sandbox:
  `--pref saitama --skip-known-url-discovery --url-search off
  --school-url-crawl off --discovery-methods prefecture_aggregator
  --batch-size 5 --rate-limit 0.1 --request-timeout 10`, with artifact,
  output, PDF storage, evidence-log, RCA output, progress, and lock paths all
  redirected under the sandbox. It downloaded the current Saitama official
  artifact `r080401kikanyokenlist.pdf`, extracted `58`, matched `51`, applied
  `added=51 / upgraded=0 / skipped=7 / review_items=2`, crawled `5`
  official-index disclosure sites, found candidates on all `5`, downloaded
  `0` strict FY2026 target PDFs, skipped `163`, and wrote `2084` discovery
  evidence lines. Ingest processed `0` documents, then status rebuild reported
  `rebuilt=2418`, `excel_ready=0`, `target_pdf_auto_yield_pct=0.0`,
  `operator_reviewable_count=5`, `operator_reviewable_yield_pct=0.2`, and
  `ship_gate_status=below_gate`; the generated RCA batch plan had `5` items /
  `5` total candidates. Post-run verification inside the sandbox reported
  `school_site_count=51`, `prefecture_aggregator_sites=51`,
  `review_items=2`, `documents=0`, `status_rows=2418`,
  `progress_status=succeeded`, `progress_percent=1.0`,
  `progress_ship_gate_status=below_gate`, `progress_operator_reviewable_count=5`,
  `evidence_lines=2084`, `rca_files=1`, `rca_items=5`, and
  `rca_total_candidates=5`. The real v380 runtime DB remained unchanged for
  these tables: `runtime_school_site_count=0`, `runtime_review_items=0`,
  `runtime_documents=0`, and `runtime_status_rows=2418`. The sandbox was
  removed afterward; cleanup reported `sandbox_exists_after_cleanup=False` and
  `remaining_matching_processes=0`.

Previous v379 Windows setup and UI-service commands:

- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v379.zip --latest-alias`
  -> wrote `dist/eidp-windows-v379.zip` and refreshed `dist/eidp-windows.zip`;
  both have SHA256
  `88afc9f40feabe0dcd701fea3ccfdb870f96d1fe1e72afa9f1c66e2490fce212`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v379.zip --require-demonstrated-discovery-patterns`
  and `uv run python scripts/verify_windows_distribution.py dist/eidp-windows.zip --require-demonstrated-discovery-patterns`
  -> both `OK core`, with matching SHA256, `44` packaged discovery gold-set
  entries, `17` publication-lag cases, `47` prefecture seeds, and
  `undemonstrated_pattern_sources=[]`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v378.zip --require-demonstrated-discovery-patterns`
  now fails under the current verifier because v378 predates the WAL-safe
  backup runbook contract and the latest Stage 6 gate-token contract.
- Windows v379 setup on `C:\Users\cyo20\EIDP-v379-71e7537`:
  transferred `dist/eidp-windows-v379.zip` and its sidecar to
  `C:\Users\cyo20\EIDP-transfer`; Windows SHA256 matched
  `88afc9f40feabe0dcd701fea3ccfdb870f96d1fe1e72afa9f1c66e2490fce212`;
  expanded into a separate directory without touching v376 or v378.
  `EIDP-setup.bat` completed with build commit
  `d851de9edc16d831707b90ab4459c1de2e83434a`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`,
  `document_unique_indexes` including `uq_document_file_hash`, and
  `wheel_count=78`.
- Windows v379 after-setup validator:
  `runtime\python\python.exe scripts\validate_windows_install.py . --after-setup --json`
  returned `ok=true`, no errors or warnings, the same v379 build commit,
  `master_xlsx_present=true`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`, and all
  required SQLite tables.
- Windows v379 diagnostics:
  `EIDP-diagnose.bat` wrote
  `logs\diagnostics-20260513-230505.txt`. FY2026 readiness remained below gate
  with `ship_readiness_rc=1`, `strict_target_pdf_schools=0`,
  `operator_reviewable_schools=0`, `excel_ready_schools=0`, and
  `estimated_manual_workload_rate=1.0`. The retroactive FY2025 section recorded
  `is_retroactive_fiscal_year=true`, `extracted_schools=2031`,
  `extracted_rate=0.84`, `retroactive_fiscal_year=2025`, and
  `retroactive_ship_readiness_rc=0`. Because this was a fresh setup without
  discovery/bootstrap progress, both FY2026 and FY2025 operator-reviewable
  readiness remained `0`.
- Windows v379 UI service health smoke:
  a PowerShell harness started Streamlit from
  `C:\Users\cyo20\EIDP-v379-71e7537` on `127.0.0.1:8501`,
  received `/_stcore/health` as `status=200 body=ok`, reported
  `Streamlit, version 1.57.0`, and then stopped the process. The stdout tail
  included `URL: http://127.0.0.1:8501`; stderr recorded
  `Uvicorn server started on 127.0.0.1:8501`. A follow-up process check
  returned `count=0` for v379 Streamlit processes. This proves app-server
  health only; browser rendering, navigation, and operator-action click-through
  still require separate evidence.

Latest v393 full non-Windows release-gate commands:

- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v393.zip --json --output _temp/v393-non-windows-release-gates-full.json`
  -> `ok=true`; SHA256 sidecar matched
  `3ab58cca9494940ac85c7018aed2faeebc20d1784370d7203b8642b5623a32e8`; full
  unit passed with `1418 passed, 5 warnings`; validator/distribution unit tests
  passed with `147 passed`; validator/distribution mypy and Ruff passed;
  discovery gold-set reported `44` entries, `10` strict target-year successes,
  `17` publication-lag cases, and `undemonstrated_pattern_sources=[]`;
  expected-prediction replay returned `44` exact matches / `0` failures; both
  package verifier modes passed with the same v393 SHA256.

Historical v378 full non-Windows release-gate commands:


- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v378.zip --latest-alias`
  -> wrote `dist/eidp-windows-v378.zip` and refreshed `dist/eidp-windows.zip`;
  both have SHA256
  `bdf1ffbae478ee32a2ae745e34960b32c57dd0b1d0689fc7c1d7d438e5092a2e`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v378.zip --require-demonstrated-discovery-patterns`
  and `uv run python scripts/verify_windows_distribution.py dist/eidp-windows.zip --require-demonstrated-discovery-patterns`
  -> both `OK core`, with matching SHA256, `44` packaged discovery gold-set
  entries, `17` publication-lag cases, `47` prefecture seeds, and
  `undemonstrated_pattern_sources=[]`.
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v378.zip --json --output _temp/v378-non-windows-release-gates.json`
  -> `ok=true`; SHA256 sidecar matched; full unit passed with
  `1385 passed, 5 warnings`; validator/distribution unit tests passed with
  `141 passed`; validator/distribution mypy and Ruff passed; discovery
  gold-set reported `44` entries, `10` strict target-year successes,
  `17` publication-lag cases, and `undemonstrated_pattern_sources=[]`;
  expected-prediction replay returned `44` exact matches / `0` failures; both
  package verifier modes passed with SHA256
  `bdf1ffbae478ee32a2ae745e34960b32c57dd0b1d0689fc7c1d7d438e5092a2e`.
- Windows v378 setup on `C:\Users\cyo20\EIDP-v378-c82af41`:
  transferred `dist/eidp-windows-v378.zip` and its sidecar to
  `C:\Users\cyo20\EIDP-transfer`; Windows SHA256 matched
  `bdf1ffbae478ee32a2ae745e34960b32c57dd0b1d0689fc7c1d7d438e5092a2e`;
  expanded into a separate directory without touching v376;
  `EIDP-setup.bat` completed with build commit
  `c82af41728a91e72cfd661d114d199175213dc9d`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`,
  `document_unique_indexes` including `uq_document_file_hash`, and
  `wheel_count=78`.
- Windows v378 after-setup validator:
  `.venv\Scripts\python.exe scripts\validate_windows_install.py . --after-setup --json`
  returned `ok=true`, no errors or warnings, the same v378 build commit,
  `master_xlsx_present=true`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`, and all
  required SQLite tables.
- Windows v378 diagnostics:
  `EIDP-diagnose.bat` wrote
  `logs\diagnostics-20260513-224228.txt`. FY2026 readiness remained below gate
  with `ship_readiness_rc=1`, `strict_target_pdf_schools=0`,
  `operator_reviewable_schools=0`, `excel_ready_schools=0`, and
  `estimated_manual_workload_rate=1.0`. The retroactive FY2025 section recorded
  `is_retroactive_fiscal_year=true`, `extracted_schools=2031`,
  `extracted_rate=0.84`, `retroactive_fiscal_year=2025`, and
  `retroactive_ship_readiness_rc=0`.
- Windows v378 UI service smoke attempt:
  `python -m streamlit version` returned `Streamlit, version 1.57.0`, and
  `import eidp.review.app` returned `app_import_ok`. However, SSH-launched
  `Start-Process` Streamlit attempts did not produce a usable
  `/_stcore/health` response and left empty stdout/stderr logs; follow-up
  process checks reported `remaining_python_processes=0`. Treat v378 UI
  service/browser proof as not yet established.

Latest v376 commands (historical Windows-validated package evidence):

- `uv run pytest tests/unit/test_windows_packaging_spike.py::test_diagnose_bat_collects_operator_evidence_without_mutating_data tests/unit/test_windows_distribution_verifier.py::test_verify_core_zip_rejects_diagnose_without_retroactive_fiscal_year_snapshot tests/unit/test_windows_distribution_verifier.py::test_verify_core_zip_rejects_diagnose_with_parse_time_errorlevel_capture -q`
  -> `3 passed`
- `uv run ruff check scripts/verify_windows_distribution.py tests/unit/test_windows_packaging_spike.py`
  -> `All checks passed`
- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v376.zip --latest-alias`
  -> wrote `dist/eidp-windows-v376.zip` and refreshed `dist/eidp-windows.zip`; both have SHA256
  `8a7c9575394a37ee55ae8c566059385961cd70b8a06c768738a5529d7be9b2cd`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v376.zip --require-demonstrated-discovery-patterns`
  and `uv run python scripts/verify_windows_distribution.py dist/eidp-windows.zip --require-demonstrated-discovery-patterns`
  -> both `OK core`, with matching SHA256 and `43` packaged discovery gold-set entries.
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v376.zip --json --output _temp/v376-non-windows-release-gates-full.json`
  -> `ok=true`; SHA256 sidecar matched; full unit passed with
  `1377 passed, 5 warnings`; validator/distribution unit tests passed with
  `133 passed`; validator/distribution mypy and Ruff passed; discovery
  gold-set reported `43` entries, `10` strict target-year successes,
  `16` publication-lag cases, and `undemonstrated_pattern_sources=[]`;
  expected-prediction replay returned `43` exact matches / `0` failures; both
  package verifier modes passed with SHA256
  `8a7c9575394a37ee55ae8c566059385961cd70b8a06c768738a5529d7be9b2cd`.
- Windows v376 setup on `C:\Users\cyo20\EIDP-v376-d2402dc`:
  `EIDP-setup.bat` completed; `scripts\validate_install.bat` returned `OK install`;
  `.venv\Scripts\python.exe scripts\validate_windows_install.py . --after-setup --json`
  returned `ok=true`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`, and
  `document_unique_indexes` including `uq_document_file_hash`.
- Windows v376 diagnostics:
  `EIDP-diagnose.bat` wrote `logs\diagnostics-20260513-211539.txt`; FY2026
  readiness remained below gate with `ship_readiness_rc=1`, while the
  retroactive FY2025 snapshot recorded `is_retroactive_fiscal_year=true`,
  `extracted_schools=2031`, `extracted_rate=0.84`,
  `retroactive_fiscal_year=2025`, and `retroactive_ship_readiness_rc=0`.
- Windows v376 UI service smoke:
  `.venv\Scripts\python.exe -m streamlit run src\eidp\review\app.py
  --server.port 8501 --server.address 127.0.0.1 --server.headless true`
  started successfully; `http://127.0.0.1:8501/_stcore/health` returned
  `200 ok`; the smoke process was stopped, and a follow-up process check found
  no remaining Streamlit process.
- Windows v376 SSH-tunnel UI precheck:
  with the remote Streamlit process held open, `ssh -o ClearAllForwardings=no
  -L 127.0.0.1:18501:127.0.0.1:8501 win` exposed the Windows service to the
  Mac; local `curl http://127.0.0.1:18501/_stcore/health` returned `ok`.
  The tunnel and remote Streamlit processes were then stopped, and a follow-up
  check found no remaining Streamlit process.
- Windows v376 browser render smoke:
  using temporary `playwright-core` under `/tmp` plus the installed local
  Google Chrome binary, the tunneled Windows UI rendered with title
  `EIDP Operator Console`, `body_text_len=3533`, no captured console warnings
  or page errors, and visible operator text including `今週のやること`,
  `① 学校別タスク`, `② PDF確認・手入力`, `③ 年度判定・修正`,
  `④ Excel プレビュー`, `対象年度: 2026年度（令和8年度）`,
  `build: d2402dc`, `対象校 2418`, `Excel出力可 0/2418 校`, and
  `URLなし 2418`. The temporary npm package, script, Chrome profile, and
  screenshot were removed afterward. This proves initial browser rendering, not
  a full click-through of every operator workflow.
- Windows v376 read-only quick-navigation click-through:
  the same tunneled browser path clicked the five non-mutating quick navigation
  buttons and rendered each page without captured console warnings or page
  errors. Verified headings were `① 学校別タスク` with
  `週次URL/PDF再取得` / `次に進める作業`, `PDF確認・手入力`,
  `対象年度の判定・修正`, `Excel プレビュー`, and `設定` with
  `バージョン` / `和暦 alias` / `OCR` / `外部 API`. The script did not click
  acquisition, save, export, or any data-mutating action. Temporary npm files
  were removed afterward.
- Windows v376 Excel preview disabled-state smoke:
  the tunneled browser path opened `④ Excel プレビュー` and verified the
  page rendered with no console warnings or page errors. With current FY2026
  target-year data still empty, the page showed `対象年度PDFあり 0`,
  `Excel出力可 0`, `Excel対象行 0`, `URLなし 2367`, `未採録校 2418`,
  and the operator warning that 2026 target-year transcribed rows are `0`.
  The `プレビュー workbook を生成` button was present but disabled, so the
  UI correctly prevents downloading old-year or empty workbook output.
- Windows v376 retroactive FY2025 Excel preview/download smoke:
  the same installed package was started with
  `EIDP_TARGET_FISCAL_YEAR=2025` and opened through the SSH tunnel. The
  `④ Excel プレビュー` page showed `対象年度: 2025年度（令和7年度）`,
  `抽出済み学校 2031`, `Excel対象行 7150`, and sheet counts
  `採録状況=2418 / 対象比率=10022 / 学科別=9719 / 在籍のみ抜粋=9719`.
  The `プレビュー workbook を生成` button was enabled, generated the in-memory
  workbook, and exposed `Excel ダウンロード`; the browser download produced
  `eidp_master.xlsx` with size `3,728,652` bytes. No browser console warnings
  or page errors were captured, and the temporary npm/download artifacts were
  removed afterward. This proves the Windows UI Excel preview/download path
  works for the retroactive R7 dataset, while FY2026 remains blocked by absent
  current target-year rows.
- Windows v376 ManualActionLog/outbox sandbox smoke:
  a disposable `C:\Users\cyo20\EIDP-v376-audit-sandbox` copied only the
  current v376 SQLite files, ran the package code with `EIDP_APP_ROOT` pointed
  at that sandbox, inserted one `stage6_smoke_manual_action` row via
  `log_manual_action`, committed it, and flushed `manual-actions.jsonl` via
  `flush_audit_outbox`. The smoke reported `inserted_delta=1`,
  `flush_stats={exported: 1, already_present: 0, failed: 0}`,
  `jsonl_exported_at_present=true`, `matching_outbox_rows=1`, and actor
  `codex-stage6-smoke`. The sandbox directory was removed afterward, and the
  current v376 runtime directory was not mutated.
- Windows v376 browser UI audit-outbox flush smoke:
  a second disposable sandbox `C:\Users\cyo20\EIDP-v376-ui-audit-sandbox`
  seeded one unexported `stage6_ui_audit_flush_smoke` `ManualActionLog` row,
  then started the v376 Streamlit UI against that sandbox. Through the SSH
  tunnel, the browser opened `詳細 operator` -> `監査ログ`, verified
  `JSONL outbox 未送信 1`, clicked `Outbox を flush`, and observed
  `exported=1 already_present=0 failed=0` with the row visible as
  `stage6_ui_audit_flush_smoke` by `codex-ui-smoke`. A direct post-UI DB/file
  check reported `pending=0`, `matching_db_rows=1`,
  `matching_exported_rows=1`, `matching_outbox_rows=1`, and `outbox_lines=1`.
  The remote sandbox, Streamlit process, SSH tunnel, and local Playwright temp
  files were removed afterward.
- Windows v376 browser UI URL-candidate review write smoke:
  a disposable `C:\Users\cyo20\EIDP-v376-url-review-sandbox` seeded one
  pending `url_candidate` `ReviewItem` for `日本工学院専門学校` with candidate URL
  `https://example.com/eidp-stage6-url-candidate-smoke`. The v376 Streamlit UI
  was started against that sandbox, and the tunneled browser opened
  `詳細 operator` -> `URL候補レビュー`, confirmed `確認待ち 1 件`, entered reject
  reason `stage6 UI reject smoke`, and clicked `却下`. The UI then showed
  `確認待ちのURL候補はありません。` with no browser console warnings or page
  errors. Direct post-UI DB verification reported `review_items=1`,
  `pending_items=0`, `resolved_rejected_items=1`, `audit_rows=1`, and
  `audit_action_types=["url_candidate_rejected"]`. The sandbox, Streamlit
  process, SSH tunnel, and local Playwright temp directory were removed
  afterward.
- Windows v376 Saitama 5-site bounded backend smoke:
  `bootstrap_pdf_pipeline.py --pref saitama --url-search off
  --school-url-crawl off --skip-known-url-discovery --discovery-methods
  prefecture_aggregator --batch-size 5 --rate-limit 0.1 --request-timeout 10`
  completed on `C:\Users\cyo20\EIDP-v376-d2402dc`. It downloaded the current
  Saitama artifact, extracted `58` rows, matched `51`, added `51`
  `SchoolSite` rows, crawled `5` official-index disclosure sites, found
  candidates on all `5`, downloaded `0` strict FY2026 target PDFs, produced
  `2084` discovery evidence lines, rebuilt `2418` school status rows, and
  reported `operator_reviewable_count=5`,
  `operator_reviewable_yield_pct=0.2`, `target_pdf_auto_yield_pct=0.0`, and
  `ship_gate_status=below_gate`. The progress JSON loaded as valid UTF-8 and
  after-run `validate_windows_install.py --after-setup --json` returned
  `ok=true` with `sqlite_integrity_check=ok`.
- Windows cleanup after v376 proof removed stale
  `C:\Users\cyo20\EIDP-v342-de2cfed` plus old transfer ZIPs
  `eidp-windows-v220.zip`, `v221`, `v222`, and `v375` with their sha256
  sidecars. Remaining EIDP paths are only `EIDP-v376-d2402dc` and
  `EIDP-transfer`; the transfer directory now contains only
  `eidp-windows-v376.zip` and `eidp-windows-v376.zip.sha256`. A follow-up
  process check found no remaining EIDP Streamlit/bootstrap process.

Previously retained v375 commands:

- `uv run pytest tests/unit/test_pdf_discovery.py::test_pdf_link_context_does_not_cross_intervening_non_year_block tests/unit/test_pdf_discovery.py::test_pdf_link_context_skips_update_date_before_heading_year tests/unit/test_pdf_discovery.py::test_prefecture_public_school_page_uses_heading_year_for_old_target_forms -q`
  -> `3 passed`
- `uv run pytest tests/unit/test_pdf_discovery.py::test_prioritize_viable_candidates_prefers_latest_public_stale_target_form tests/unit/test_pdf_discovery.py::test_current_year_syllabus_does_not_outrank_previous_year_target_form tests/unit/test_pdf_discovery.py::test_prioritize_viable_candidates_prefers_current_year_target_over_higher_score_stale_target -q`
  -> `3 passed`
- `uv run ruff check src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py src/eidp/scraper/discovery_gold_set.py tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_summary.py tests/unit/test_cli_discovery_gold_set.py tests/unit/test_cli_eval_discovery_gold.py tests/unit/test_discovery_gold_set_eval.py tests/unit/test_discovery_gold_set_seed.py`
  -> `All checks passed`
- `uv run mypy src/eidp/scraper/pdf_discovery.py src/eidp/scraper/discovery_gold_set.py`
  -> `Success: no issues found in 2 source files`
- `uv run pytest tests/unit/test_pdf_discovery.py -q`
  -> `161 passed, 5 warnings`
- `uv run pytest tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_summary.py tests/unit/test_cli_discovery_gold_set.py tests/unit/test_cli_eval_discovery_gold.py tests/unit/test_discovery_gold_set_eval.py tests/unit/test_discovery_gold_set_seed.py -q`
  -> `47 passed`
- `uv run ruff check tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_summary.py tests/unit/test_cli_discovery_gold_set.py tests/unit/test_cli_eval_discovery_gold.py tests/unit/test_discovery_gold_set_eval.py tests/unit/test_discovery_gold_set_seed.py src/eidp/scraper/discovery_gold_set.py`
  -> `All checks passed`
- `uv run pytest tests/unit -q`
  -> `1377 passed, 5 warnings`
- `uv run eidp discovery-gold-set --json`
  -> `43` entries, `10` strict target-year successes, `16` publication-lag cases, `0` undemonstrated pattern sources.
- `uv run eidp eval-discovery-gold --predictions data/discovery-gold-set/expected-predictions.jsonl --fail-on-regression --json`
  -> `43` exact matches, `0` failed, `0` missing, and `0` unexpected predictions.
- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v375.zip --latest-alias`
  -> wrote `dist/eidp-windows-v375.zip` and refreshed `dist/eidp-windows.zip`; both have SHA256
  `fa9a7c11f6d2f1efeadc4aa234965d733c8c45862f179e4e82dea65ac177ce4c`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v375.zip --require-demonstrated-discovery-patterns`
  and `uv run python scripts/verify_windows_distribution.py dist/eidp-windows.zip --require-demonstrated-discovery-patterns`
  -> both `OK core`, with matching SHA256 and `43` packaged discovery gold-set entries.
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v375.zip --json --output _temp/v375-non-windows-release-gates-full.json`
  -> `ok=true`, SHA256 sidecar matched, full unit passed with `1377 passed, 5 warnings`, distribution-verifier passed with `133 passed`, package verifier passed, and demonstrated-pattern gate passed.
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v375.zip --skip-full-unit --pdf-evidence _temp/win-v342-tokyo-probe/discovery_rejections_tokyo_v342_30.jsonl --pdf-evidence _temp/win-v342-evidence/discovery_rejections.jsonl --pdf-evidence _temp/seijuji-gold-v2/discovery_evidence.jsonl --pdf-evidence _temp/kousei-gold-v2/discovery_evidence.jsonl --pdf-evidence _temp/chuo-gold-v1/discovery_evidence.jsonl --pdf-evidence _temp/kimikan-manual-v2/discovery_evidence.jsonl --json --output _temp/v375-non-windows-release-gates-evidence.json`
  -> `ok=true`, Tokyo evidence `4` exact / `0` failures, Saitama evidence `16` exact / `0` failures, 聖十字 evidence `1` exact / `0` failures, 更生 evidence `1` exact / `0` failures, 中央情報 evidence `1` exact / `0` failures, and 君津 evidence `1` exact / `0` failures. 愛生会, あいち福祉医療, and 尚美 are expectedly absent from those older bounded evidence JSONL files because they were added from fresh manual-web / official-index traces.

Previously retained v359/v358/v357/v342 source/package evidence:

- `uv run pytest tests/unit -q` -> `1366 passed, 5 warnings`
- `uv run pytest tests/unit/test_pdf_discovery.py::test_extract_pdf_links_does_not_assign_visible_sibling_anchor_text_to_empty_anchor tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_summary.py tests/unit/test_cli_eval_discovery_gold.py tests/unit/test_cli_discovery_gold_set.py tests/unit/test_discovery_gold_set_eval.py tests/unit/test_discovery_gold_set_seed.py -q`
  -> `47 passed`
- `uv run pytest tests/unit/test_pdf_discovery.py tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_summary.py tests/unit/test_cli_eval_discovery_gold.py tests/unit/test_cli_discovery_gold_set.py tests/unit/test_discovery_gold_set_eval.py tests/unit/test_discovery_gold_set_seed.py tests/unit/test_windows_distribution_verifier.py -q`
  -> `290 passed, 5 warnings`
- `uv run ruff check tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_summary.py tests/unit/test_cli_eval_discovery_gold.py tests/unit/test_cli_discovery_gold_set.py tests/unit/test_discovery_gold_set_eval.py tests/unit/test_discovery_gold_set_seed.py`
  -> `All checks passed`
- `uv run ruff check src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_summary.py tests/unit/test_cli_eval_discovery_gold.py tests/unit/test_cli_discovery_gold_set.py tests/unit/test_discovery_gold_set_eval.py tests/unit/test_discovery_gold_set_seed.py`
  -> `All checks passed`
- `uv run mypy src/eidp/scraper/pdf_discovery.py`
  -> `Success: no issues found in 1 source file`
- Current Tokyo Anime HTML extraction probe:
  `_extract_pdf_links` against `https://www.anime.ac.jp/school/public_info/`
  -> emitted visible `11_confirmation_application.pdf` and `12_kakunin.pdf`
  candidates, and did not emit the commented-out `07_study_support_application.pdf`.
- Source-side 君津 one-school replay:
  `discover-pdfs --discovery-method discovery_gold_set --school-id 798`
  -> `crawled=1`, `found=1`, `downloaded=1`, `failed=0`, `skipped=0`,
  evidence `reason=accepted_downloaded`, `year_evidence=url_hint`,
  `pattern_type=direct`, `pdf_type=target`, and visible-anchor-local context.
- `uv run python -m eidp.cli eval-discovery-gold --pdf-evidence _temp/kimikan-manual-v2/discovery_evidence.jsonl --json`
  -> `1` exact / `0` failures for `kimikan-nursing-empty-anchor-accepted-2026`
- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v357.zip`
  -> wrote `dist/eidp-windows-v357.zip` and checksum sidecar.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v357.zip`
  -> `OK core`, build commit
  `aa10c8982a4b7f67a5a10509bbd86dbfee462b21`, `git_dirty=false`,
  `discovery_gold_set_entries=36`, `discovery_gold_expected_predictions=36`,
  `discovery_gold_undemonstrated_pattern_sources=[]`,
  `discovery_gold_pattern_sources={'direct': 5, 'embed': 1, 'wordpress': 4, 'wordpress_download_manager': 1}`,
  SHA256 `5385dd9395e295bc31b31193fd7582bd0df3678d7f6bc39abd845a6bfb32952f`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v357.zip --require-demonstrated-discovery-patterns`
  -> `OK core`, with `discovery_gold_undemonstrated_pattern_sources=[]`.
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v357.zip --json --output _temp/v357-non-windows-release-gates-full.json`
  -> `ok=true`, SHA256 sidecar matched, full unit passed, and all non-Windows gates passed.
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v357.zip --skip-full-unit --pdf-evidence _temp/win-v342-tokyo-probe/discovery_rejections_tokyo_v342_30.jsonl --pdf-evidence _temp/win-v342-evidence/discovery_rejections.jsonl --pdf-evidence _temp/seijuji-gold-v2/discovery_evidence.jsonl --pdf-evidence _temp/kousei-gold-v2/discovery_evidence.jsonl --pdf-evidence _temp/chuo-gold-v1/discovery_evidence.jsonl --pdf-evidence _temp/kimikan-manual-v2/discovery_evidence.jsonl --json --output _temp/v357-non-windows-release-gates-evidence.json`
  -> `ok=true`, Tokyo evidence `4` exact / `0` failures, Saitama evidence `16` exact / `0` failures, 聖十字 evidence `1` exact / `0` failures, 更生 evidence `1` exact / `0` failures, 中央情報 evidence `1` exact / `0` failures, and 君津 evidence `1` exact / `0` failures.

Previously retained v354 source/package evidence:

- `uv run pytest tests/unit -q` -> `1364 passed, 5 warnings`
- `uv run pytest tests/unit/test_pdf_discovery.py tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_summary.py tests/unit/test_cli_eval_discovery_gold.py tests/unit/test_cli_discovery_gold_set.py tests/unit/test_discovery_gold_set_eval.py tests/unit/test_discovery_gold_set_seed.py tests/unit/test_windows_distribution_verifier.py -q`
  -> `288 passed, 5 warnings`
- `uv run ruff check src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_summary.py tests/unit/test_cli_eval_discovery_gold.py tests/unit/test_cli_discovery_gold_set.py tests/unit/test_discovery_gold_set_eval.py tests/unit/test_discovery_gold_set_seed.py`
  -> `All checks passed`
- `uv run mypy src/eidp/scraper/pdf_discovery.py`
  -> `Success: no issues found in 1 source file`
- Source-side 更生 one-school replay:
  `discover-pdfs --discovery-method discovery_gold_set --school-id 1375`
  -> `crawled=1`, `found=1`, `downloaded=1`, `failed=0`, `skipped=0`,
  evidence `reason=accepted_downloaded`, `year_evidence=url_hint`,
  `pattern_type=direct`, `pdf_type=target`, and local `dd` anchor context.
- `uv run python -m eidp.cli eval-discovery-gold --pdf-evidence _temp/kousei-gold-v2/discovery_evidence.jsonl --json`
  -> `1` exact / `0` failures for `kousei-nursing-support-accepted-2026`
- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v354.zip`
  -> wrote `dist/eidp-windows-v354.zip` and checksum sidecar.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v354.zip`
  -> `OK core`, build commit
  `0ee34c6cbaf9a8c4f6dd1d7712a0ee51b758afb9`, `git_dirty=false`,
  `discovery_gold_set_entries=34`, `discovery_gold_expected_predictions=34`,
  `discovery_gold_undemonstrated_pattern_sources=[]`,
  `discovery_gold_pattern_sources={'direct': 4, 'embed': 1, 'wordpress': 3, 'wordpress_download_manager': 1}`,
  SHA256 `95ed537dc21beb52add6b31df0705ec9a6528c272354da68783f362b27b55dc4`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v354.zip --require-demonstrated-discovery-patterns`
  -> `OK core`, with `discovery_gold_undemonstrated_pattern_sources=[]`.
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v354.zip --json --output _temp/v354-non-windows-release-gates-full.json`
  -> `ok=true`, SHA256 sidecar matched, full unit passed, and all non-Windows gates passed.
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v354.zip --skip-full-unit --pdf-evidence _temp/win-v342-tokyo-probe/discovery_rejections_tokyo_v342_30.jsonl --pdf-evidence _temp/win-v342-evidence/discovery_rejections.jsonl --pdf-evidence _temp/seijuji-gold-v2/discovery_evidence.jsonl --pdf-evidence _temp/kousei-gold-v2/discovery_evidence.jsonl --json --output _temp/v354-non-windows-release-gates-evidence.json`
  -> `ok=true`, Tokyo evidence `4` exact / `0` failures, Saitama evidence `16` exact / `0` failures, 聖十字 evidence `1` exact / `0` failures, and 更生 evidence `1` exact / `0` failures.

- `uv run pytest tests/unit -q` -> `1363 passed, 5 warnings`
- `uv run python -m eidp.cli db-info`
  -> clean `rc=2` when the local SQLite file has no schema, with no traceback and an operator-actionable setup/import message
- `uv run pytest tests/unit/test_non_windows_release_gates.py -q`
  -> `8 passed`
- `uv run mypy scripts/run_non_windows_release_gates.py`
  -> `Success: no issues found in 1 source file`
- `uv run ruff check scripts/run_non_windows_release_gates.py tests/unit/test_non_windows_release_gates.py`
  -> `All checks passed`
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v353.zip --json --output _temp/v353-non-windows-release-gates-full.json`
  -> `ok=true`, SHA256 sidecar matched, full unit passed, and all non-Windows gates passed
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v353.zip --skip-full-unit --pdf-evidence _temp/win-v342-tokyo-probe/discovery_rejections_tokyo_v342_30.jsonl --pdf-evidence _temp/win-v342-evidence/discovery_rejections.jsonl --pdf-evidence _temp/seijuji-gold-v2/discovery_evidence.jsonl --json --output _temp/v353-non-windows-release-gates-evidence.json`
  -> `ok=true`, Tokyo evidence `4` exact / `0` failures, Saitama evidence `16` exact / `0` failures, 聖十字 evidence `1` exact / `0` failures;
  pdf-evidence replay gates allow bounded missing entries but fail on failed/unexpected predictions
- `EIDP_DATABASE_URL=sqlite:///$PWD/_temp/v348-mac-tokyo20/eidp.sqlite3 uv run python -m eidp.cli report ship-readiness --json`
  -> `ok=false`, `total_schools=2418`, `strict_target_pdf_rate=0.0`,
  `operator_reviewable_rate=0.019`, `excel_ready_rate=0.0`
- `uv run pytest tests/unit/test_pdf_discovery.py tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_summary.py tests/unit/test_cli_discovery_gold_set.py tests/unit/test_windows_distribution_verifier.py -q` -> `247 passed, 5 warnings`
- `uv run pytest tests/unit/test_windows_distribution_verifier.py -q` -> `89 passed`
- `uv run pytest tests/unit/test_windows_install_validator.py tests/unit/test_windows_distribution_verifier.py -q`
  -> `131 passed`
- `uv run mypy scripts/validate_windows_install.py scripts/verify_windows_distribution.py`
  -> `Success: no issues found in 2 source files`
- `uv run ruff check scripts/validate_windows_install.py scripts/verify_windows_distribution.py tests/unit/test_windows_install_validator.py tests/unit/test_windows_distribution_verifier.py`
  -> `All checks passed`
- `uv run pytest tests/unit/test_pdf_discovery.py tests/unit/test_url_discovery.py tests/unit/test_url_normalization.py tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_eval.py tests/unit/test_cli_eval_discovery_gold.py tests/unit/test_discovery_gold_set_summary.py -q` -> `206 passed, 5 warnings`
- `uv run pytest tests/unit/test_review_excel_preview.py tests/unit/test_excel_exporter.py tests/unit/test_windows_distribution_verifier.py -q` -> `96 passed`
- `uv run ruff check src/eidp/review/_pages/excel_preview.py tests/unit/test_review_excel_preview.py` -> `All checks passed`
- `uv run pytest tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_summary.py tests/unit/test_discovery_gold_set_seed.py tests/unit/test_discovery_gold_set_eval.py tests/unit/test_cli_discovery_gold_set.py tests/unit/test_cli_eval_discovery_gold.py -q` -> `46 passed`
- `uv run pytest tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_summary.py tests/unit/test_discovery_gold_set_eval.py tests/unit/test_cli_eval_discovery_gold.py -q` -> `36 passed`
- `uv run ruff check src/eidp/scraper/pdf_discovery.py src/eidp/scraper/discovery_evidence_summary.py src/eidp/scraper/discovery_gold_set.py tests/unit/test_pdf_discovery.py tests/unit/test_discovery_evidence_summary.py tests/unit/test_cli_eval_discovery_gold.py` -> `All checks passed`
- `uv run ruff check tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_summary.py` -> `All checks passed`
- `uv run ruff check src/eidp/config.py src/eidp/scraper/pdf_discovery.py src/eidp/scraper/discovery_gold_set.py scripts/verify_windows_distribution.py tests/unit/test_pdf_discovery.py tests/unit/test_discovery_gold_set.py tests/unit/test_cli_discovery_gold_set.py tests/unit/test_windows_distribution_verifier.py` -> `All checks passed`
- `uv run eidp discovery-gold-set --json` -> `32` entries,
  `accepted_target_pdf=4`, `needs_operator_review=15`,
  `publication_lag_latest_public=11`, `strict_target_year_successes=4`
- `uv run eidp eval-discovery-gold --predictions data/discovery-gold-set/expected-predictions.jsonl --fail-on-regression --json` -> `32` exact, `0` failures
- `uv run eidp eval-discovery-gold --pdf-evidence _temp/win-v342-tokyo-probe/discovery_rejections_tokyo_v342_30.jsonl --json` -> `4` exact, `0` failures for the Tokyo entries present in the bounded run, including `pattern_type`
- `uv run eidp eval-discovery-gold --pdf-evidence _temp/win-v342-evidence/discovery_rejections.jsonl --json` -> `16` exact, `0` failures for the Saitama evidence entries present in the bounded run
- `uv run python` bounded live HTML scan over `160` official-index school URLs
  from the v342 Tokyo/Saitama evidence SQLite DBs -> pattern sources observed:
  `direct=37059`, `wordpress=857`, `cache_busted=52`; observed examples for
  the six undemonstrated sources remained `0`. The scan wrote its local
  summary to `_temp/v345-pattern-source-live-scan-summary.json`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v342.zip` -> `OK core`
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v342.zip --require-demonstrated-discovery-patterns` -> expected failure for the six remaining undemonstrated sources
- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v350.zip`
  -> wrote `dist/eidp-windows-v350.zip` and checksum sidecar.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v350.zip`
  -> `OK core`, build commit
  `ac54605b0a57b94fe4b0467a74f942f3919b4f0f`, `git_dirty=false`,
  `discovery_gold_set_entries=32`, `discovery_gold_expected_predictions=32`,
  `discovery_gold_undemonstrated_pattern_sources=[]`,
  `discovery_gold_pattern_sources={'direct': 3, 'embed': 1, 'wordpress': 2, 'wordpress_download_manager': 1}`,
  SHA256 `f6c450576202409f82e524f708b62ae6174e70281e87cf411022bc8109fc6dae`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v350.zip --require-demonstrated-discovery-patterns`
  -> `OK core`, with `discovery_gold_undemonstrated_pattern_sources=[]`.
- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v351.zip`
  -> wrote `dist/eidp-windows-v351.zip` and checksum sidecar.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v351.zip`
  -> `OK core`, build commit
  `90b64c583080011bb2cd94053fe82a51b0d66ca7`, `git_dirty=false`,
  `discovery_gold_set_entries=32`, `discovery_gold_expected_predictions=32`,
  `discovery_gold_undemonstrated_pattern_sources=[]`,
  `discovery_gold_pattern_sources={'direct': 3, 'embed': 1, 'wordpress': 2, 'wordpress_download_manager': 1}`,
  SHA256 `e97d1e58360e87ededa219846a80145aed0242a5d1d1f1f6d64a6403476a94fc`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v351.zip --require-demonstrated-discovery-patterns`
  -> `OK core`, with `discovery_gold_undemonstrated_pattern_sources=[]`.
- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v352.zip`
  -> wrote `dist/eidp-windows-v352.zip` and checksum sidecar.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v352.zip`
  -> `OK core`, build commit
  `8f385f86e5a976b913d777ea80b56c00dc1c5ae7`, `git_dirty=false`,
  `discovery_gold_set_entries=32`, `discovery_gold_expected_predictions=32`,
  `discovery_gold_undemonstrated_pattern_sources=[]`,
  `discovery_gold_pattern_sources={'direct': 3, 'embed': 1, 'wordpress': 2, 'wordpress_download_manager': 1}`,
  SHA256 `2a8716d79cf2fcb42397bb126d90222ccf63e7fe72e38a3e303c5f9f6fbb5f25`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v352.zip --require-demonstrated-discovery-patterns`
  -> `OK core`, with `discovery_gold_undemonstrated_pattern_sources=[]`.
- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v353.zip`
  -> wrote `dist/eidp-windows-v353.zip` and checksum sidecar.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v353.zip`
  -> `OK core`, build commit
  `b75eecd60d0417369f58cc17f298e288c1f2d251`, `git_dirty=false`,
  `discovery_gold_set_entries=33`, `discovery_gold_expected_predictions=33`,
  `discovery_gold_undemonstrated_pattern_sources=[]`,
  `discovery_gold_pattern_sources={'direct': 3, 'embed': 1, 'wordpress': 3, 'wordpress_download_manager': 1}`,
  SHA256 `9c68738c78ded416c84696fb78606f29767c9fe4f566747f42db802cb8a827de`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v353.zip --require-demonstrated-discovery-patterns`
  -> `OK core`, with `discovery_gold_undemonstrated_pattern_sources=[]`.
- Source-side v348 strict Tokyo repeat on a copy of the v342 Tokyo aggregate DB:
  `EIDP_DATABASE_URL=sqlite:///$PWD/_temp/v348-mac-tokyo20/eidp.sqlite3 EIDP_DATA_DIR=$PWD/_temp/v348-mac-tokyo20/data uv run eidp discover-pdfs --storage-dir _temp/v348-mac-tokyo20/pdfs --batch-size 20 --rate-limit 0.2 --request-timeout 12 --discovery-method prefecture_aggregator --evidence-log _temp/v348-mac-tokyo20/discovery_rejections.jsonl`
  -> `crawled=20`, `found=20`, `downloaded=0`, `failed=4`,
  `skipped=404`, `cached_rejections=125`, `prefiltered=229`,
  `candidate_budget_limited=1`, `candidate_budget_dropped=6`,
  `rejection_reason_pre_filtered_non_target_hint=351`,
  `rejection_reason_fiscal_year_mismatch=62`,
  `rejection_reason_classified_non_target=34`,
  `rejection_reason_target_fiscal_year_not_detected=10`,
  `rejection_reason_http_error_httpstatuserror=3`, and
  `rejection_reason_not_pdf_magic=2`.
- `EIDP_DATABASE_URL=sqlite:///$PWD/_temp/v348-mac-tokyo20/eidp.sqlite3 uv run eidp summarize-discovery-evidence --evidence-log _temp/v348-mac-tokyo20/discovery_rejections.jsonl --discovery-method prefecture_aggregator --json`
  -> `468` evidence rows, pattern sources `direct=394`, `wordpress=39`,
  `cache_busted=35`, PDF type counts `target=66`, `image_only=6`,
  `non_target=385`, `unknown=5`, and `null=6`. Among the `20` crawled
  schools with evidence, buckets are `publication_lag_or_old_target_pdf=15`,
  `target_form_without_year_evidence=1`, and `non_target_candidates_only=4`.
  The command also reports `no_evidence=263` for Tokyo official-index sites
  that were in the copied aggregate DB but outside this `batch_size=20` smoke.

Post-v342 source-side gold-set expansion:

- Four Tokyo source/evidence rows have been promoted to committed discovery
  gold-set entries:
  東京俳優・映画＆放送専門学校 `conf-apl.pdf`,
  東京ダンス・俳優＆舞台芸術専門学校 `check-da.pdf`, and
  東京メディカル・スポーツ専門学校 `support2024.pdf`, plus the source-side
  v348 Tokyo Sanko publication-lag case for
  東京医療秘書歯科衛生＆IT専門学校 `yoshiki2025.pdf`.
- `uv run eidp discovery-gold-set --json` now reports `32` entries:
  `accepted_target_pdf=4`, `needs_operator_review=15`,
  `publication_lag_latest_public=11`, `no_target_candidate_found=1`,
  and `site_fetch_error=1`.
- `uv run eidp eval-discovery-gold --predictions data/discovery-gold-set/expected-predictions.jsonl --fail-on-regression --json`
  now reports `32` exact predictions with `0` failures.
- `uv run eidp eval-discovery-gold --pdf-evidence _temp/win-v342-tokyo-probe/discovery_rejections_tokyo_v342_30.jsonl --json`
  now reports `4` exact predictions with `0` failures. The remaining `28`
  missing entries are outside the Tokyo 30-site sample.
- This source-side evidence, the Excel preview threshold-label fix, and the
  Tokyo pattern-type regression contract, the Tokyo Sanko publication-lag
  regression, and the default isolation of synthetic-only extractor sources are
  packaged into the new Mac-verifier-clean `dist/eidp-windows-v351.zip`.
  It still requires a future Windows extraction
  and setup run before it can replace v342 as Windows-setup-proven.

v351 verifier exposes the current production-pattern demonstration status:

- Discovery gold-set entries: `32`
- Outcome distribution: `accepted_target_pdf=4`, `needs_operator_review=15`,
  `no_target_candidate_found=1`, `publication_lag_latest_public=11`,
  `site_fetch_error=1`
- Demonstrated extractor sources: `direct` (3), `embed` (1), `wordpress` (2),
  `wordpress_download_manager` (1)
- Production-tracked undemonstrated sources: none
- Experimental-only, default-disabled sources: `data_attribute`, `form_action`,
  `input_control`, `meta_refresh`, `onclick`, `select_option`

## Current Windows Backend Evidence

Commands and observations from `ssh win` for v342 setup and targeted discovery
probe:

- Uploaded `dist/eidp-windows-v342.zip` to
  `C:\Users\cyo20\eidp-windows-v342.zip`.
- Windows `Get-FileHash -Algorithm SHA256` ->
  `8eb3fcb785f8dbbeebc008f710af7f58bf4d91fcd4d53958b6f519a6b934b593`.
- Extracted to `C:\Users\cyo20\EIDP-v342-de2cfed`.
- `scripts\first_setup.bat` -> exit `0`; core and after-setup validators
  returned `0`, reported commit `de2cfed4f2a0f1834bc76368438bda3d80ff8413`,
  `build_dirty=false`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`,
  required SQLite tables present, `department_change` void columns present,
  and `uq_document_file_hash` present.
- Windows package-local targeted Kanto probe for
  `https://kanto-koudai.com/school/#information` reports
  `best_score=2.5`,
  `best_url=https://kanto-koudai.com/school/johokokai/j2024_05a.pdf`,
  `download_pdf_type=image_only`, and
  `download_reason=fiscal_year_mismatch:2024`. The SSH console rendered the
  Japanese anchor text as mojibake, but the URL/ranking/rejection outcome proves
  the backend behavior.
- Windows package-local targeted Iruma probe for
  `https://www.i-heiseigakuen.ac.jp/kokai/` follows the application-form page
  to the WordPress Download Manager wrapper. The best candidate is
  `https://i-heiseigakuen.ac.jp/download/yousiki2/?wpdmdl=5471&refresh=...`,
  `pattern_type=wordpress_download_manager`, and strict download now rejects it
  as `target` / `fiscal_year_mismatch:2024` instead of
  `target_fiscal_year_not_detected`. The SSH console rendered the Japanese
  `様式２（R6年度分申請）` package title as mojibake, but the rejection outcome
  proves the year-context repair in the packaged runtime.

Latest bounded bootstrap evidence is v342:

Commands and observations from `ssh win` for v342 setup/bootstrap:

- `scripts\bootstrap_pdfs.bat --pref saitama --skip-known-url-discovery --url-search off --school-url-crawl off --batch-size 50 --rate-limit 0.2 --request-timeout 15` -> exit `0`.
- Official Saitama artifact downloaded; aggregate `extracted=58`,
  `matched=51`, `added=51`, `review_items=2`.
- PDF discovery: `crawled=50`, `found=49`, `downloaded=0`, `failed=3`,
  `skipped=1391`, `prefiltered=1055`, `cached_rejections=285`,
  `candidate_school_mismatch=5160`, `candidate_budget_dropped=855`,
  `rejection_reason_discovery_error=1`,
  `rejection_reason_pre_filtered_non_target_hint=1062`,
  `rejection_reason_fiscal_year_mismatch=328`,
  `rejection_reason_target_fiscal_year_not_detected=31`,
  `rejection_reason_unsafe_url=1`.
- Ingest: `processed=0`, `departments_created=0`, `yearly_upserted=0`,
  `skipped=0`.
- Rebuilt status: `excel_ready=0`, `target_pdf_auto_acquired_count=0`,
  `operator_reviewable_count=46`, `operator_reviewable_yield_pct=1.9`,
  `ship_gate_status=below_gate`.
- Diagnostics after bootstrap:
  `validate_after_bootstrap_rc=0`,
  `validate_after_bootstrap_ship_gate_rc=1`.
- Local evidence snapshot was pulled to `_temp/win-v342-evidence/`, including
  `bootstrap-pdfs-20260513-072137.log`, `bootstrap-pdfs-20260513-072137.json`,
  `bootstrap-20260513_073824-discovery-rca-batch-plan.json`,
  `discovery_rejections.jsonl`, and `eidp.sqlite3`.
- v342 evidence confirms Kanto is no longer dropped by neighboring disclosure-card
  noise: `j2024_05a.pdf` appears with `score=2.5`, `pdf_type=image_only`,
  and `reason=fiscal_year_mismatch:2024`; the status cache records school `783`
  as `target_year_unverified`.
- v342 evidence confirms the Iruma WordPress Download Manager context repair:
  `wpdmdl=5471` carries `様式２（R6年度分申請）` in `anchor_text` and is rejected
  as `target` / `fiscal_year_mismatch:2024`; the status cache records school
  `760` as `publication_lag`.
- `uv run eidp eval-discovery-gold --pdf-evidence _temp/win-v342-evidence/discovery_rejections.jsonl --json`
  reports `16` exact predictions, `0` failed predictions, and `12` missing
  entries outside the bounded Saitama sample.
- SQLite status rows from the v342 evidence DB: `none=2372`,
  `publication_lag=38`, `target_year_unverified=8`.
- Reproducible scoped summary command:
  `EIDP_DATABASE_URL=sqlite:///$PWD/_temp/win-v342-evidence/eidp.sqlite3 uv run eidp summarize-discovery-evidence --evidence-log _temp/win-v342-evidence/discovery_rejections.jsonl --discovery-method prefecture_aggregator --json`.
  It reports Saitama official-index scope `51` schools with
  `publication_lag_or_old_target_pdf=38`, `target_form_without_year_evidence=8`,
  `non_target_candidates_only=3`, `site_fetch_error_only=1`, and
  `no_evidence=1`. The `no_evidence` row is the one official-index site outside
  the bounded `batch_size=50` smoke: 埼玉福祉保育医療製菓調理専門学校
  (`school_id=2399`).
- The v342 RCA batch plan has `10` items / `50` total candidates. Bucket split:
  `target_form_without_year_evidence=8`, `non_target_candidates_only=2`.
  Representative rows show that the low strict yield is dominated by forms that
  are visible but cannot prove FY2026 from PDF/link evidence: 埼玉コンピュータ＆
  医療事務専門学校 `補正➅確認申請書（様式第2号）.pdf`,
  専門学校埼玉自動車大学校 `koutoumusyou.pdf`, 上尾中央看護専門学校
  `study_support_system.pdf`, 中央情報専門学校 `youshiki2.pdf`, and
  さいたま看護専門学校 `申請書_0602_資料A.pdf`. The two non-target-only packets
  are 大川学園医療福祉専門学校 (old-year image-only form evidence) and
  呉竹医療専門学校 (self-evaluation reports).

Additional v342 Tokyo official-index probe:

- `scripts\bootstrap_pdfs.bat --pref tokyo --skip-known-url-discovery --url-search off --school-url-crawl off --skip-discover --rate-limit 0.2 --request-timeout 15`
  -> exit `0`.
- Official Tokyo artifact downloaded from
  `https://www.seikatubunka.metro.tokyo.lg.jp/documents/d/seikatubunka/12syugakushien_kakuninko_ichiran_260401_1341`;
  aggregate `extracted=243`, `matched=232`, `added=232`, `skipped=11`.
- A targeted 30-site discovery run over the first Tokyo
  `prefecture_aggregator` sites used:
  `eidp.exe discover-pdfs --discovery-method prefecture_aggregator --batch-size 30 --rate-limit 0.2 --request-timeout 15 --evidence-log output\discovery_rejections_tokyo_v342_30.jsonl --school-id ...`
  -> exit `0`.
- PDF discovery: `crawled=30`, `found=30`, `downloaded=0`, `failed=5`,
  `skipped=524`, `cached_rejections=88`, `prefiltered=293`,
  `candidate_budget_limited=1`, `candidate_budget_dropped=6`,
  `candidate_school_mismatch=1`, `rejection_reason_pre_filtered_non_target_hint=371`,
  `rejection_reason_fiscal_year_mismatch=76`,
  `rejection_reason_target_fiscal_year_not_detected=19`,
  `rejection_reason_classified_non_target=118`,
  `rejection_reason_http_error_httpstatuserror=3`,
  `rejection_reason_not_pdf_magic=2`, and `rejection_reason_unsafe_url=2`.
- Local evidence snapshot was pulled to `_temp/win-v342-tokyo-probe/`,
  including `discovery_rejections_tokyo_v342_30.jsonl`,
  `eidp-after-tokyo-aggregate.sqlite3`, and
  `eidp-after-tokyo-discover.sqlite3`.
- Reproducible summary command:
  `EIDP_DATABASE_URL=sqlite:///$PWD/_temp/win-v342-tokyo-probe/eidp-after-tokyo-discover.sqlite3 uv run eidp summarize-discovery-evidence --evidence-log _temp/win-v342-tokyo-probe/discovery_rejections_tokyo_v342_30.jsonl --json`.
  It reports `598` evidence rows, `30` schools with evidence, PDF type counts
  `target=80`, `image_only=15`, `non_target=490`, `unknown=7`, and `null=6`,
  and school bucket counts `publication_lag_or_old_target_pdf=19`,
  `target_form_without_year_evidence=6`, `non_target_candidates_only=5`.
- Reproducible RCA command:
  `EIDP_DATABASE_URL=sqlite:///$PWD/_temp/win-v342-tokyo-probe/eidp-after-tokyo-discover.sqlite3 uv run eidp discovery-rca-batch-plan --evidence-log _temp/win-v342-tokyo-probe/discovery_rejections_tokyo_v342_30.jsonl --limit 10 --json`.
  Representative target-form-without-year-evidence rows are
  東京俳優・映画＆放送専門学校 `conf-apl.pdf`,
  東京ダンス・俳優＆舞台芸術専門学校 `check-da.pdf`, and
  東京メディカル・スポーツ専門学校 `support2024.pdf`.
- The Tokyo sample reinforces the Saitama result: official-index URL seeding is
  functioning, and low strict yield is currently dominated by publication lag,
  stale target forms, image-only / no-year target forms, and non-target
  disclosure PDFs rather than by a missing official-index URL pipeline.

Superseded bounded bootstrap evidence from v341:

Commands and observations from `ssh win` for v341 setup/bootstrap:

- `scripts\bootstrap_pdfs.bat --pref saitama --skip-known-url-discovery --url-search off --school-url-crawl off --batch-size 50 --rate-limit 0.2 --request-timeout 15` -> exit `0`.
- Official Saitama artifact downloaded; aggregate `extracted=58`,
  `matched=51`, `added=51`, `review_items=2`.
- PDF discovery: `crawled=50`, `found=49`, `downloaded=0`, `failed=3`,
  `skipped=1391`, `prefiltered=1055`, `cached_rejections=285`,
  `candidate_school_mismatch=5160`, `candidate_budget_dropped=855`,
  `rejection_reason_discovery_error=1`,
  `rejection_reason_pre_filtered_non_target_hint=1062`,
  `rejection_reason_fiscal_year_mismatch=327`,
  `rejection_reason_target_fiscal_year_not_detected=32`,
  `rejection_reason_unsafe_url=1`.
- Ingest: `processed=0`, `departments_created=0`, `yearly_upserted=0`,
  `skipped=0`.
- Rebuilt status: `excel_ready=0`, `target_pdf_auto_acquired_count=0`,
  `operator_reviewable_count=45`, `operator_reviewable_yield_pct=1.9`,
  `ship_gate_status=below_gate`.
- Diagnostics after bootstrap:
  `validate_after_bootstrap_rc=0`,
  `validate_after_bootstrap_ship_gate_rc=1`.
- Local evidence snapshot was pulled to `_temp/win-v341-evidence/`, including
  `bootstrap-pdfs-20260513-064933.log`, `bootstrap-pdfs-20260513-064933.json`,
  `bootstrap-20260513_070621-discovery-rca-batch-plan.json`,
  `discovery_rejections.jsonl`, and `eidp.sqlite3`.
- v341 evidence confirms Kanto is no longer dropped by neighboring disclosure-card
  noise: `j2024_05a.pdf` appears with `score=2.5`, `pdf_type=image_only`,
  and `reason=fiscal_year_mismatch:2024`.

Superseded bounded bootstrap evidence from v340:

Commands and observations from `ssh win` for v340 setup/bootstrap:

- Uploaded `dist/eidp-windows-v340.zip` to
  `C:\Users\cyo20\eidp-windows-v340.zip`.
- Windows `Get-FileHash -Algorithm SHA256` ->
  `4d774c10c5b0743c3eff22ac224489407f06f3653d081c7133ba8ecbed56405e`.
- Extracted to `C:\Users\cyo20\EIDP-v340-2097ad6`.
- `scripts\first_setup.bat` -> exit `0`; core and after-setup validators
  returned `0`, reported commit `2097ad6ac6f80c236494f4fa439e0c2113302920`,
  `build_dirty=false`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`,
  required SQLite tables present, `department_change` void columns present,
  and `uq_document_file_hash` present.
- `scripts\bootstrap_pdfs.bat --pref saitama --skip-known-url-discovery --url-search off --school-url-crawl off --batch-size 50 --rate-limit 0.2 --request-timeout 15` -> exit `0`.
- Official Saitama artifact downloaded; aggregate `extracted=58`,
  `matched=51`, `added=51`, `review_items=2`.
- PDF discovery: `crawled=50`, `found=49`, `downloaded=0`, `failed=4`,
  `skipped=1387`, `prefiltered=1055`, `cached_rejections=286`,
  `candidate_school_mismatch=5160`, `candidate_budget_dropped=853`,
  `rejection_reason_discovery_error=1`,
  `rejection_reason_pre_filtered_non_target_hint=1060`,
  `rejection_reason_fiscal_year_mismatch=330`,
  `rejection_reason_target_fiscal_year_not_detected=31`,
  `rejection_reason_unsafe_url=1`.
- Ingest: `processed=0`, `departments_created=0`, `yearly_upserted=0`,
  `skipped=0`.
- Rebuilt status: `excel_ready=0`, `target_pdf_auto_acquired_count=0`,
  `operator_reviewable_count=45`, `operator_reviewable_yield_pct=1.9`,
  `ship_gate_status=below_gate`.
- SQLite status rows: `none=2373`, `publication_lag=38`,
  `target_year_unverified=7`; the seven 年度未確認候補 schools are
  上尾中央看護専門学校, 浦和専門学校, 大宮歯科衛生士専門学校,
  公益社団法人地域医療振興協会さいたま看護専門学校,
  埼玉コンピュータ＆医療事務専門学校, 専門学校埼玉自動車大学校,
  and 中央情報専門学校.
- Diagnostics after bootstrap:
  `validate_core_rc=0`, `validate_after_setup_rc=0`,
  `validate_after_bootstrap_rc=0`,
  `validate_after_bootstrap_ship_gate_rc=1`.
- ARS/アルスコンピュータ evidence in `discovery_rejections.jsonl`:
  the R7 target-form PDF is rejected as `fiscal_year_mismatch:2025`, while
  current-year `R8_IT_0420.pdf` and `R8_GB_0420.pdf` are rejected before
  download as `pre_filtered_non_target_hint` syllabus/course-plan PDFs.
- Local evidence snapshot was pulled to `_temp/win-v340-evidence/`, including
  `bootstrap-pdfs-20260513-061039.log`, `bootstrap-pdfs-20260513-061039.json`,
  `bootstrap-20260513_062725-discovery-rca-batch-plan.json`,
  `discovery_rejections.jsonl`, and a copy of `eidp-v340.sqlite3`.

Superseded v333 setup/bootstrap evidence:

- Uploaded `dist/eidp-windows-v333.zip` to
  `C:\Users\cyo20\eidp-windows-v333.zip`.
- Windows `Get-FileHash -Algorithm SHA256` ->
  `70211256799674031CEBE671732212D1C4F30DD6058B6EBBE48BF53DEBD83F7F`.
- Extracted to `C:\Users\cyo20\EIDP-v333-422741d`.
- `scripts\first_setup.bat` -> exit `0`; after-setup validator reported
  commit `422741d9f9cff64bdd67a9987654bd4963fdac52`,
  `build_dirty=false`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`,
  required SQLite tables present, `department_change` void columns present,
  and `uq_document_file_hash` present.
- Windows `eidp discovery-gold-set --json` reports `23` entries,
  `publication_lag_latest_public=9`, and demonstrated extractor sources
  `embed` plus `wordpress_download_manager`.
- `scripts\bootstrap_pdfs.bat --pref saitama --skip-known-url-discovery --url-search off --school-url-crawl off --batch-size 50 --rate-limit 0.2 --request-timeout 15` -> exit `0`.
- Official Saitama artifact downloaded; aggregate `extracted=58`,
  `matched=51`, `added=51`, `review_items=2`.
- PDF discovery: `crawled=50`, `found=49`, `downloaded=0`, `failed=4`,
  `skipped=1380`, `prefiltered=1048`, `cached_rejections=286`,
  `candidate_school_mismatch=5160`, `candidate_budget_dropped=853`,
  `rejection_reason_discovery_error=1`,
  `rejection_reason_fiscal_year_mismatch=330`,
  `rejection_reason_target_fiscal_year_not_detected=31`,
  `rejection_reason_unsafe_url=1`.
- Ingest: `processed=0`, `departments_created=0`, `yearly_upserted=0`,
  `skipped=0`.
- Rebuilt status: `excel_ready=0`, `target_pdf_auto_acquired_count=0`,
  `operator_reviewable_count=38`, `operator_reviewable_yield_pct=1.6`,
  `ship_gate_status=below_gate`.
- Diagnostics after bootstrap:
  `validate_core_rc=0`, `validate_after_setup_rc=0`,
  `validate_after_bootstrap_rc=0`,
  `validate_after_bootstrap_ship_gate_rc=1`, `ship_readiness_rc=1`.
- Local evidence snapshot was pulled to `_temp/win-v333-evidence/`, including
  `bootstrap-pdfs-20260513-042824.log`, `bootstrap-pdfs-20260513-042824.json`,
  `diagnostics-20260513-044537.txt`, the RCA batch plan,
  `discovery_rejections.jsonl`, and a copy of `eidp.sqlite3`. SQLite checks on
  that snapshot report `2418` schools, `51` school sites, `0` documents, `0`
  PDF-derived current 2026 DepartmentYearly rows, `2418` 2026 school status
  rows, `0` Excel-ready schools, and `2` pending review items.
- The v332 false-positive downloaded URLs now appear in
  `discovery_rejections.jsonl` as `target_fiscal_year_not_detected`, for
  example 上尾中央看護専門学校 `study_support_system.pdf`, さいたま看護専門学校
  `申請書_0602_資料A.pdf`, 幸手看護専門学校
  `高等教育無償化更新確認申請書 様式第2号の1～4.pdf`, 専門学校埼玉自動車大学校
  `koutoumusyou.pdf`, and 中央情報専門学校 `youshiki2.pdf`.

## Previous Windows Bootstrap Evidence With Superseded Strict-Year Behavior

v332/v331 both showed `downloaded=7` / `excel_ready=5` on the same bounded
Saitama sample, but v333 proved those were false-positive strict-year successes:
the accepted evidence used `year_evidence=prefecture_index_current_year` with
empty `detected_fiscal_year`. That behavior is intentionally superseded by
v333.

Earlier commands and observations from `ssh win` for v331 setup/bootstrap:

- Uploaded `dist/eidp-windows-v331.zip` to
  `C:\Users\cyo20\eidp-windows-v331.zip`.
- Windows `Get-FileHash -Algorithm SHA256` ->
  `455C562901B0361E68BE6DD00084FD89F2DE33DF09670246168E910DCFB09186`.
- Extracted to `C:\Users\cyo20\EIDP-v331-9730b5a`.
- `scripts\first_setup.bat` -> exit `0`; after-setup validator reported
  commit `9730b5acc097b19d26a2b2db6a7d8212bca6483a`,
  `build_dirty=false`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`,
  required SQLite tables present, `department_change` void columns present,
  and `uq_document_file_hash` present.
- Read-only v331 Windows discovery probe for the prior three
  `site_fetch_error_only` rows:
  - school `760` now returns `error=null`, `candidates=2`, best
    `https://i-heiseigakuen.ac.jp/download/yousiki2/?wpdmdl=5471&refresh=...`;
  - school `767` returns `error_code=robots_disallow_all`, `retryable=false`;
  - school `785` now returns `error=null`, `candidates=27`, best
    `https://nihon-ika.ac.jp/wp/wp-content/uploads/2025/08/⑮2025年更新確認申請書.pdf`.
  The subsequent bounded bootstrap confirms two v330 timeout rows were transient
  fetch failures, while the Kitasato row is a real robots-policy block.
- `scripts\bootstrap_pdfs.bat --pref saitama --skip-known-url-discovery --url-search off --school-url-crawl off --batch-size 50 --rate-limit 0.2 --request-timeout 15` -> exit `0`.
- Official Saitama artifact downloaded; aggregate `extracted=58`,
  `matched=51`, `added=51`, `review_items=2`.
- PDF discovery: `crawled=50`, `found=49`, `downloaded=7`, `failed=4`,
  `skipped=1235`, `prefiltered=919`, `cached_rejections=286`,
  `candidate_school_mismatch=5160`, `candidate_budget_dropped=853`,
  `rejection_reason_discovery_error=1`,
  `rejection_reason_fiscal_year_mismatch=326`,
  `rejection_reason_target_fiscal_year_not_detected=22`,
  `rejection_reason_unsafe_url=1`.
- Ingest: `processed=7`, `departments_created=12`, `yearly_upserted=18`,
  `skipped=1`.
- Rebuilt status: `excel_ready=5`, `target_pdf_auto_acquired_count=5`,
  `operator_reviewable_count=41`, `operator_reviewable_yield_pct=1.7`,
  `ship_gate_status=below_gate`.
- Diagnostics after bootstrap:
  `validate_core_rc=0`, `validate_after_setup_rc=0`,
  `validate_after_bootstrap_rc=0`,
  `validate_after_bootstrap_ship_gate_rc=1`, `ship_readiness_rc=1`.
- DB evidence after the 50-site run has `Document=7`: `5` ingested,
  `1` review-pending, and `1` school-mismatch.
- The malformed raw URL from 越生自動車大学校 was recorded as
  `unsafe_url`:
  `http://www.ogo\nsejidai.ac.jp/wordpress/wp-content/uploads/2019/08/e46236c71464104f59caea652d9567e3.pdf`.
- Evidence review confirmed stale-label rejection: the prior v324 false
  acceptance `R7確認申請書類 様式第2号` is now recorded as
  `fiscal_year_mismatch:2025`.
- The v331 RCA batch plan has `10` items / `43` actionable candidates. Top
  buckets include `target_form_without_year_evidence` for 浦和専門学校 and
  大宮歯科衛生士専門学校, `non_target_candidates_only` for several schools,
  and `publication_lag_or_old_target_pdf` for 東京IT会計公務員専門学校大宮校.

## Next Required Proof

1. Run browser UI operator click-through on the current Windows install:
   `EIDP-start.bat` -> operator pages -> Excel preview/download -> diagnostics.
2. Expand Windows official-index discovery beyond the 50-site Saitama bounded
   smoke and record target PDFs accepted, publication-lag queue,
   manual-required queue, and errors.
3. Repeat the v342 RCA batch-plan classification on a larger official-index
   sample to quantify whether low strict-target result remains dominated by
   upstream publication lag / missing PDF-year evidence rather than crawler
   false negatives.
4. Compare measured operator-reviewable coverage, manual workload, and Excel
   readiness against the shipping line; keep strict target-PDF acquisition as a
   diagnostic metric during the May publication-lag window.
5. Only after those numbers pass should the branch be treated as release-ready.

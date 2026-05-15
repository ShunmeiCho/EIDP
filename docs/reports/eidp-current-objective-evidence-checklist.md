# EIDP Current Objective Evidence Checklist

Updated: 2026-05-15
Latest Mac/non-Windows package snapshot: `09ad5e6bfa80c8a03ab6f60b2f39a39333fdd42c`
Status: **NOT COMPLETE**

This checklist maps the long-term EIDP objective to concrete artifacts and gates.
It is intentionally explicit about lane boundaries: the active operator-PC
Stage 6 setup/UI lane is now `C:\Users\cyo20\EIDP-v408-f0c27158` for
`dist/eidp-windows-v408.zip` / code evidence base `f0c27158`. v415 is the
latest Mac/non-Windows release-gate-clean package for the current source lane,
but it has no Windows transfer/setup/UI proof because SSH-Win is currently
disconnected. v408 now has R7 CLI Excel parity, R7 browser Excel download proof,
a disposable copied-DB UI write/audit sandbox proof, and a verifier-accepted
non-Excel diagnostic evidence bundle; the real operator cycle is still missing.
v415 includes the post-v410 non-runtime test-timeout, coverage-gate,
optional-adapter test, local-ignore, docs-only stale-package replay, and
`diff-excel --json` diagnostics commits, plus the legacy Venus multi-method
rediscovery cron fix. Its packaged `BUILD_INFO.json` records snapshot
`09ad5e6bfa80c8a03ab6f60b2f39a39333fdd42c`.

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
| Strict target-FY PDF discovery excludes stale fallback from success | `src/eidp/scraper/pdf_discovery.py`; `src/eidp/scraper/discovery_evidence_summary.py`; `tests/unit/test_pdf_discovery.py`; v375 heading/update-date tests pass; source HEAD also guards romanized-only renewal-form hints in both strong application and weak form-shape detection, prioritizes yearless target-form evidence over older-year target evidence in RCA triage, and inherits same-section support-system headings for year-only target-form links so they enter the download budget before generic `様式4` PDFs | Mechanically guarded; yield gate failing |
| PDF extraction uses pdfplumber / PyMuPDF / Tesseract and writes only confidence >= 0.70 | OCR/package verifier contracts; v384 OCR image/write smoke; unit coverage for confidence propagation; source HEAD names the default `0.70` review threshold via `DEFAULT_CONFIDENCE_REVIEW` and keeps Excel/exporter env-threshold tests green | Mechanically proven for smokes; no current strict target-form OCR workload evidence |
| DepartmentYearly / SupportRecipient append-only writes | Unit coverage plus v384 copied-DB UI/manual-entry, fiscal override, and SupportRecipient ingest smokes; v407 disposable operator-PC UI sandbox proved manual-entry write and fiscal-year override clones for DepartmentYearly, SupportRecipient, and SchoolYearStatus with prior FY2024 rows marked non-current; current v408 disposable UI sandbox repeated the browser-write surface with one manual FY2025 `DepartmentYearly` row (`capacity=40`, `enrollment=28`, `extraction_method=manual`, `extraction_confidence=1.0`, `verified=true`) and one fiscal-year override that marked FY2024 `DepartmentYearly`, `SupportRecipient`, and `SchoolYearStatus` rows non-current while FY2025 current rows were present | Proven on sandboxed/copy DB paths including current v408; real operator one-cycle proof still missing |
| Excel template export | v384 R7 retroactive Excel preview/download proof; v408 Windows R7/FY2025 CLI export wrote `v408-r7-retroactive-export.xlsx` with `採録状況=2418`, `対象比率=10022`, `学科別=9719`, `在籍のみ抜粋=9719`; v408 business diff against the proven v407 R7 export returned `missing_sheets=0`, `extra_sheets=0`, `missing_rows=0`, `extra_rows=0`, and `differing_fields=0`; `openpyxl` opened the v408 CLI workbook at `3,673,084` bytes with sheet dimensions `2419x10`, `10023x22`, `9721x83`, `9721x19`; v415 integrated non-Windows release gate created isolated app root `_temp/non-windows-retroactive-fy2025-20260515-123749`, imported `data/master.xlsx`, exported FY2025 with the same row counts, and the `retroactive_excel_diff_reference` gate returned zero missing/extra rows and zero differing fields against `_temp/v408-r7-cli-export.xlsx`; v414 FY2024/FY2023 raw-sample reference preflights also generated isolated exports with the same row counts, but intentionally failed against the unprepared raw `sample/◆2025専門学校無償化情報公開まとめ.xlsx` workbook (`FY2024: missing_rows=1097 extra_rows=1557 differing_fields=12548`; `FY2023: missing_rows=1097 extra_rows=1557 differing_fields=9718`), proving reference-preparation work remains before N=3 pass/fail gates; v408 real-install browser R7 preview/download generated `_temp/v408-r7-browser-eidp_master.xlsx`, suggested `eidp_master.xlsx`, and matched the v408 CLI export with `missing_sheets=0`, `extra_sheets=0`, `missing_rows=0`, `extra_rows=0`, and `differing_fields=0`; v407 disposable UI sandbox generated a smaller Excel preview workbook with `採録状況=2`, `対象比率=1`, `学科別=2`, and `在籍のみ抜粋=2`; FY2026 export remains disabled with `Excel出力可 0/2418` on current setup evidence | R7 CLI export/diff and browser download proven on v408; v415 source-lane retroactive FY2025 export is regression-clean vs v408; FY2024/FY2023 raw sample is diagnostic-only until canonical references are prepared; FY2026 target-year output not ready |
| ManualActionLog audits every operator action | v384 manual-entry, fiscal override, URL-candidate reject, and audit outbox browser smokes; source HEAD dedups audit outbox archives by matching filename stem for both default and custom outbox paths and ignores archive symlinks; v407 disposable UI sandbox flushed seven operator actions with `exported=7 already_present=0 failed=0` and `jsonl_exported_at_present=true` for all seven rows; current v408 disposable UI sandbox repeated the audit path through `監査ログ`, showing `JSONL outbox 未送信=7`, `Outbox を flush` result `exported=7 already_present=0 failed=0`, and seven rows with `jsonl_exported_at_present=true` in direct DB verification | Proven on sandboxed paths including current v408; real operator one-cycle proof still missing |
| ZIP distribution, double-click setup, browser UI offline operation | v408 transfer, SHA match, setup completion, SQLite integrity, scheduled-task action update to `C:\Users\cyo20\EIDP-v408-f0c27158\scripts\weekly_run.bat`, packaged recovery checker proof, Streamlit health, `18508 -> 8508` tunnel health, default `EIDP-start.bat` / `18501 -> 8501` launcher health, v408 R7 browser Excel proof through `18509 -> 8509`, v408 disposable UI write/audit proof through `18510 -> 8510`, and v408 non-Excel diagnostic bundle `logs\stage6-evidence-20260514-190257.zip` verified by `logs\stage6-evidence-verify-20260515-040322.json` with `ok=true`, no forbidden/unsafe entries, and labels `build_info`, `diagnostics`, `last_run`, `stage6_recovery`, `stage6_residual_cleanup`, and `weekly_run_logs`; v407 verifier-accepted diagnostic bundle `logs\stage6-evidence-20260514-174859.zip` and sandbox proof remain historical support; v397 browser read-only navigation retained as historical support | Current v408 setup/service/recovery/UI-health, default launcher, R7 browser Excel, sandbox browser-write/audit, and diagnostic evidence bundle proven; real operator one-cycle missing |
| Stage 6 one operator-PC cycle | `docs/runbooks/eidp-operator-e2e-template.md`; `docs/reports/current-release-status.md` Stage 6 boundary | Missing |
| Ship gate: true target-form auto-acquisition 60-70% | Latest recorded strict target PDF auto-yield remains `0.0%`; `ship_readiness_rc=1` in current Windows evidence | Failing |
| Ship gate: estimated manual work <= 30% | Current evidence records operator-reviewable yield far below release threshold and manual workload effectively above target | Failing |

## Current Release Boundary

- Current Mac/non-Windows release-gate proof: v415, package snapshot
  `09ad5e6bfa80c8a03ab6f60b2f39a39333fdd42c`, app-code evidence base
  `15c88348f46ab3fbcc9383afe5830047e562b0c1`, SHA256
  `25478903757785bec4ab34583878e0af344ceffc1f153a7de5ef219584d11ffd`.
  `scripts/verify_windows_distribution.py dist/eidp-windows-v415.zip --json`
  returned `ok=true`, `git_dirty=false`, `wheel_count=78`, and
  `discovery_gold_set_entries=44`. `scripts/run_non_windows_release_gates.py
  dist/eidp-windows-v415.zip --retroactive-excel-reference
  _temp/v408-r7-cli-export.xlsx --retroactive-fiscal-year 2025 --json --output
  logs/release-gate-v415-retroactive.json`
  returned `ok=true`, with `source_dirty=false`, `stale=false`, `tests/unit -q`
  returning `1537 passed`, validator/distribution tests returning `161 passed`,
  validator/distribution mypy and Ruff passing, expected discovery-gold
  predictions matching `44/44`, and the demonstrated-pattern package verifier
  passing. v415 also has integrated isolated Mac retroactive FY2025/R7
  import/export proof under `_temp/non-windows-retroactive-fy2025-20260515-123749`:
  import produced `対象比率=10022`, `学科別=9719`, `DepartmentYearly=40731`,
  and `SupportRecipient=10022`; export wrote `採録状況=2418`,
  `対象比率=10022`, `学科別=9719`, and `在籍のみ抜粋=9719`; and
  `retroactive_excel_diff_reference` returned zero missing/extra rows and zero
  differing fields against `_temp/v408-r7-cli-export.xlsx`. v415 is not
  Windows-proven.
- Post-v410 non-runtime hardening included in v415: Streamlit AppTest cold-start timeout
  budget was raised from `15s` to `30s` for UI smoke tests, with
  `uv run pytest tests/unit/test_review_school_year_tasks.py
  tests/unit/test_review_pdf_manual_entry.py -q` returning `100 passed`;
  optional Scrapling and OCR-runtime boundary tests now keep the local coverage
  line above the configured threshold; `[tool.coverage.report] fail_under = 80`
  is set in `pyproject.toml`; `uv run pytest --cov=src/eidp --cov-report=term`
  returned `1530 passed`, `TOTAL 14186 2837 80%`, and `Total coverage: 80.00%`;
  local runtime/tool artifacts are ignored narrowly via `.gitignore`.
- Active Windows transfer/setup/UI-health proof: v408, commit
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
- Current source-code evidence base: `15c88348`, with post-v408 source-only
  coverage recovery plus Stage 6 safety fixes for recovery check,
  evidence bundle Excel exclusion, residual cleanup symlink/junction safety,
  clarified ship-readiness criteria semantics, audit outbox custom-archive
  dedup, stricter romanized renewal-form hint handling across strong and weak
  target-form hint paths, operator-facing PDF discovery reason labels in the
  school task-board detail panel, and typed fiscal-year
  override / PDF ingest / PDF OCR / Excel exporter / Excel import stats /
  manual audit / operator UI / bootstrap URL crawl / append-only audit-helper
  paths, plus unit-test isolation for Streamlit AppTest's fake `__main__`
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
  named constants used by `ConfidenceThresholds`. The packaged ZIP verifier now
  requires default Stage 6 tunnel guidance for `18501 -> 8501` in both the
  operator runbook and E2E evidence template. The non-Windows release gate also
  keeps `--allow-stale-package` dirty-safe: it can bypass a historical package
  commit mismatch, but still rejects uncommitted tracked source. The Windows
  install validator also rejects `last_run.json status=lock_busy` as weekly
  ship-gate evidence even if the payload claims `ship_gate_status=pass`. For
  bootstrap release-gate checks, progress-count mismatches against SQLite are
  fatal under `--require-ship-gate` while remaining warnings for structure-only
  validation.
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

Latest v415 Mac/non-Windows release-gate evidence, latest v408 setup/UI lane
evidence, and v407 supporting diagnostic evidence are summarized in
`docs/reports/current-release-status.md`. The retained detailed local checks
below include source-code evidence base `4a16363d` and later refreshes:

- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v415.zip --latest-alias`
  -> wrote `dist/eidp-windows-v415.zip`, refreshed `dist/eidp-windows.zip`,
  and wrote `dist/eidp-windows-v415.zip.sha256`.
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v415.zip --retroactive-excel-reference _temp/v408-r7-cli-export.xlsx --retroactive-fiscal-year 2025 --json --output logs/release-gate-v415-retroactive.json`
  -> `ok=true`, SHA256
  `25478903757785bec4ab34583878e0af344ceffc1f153a7de5ef219584d11ffd`,
  packaged/source commit `09ad5e6bfa80c8a03ab6f60b2f39a39333fdd42c`,
  `package_source_check.stale=false`, `tests/unit -q` reported `1537 passed`,
  validator/distribution tests reported `161 passed`, validator/distribution
  mypy and Ruff passed, discovery-gold expected predictions were `44/44`,
  package verification with `--require-demonstrated-discovery-patterns` passed,
  and `retroactive_excel_diff_reference` returned zero missing/extra rows and
  zero differing fields against `_temp/v408-r7-cli-export.xlsx`.
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v415.zip --skip-full-unit --allow-docs-only-stale-package --json --output logs/release-gate-v415-docs-only-stale-after-sha-sidecar-note.json`
  -> `ok=true`; SHA256 sidecar matched; `package_source_check` reported
  `stale=true`, `docs_only_stale=true`, `source_dirty=false`,
  `allowed_stale_reason=docs_only`, and changed paths limited to release/status
  documentation under `docs/`; validator/distribution tests reported
  `161 passed`, validator/distribution mypy and Ruff passed, discovery-gold
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
  -> `163 passed, 5 warnings in 11.00s`.
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
  tree and passes across 83 source files. This is still Mac-side evidence only;
  it does not prove the real Windows operator-PC Stage 6 one-cycle or the
  rolling FY yield gate. The current-package v408 browser-write proof is
  sandbox-only, and the v408 evidence bundle is dry-run diagnostic evidence;
  neither must be treated as a real operator-cycle sign-off.

## Next Concrete Gate

When SSH-Win is available again, start the next Windows execution lane from the
latest Mac/non-Windows-clean package, v415. v408 remains the latest
Windows-proven setup/UI evidence lane and can be used as historical support,
but it should not be treated as the final v1.0 real-cycle package unless the
owner explicitly decides to freeze on v408.

First transfer and verify `dist/eidp-windows-v415.zip`:

```text
Package snapshot: 09ad5e6bfa80c8a03ab6f60b2f39a39333fdd42c
Expected SHA256: 25478903757785bec4ab34583878e0af344ceffc1f153a7de5ef219584d11ffd
Suggested extract path: C:\Users\cyo20\EIDP-v415-09ad5e6b
```

Then start the operator UI tunnel after Windows setup/validation has passed:

```bash
ssh -N -o ClearAllForwardings=no -o ExitOnForwardFailure=yes -L 127.0.0.1:18501:127.0.0.1:8501 win
```

Then verify the UI at `http://127.0.0.1:18501/` and complete the Stage 6
click-through against the real v415 operator cycle or an approved full-cycle copy:
manual PDF entry write, fiscal-year override write, R7 Excel preview/download,
audit log/outbox flush, diagnostics capture, evidence verify, and sign-off
fields.

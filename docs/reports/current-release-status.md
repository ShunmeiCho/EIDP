# EIDP Current Release Status

Updated: 2026-05-13
Branch: `sprint8-handoff-finalize`
Current Mac-verifier-clean package: `dist/eidp-windows-v359.zip`
Package commit: `0b2c4c295e996c3fd4be5ee287ff4e77ceeacde7`
Package SHA256: `b6a76c3fd85ba87bdb1b639996811fd6ef72eb1d686eec22b9ae71c1e7dec337`
Latest Windows-core-validated package: `dist/eidp-windows-v342.zip`
Latest Windows-setup-proven package: `dist/eidp-windows-v342.zip`
Latest Windows-bounded-bootstrap-proven package: `dist/eidp-windows-v342.zip`

## Verdict

Status: **NOT COMPLETE**

The current Mac-verifier-clean ZIP snapshot is v359 and passes the default
macOS package verifier, including `--require-demonstrated-discovery-patterns`.
The latest Windows setup and bounded-bootstrap proof remains v342.
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
still not complete: browser UI operator
click-through is missing, and the measured
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

## Objective Checklist

| Requirement | Current evidence | Status |
| --- | --- | --- |
| 47 prefecture official indexes seed school public URLs | v342 verifier: `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`, `prefecture_seed_school_rows_total=2148`; Windows v342 Saitama run downloaded the current official artifact and added `51` `SchoolSite` rows from `58` extracted / `51` matched rows | Evidence present |
| Discover and download current target-FY PDFs in strict mode | v359 verifier clean by default; discovery gold-set `36` entries / `8` strict target-year successes; source-side 聖十字 replay crawled `1`, found `1`, downloaded `1`, and gold-set evidence replay matched the accepted target PDF exactly; source-side 更生 replay crawled `1`, found `1`, downloaded `1`, and gold-set evidence replay matched the accepted target PDF exactly; source-side 中央情報 replay crawled `1`, found `1`, downloaded `1`, and gold-set evidence replay matched the accepted target PDF exactly; source-side 君津 replay crawled `1`, found `1`, downloaded `1`, and gold-set evidence replay matched the accepted target PDF exactly; current Tokyo Anime HTML probe ignores the commented-out old `07_study_support_application.pdf` link while keeping visible confirmation-form links; Windows v342 Saitama 50-site run crawled `50` official-index sites, found candidates on `49`, downloaded `0`, processed `0`, and produced `0` Excel-ready schools after removing false-positive prefecture-index year fill; Windows v342 Tokyo 30-site probe found candidates on all `30` sites and downloaded `0`; a source-side v348 Tokyo 20-site repeat crawled `20`, found candidates on all `20`, downloaded `0`, and reproduced the same publication-lag / stale-year / no-year target-form distribution; Windows v342 evidence proves Kanto/Iruma context fixes without accepting old-year PDFs as current-FY success | Mechanically proven, strict yield still failing at workload scale |
| Exclude stale-year fallback from auto-success | Ship gate uses operator-reviewable coverage, while strict auto-yield remains diagnostic; gold-set includes `11` publication-lag cases; Windows v333/v339/v340 evidence records prior false-success or stale-year URLs as `target_fiscal_year_not_detected` / `fiscal_year_mismatch:*` instead of `accepted_downloaded`; malformed raw URLs are recorded as `unsafe_url` instead of aborting the batch | Evidence present |
| Extract with pdfplumber/PyMuPDF/Tesseract and write only confidence >= 0.70 rows | Unit/package gates cover OCR runtime presence and confidence contracts; Windows v340 Saitama 50-site run produced no strict target PDFs, so no PDF-derived yearly rows were written; this avoids v332's false-positive `18` current rows | Mechanically proven, no current strict target data |
| Append-only DepartmentYearly / SupportRecipient writes | Fresh full unit suite passed; source audits and targeted tests cover demote-plus-new-revision paths in ingest, manual entry, and fiscal-year override | Evidence present, Win UI E2E still missing |
| Excel template output | v342 package verifier includes Excel/export contracts and centralized confidence threshold contract; current operator-PC preview/download flow is not revalidated on v333/v339/v340/v341/v342 | Partially proven |
| ManualActionLog audit for operator actions | v342 package verifier includes audit contracts and outbox checks; current operator-PC run not revalidated through browser UI on v333/v339/v340/v341/v342 | Partially proven |
| ZIP distribution, double-click setup, browser UI offline operation | v342 ZIP verifies clean on macOS packaging gate; v342 was transferred to Windows with matching SHA256, extracted to `C:\Users\cyo20\EIDP-v342-de2cfed`, and `scripts\first_setup.bat` completed successfully; browser UI click-through remains unverified | Backend Win setup proof present, UI proof missing |
| Shipping threshold: operator-reviewable coverage sufficient for operator manual work <=30%, with strict Excel readiness retained as diagnostic output | v358 `ship-readiness` now reports `ok_operator_review` separately from `ok_strict`; Windows v342 50-site diagnostics report `target_pdf_auto_yield_pct=0.0`, `operator_reviewable_yield_pct=1.9`, `excel_ready=0`, `ship_gate_status=below_gate`, and `validate_after_bootstrap_ship_gate_rc=1` | Failing on latest Windows evidence |

## Current Non-Windows Evidence

Runbook: `docs/runbooks/eidp-non-windows-release-gates.md`.

Latest v359 commands:

- `uv run pytest tests/unit -q` -> `1367 passed, 5 warnings`
- `uv run pytest tests/unit/test_cli_reports.py tests/unit/test_cli_write_lock_contract.py tests/unit/test_windows_distribution_verifier.py -q`
  -> `96 passed`
- `uv run ruff check src/eidp/cli.py src/eidp/cli_reports.py scripts/verify_windows_distribution.py tests/unit/test_cli_reports.py tests/unit/test_cli_write_lock_contract.py tests/unit/test_windows_distribution_verifier.py`
  -> `All checks passed`
- `uv run mypy src/eidp/cli.py src/eidp/cli_reports.py scripts/verify_windows_distribution.py`
  -> `Success: no issues found in 3 source files`
- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v359.zip`
  -> wrote `dist/eidp-windows-v359.zip` and checksum sidecar.
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v359.zip --json --output _temp/v359-non-windows-release-gates-full.json`
  -> `ok=true`, SHA256 sidecar matched, full unit passed, package verifier passed, and demonstrated-pattern gate passed.
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v359.zip --pdf-evidence _temp/win-v342-tokyo-probe/discovery_rejections_tokyo_v342_30.jsonl --pdf-evidence _temp/win-v342-evidence/discovery_rejections.jsonl --pdf-evidence _temp/seijuji-gold-v2/discovery_evidence.jsonl --pdf-evidence _temp/kousei-gold-v2/discovery_evidence.jsonl --pdf-evidence _temp/chuo-gold-v1/discovery_evidence.jsonl --pdf-evidence _temp/kimikan-manual-v2/discovery_evidence.jsonl --json --output _temp/v359-non-windows-release-gates-evidence.json`
  -> `ok=true`, Tokyo evidence `4` exact / `0` failures, Saitama evidence `16` exact / `0` failures, 聖十字 evidence `1` exact / `0` failures, 更生 evidence `1` exact / `0` failures, 中央情報 evidence `1` exact / `0` failures, and 君津 evidence `1` exact / `0` failures.

Previously retained v358/v357/v342 source/package evidence:

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

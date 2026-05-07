# Active Goal Completion Audit — EIDP Rolling Automation

Date: 2026-05-07
Branch: `sprint8-handoff-finalize`
Latest audited Windows package commit: `b3821f4e77c7207860ca6b6f2a67acb84b1c9c44` (`eidp-windows-v80.zip`)

## Objective Restatement

Build EIDP into a durable annual automation system for collecting each
university/vocational school's official 修学支援新制度 confirmation PDF,
verifying the configured target fiscal year, extracting department/student
figures into the DB, and producing the Excel outputs through a Windows
operator UI with minimal manual work.

This is not a one-year R8 project. The same system must roll from FY2026
to FY2027 and later by changing or deriving `target_fiscal_year`.

## Prompt-To-Artifact Checklist

| Requirement | Current evidence | Status |
| --- | --- | --- |
| Rolling target fiscal year, not hard-coded R8 | `src/eidp/config.py` uses `settings.target_fiscal_year`; `src/eidp/fiscal_year.py` derives Japanese fiscal year by April boundary and formats `2026年度（令和8年度）`. Production runners are `run_weekly_target_year_discovery.py` and `target_year_acquisition_plan.py`; R8-named scripts left in `scripts/` are compatibility wrappers. `settings_page.py` now lets the operator change target FY / era alias / OCR / API settings and rebuilds all active `school_fiscal_year_status` rows when target FY changes. | Mostly covered locally: runtime and active entrypoints are rolling; settings changes no longer leave stale task rows. Remaining R8 strings are compatibility wrappers, historical reports/plans, or FY2026 test fixtures. |
| Start from official government/prefecture indexes where possible | `data/prefecture-aggregators/seed.csv`; `src/eidp/scraper/prefecture_aggregator.py`; `scripts/verify_windows_distribution.py` now reads the ZIP seed/parser source and gates 47 prefecture rows, 47 parser registrations, and 47 downloadable official artifact URLs. Latest v80 verifier details: `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`, `prefecture_seed_with_school_link_signal=37`, `prefecture_seed_supplemental_rows=1`, `prefecture_seed_school_rows_total=2148`. Windows bounded bootstrap smoke on v73 downloaded/parsed all 47 official indexes and produced `official_index_rows_extracted=1948`, `official_index_rows_matched=1770`, `official_school_sites_added=1306`, plus 48 seed URLs and 295 corporation-pattern URLs before the 25-site PDF crawl. | Release-gated for nationwide official-index bootstrap presence, and official-index URL yield is proven on Windows through Step 2b from v73. Latest v80 still needs Windows revalidation. Full target-year PDF crawling/ingestion still has to prove PDF yield. |
| Show source chain / why a PDF was found | `src/eidp/review/_pages/pdf_manual_entry.py` shows selected PDF, source page, confidence, and discovery evidence log; `school_year_tasks.py` now labels crawl entry source quality. | Mostly covered locally; Windows click-through not revalidated after latest UI. |
| Minimize manual URL entry | `school_year_tasks.py` has UI buttons for initial URL/PDF bootstrap and weekly rediscovery; `URL追加` supports reusable page URLs and CSV bulk import. Web search now rejects known third-party directory/government-index URLs before registering `school_site`. Initial-bootstrap completion now preserves official-index yield details (`official_index_rows_extracted`, `official_index_rows_matched`, URL added/upgraded counts, and no-new-URL prefectures) for the operator UI. | Partial: manual entry is reduced and the reason for low yield is more visible, but prefectures without school-publication links and schools whose official page is not discoverable still need fallback discovery/operator review. |
| Avoid counting stale old-year PDFs as success | `pdf_discovery.py` strict target-FY mode; `target_year_status.py`; `excel_preview.py` warns when target FY data is missing; `school_fiscal_year_status.py` tracks stale fallback separately. `pdf_discovery.py` also pre-filters clear non-target public documents, decoded wrapper-URL filenames, and explicit stale fiscal-year link hints such as `令和7年度`, `r07`, and `2025年度` before download, while preserving post-download target-year checks for ambiguous confirmation forms. | Mostly covered for current pipeline; bounded Windows Step 3 smoke proved `prefiltered=87` and `cached_rejections=46` on 25 real sites. v72->v73 evidence comparison showed wrapper URL filtering reduced `http_error` from 10 to 5 and raised `pre_filtered_non_target_hint` from 41 to 55. Full PDF crawl/ingest still needs validation. |
| Make PDF確認 usable | `school_year_tasks.py` now works as the main operator task board: progress bar, work-lane buttons for URL gaps / target-year PDF wait / stale PDFs / PDF確認・手入力 / dept changes / Excel preview, and preserved filters. `PDF確認・手入力` now adds queue-level next-action summaries, year buckets, editable/read-only counts, focused-doc auto expansion, evidence panel, PDF preview/download, lock handling, and manual entry save path. | Improved locally with UI wiring tests; user still needs final real-workload UI feedback. |
| Review school-universe changes from official remarks | `src/eidp/review/_pages/prefecture_remarks.py` now has dedicated page for official index coverage and `prefecture_remark` review items. The distribution verifier now proves the packaged official-index seed is nationwide rather than partial. | Covered locally with tests and package gate; real operator review of remark workload remains pending. |
| Excel output should use current target FY | `excel_preview.py` blocks preview generation when target-FY data is zero and shows gap metrics; `competition_exporter.py` defaults business export to `settings.target_fiscal_year`, rejects empty target-year business export, and no longer carries the old auto-select-most-populated-year helper. | Core code covered locally; remaining risk is Windows UI click-through and real template/operator validation. |
| Windows operator delivery | `dist/eidp-windows.zip` rebuilt as v80 at commit `b3821f4`, verifier `ok=true`, `git_dirty=false`, SHA256 `4d7b291b2b67fbcfd1e82643f995a6e2dcbe47e1206320d4ca888e1b3b24c253`, wheelhouse 82 wheels. Latest package includes the current operator runbook, settings page, and UI-first weekly rediscovery guidance. Latest Mac smoke confirms Streamlit starts, settings page imports, and Settings navigation has zero exceptions against an isolated SQLite DB. Remote Windows smoke is still only proven through v73: SHA256 match, clean setup exit code 0, `school_count=2418`, `school_fiscal_year_status_count=2418`, official-index yield, and bounded Step 3 cache/prefilter behavior. | Latest package is locally verified and ready for Windows transfer. Full Windows PDF crawl/ingest and UI click-through are still not complete on v80. |
| Universities ~700 and vocational schools ~1700 | UI filters support `専門学校` / `大学`; official index parsers can parse mixed lists. | Not complete: full university rollout is explicitly v1.2; only pilot scope is planned. |

## Latest Verification Evidence

- `uv run pytest -q` → `820 passed, 5 warnings`
- `uv run pytest tests/unit/test_settings_page.py -q` → `7 passed`
- `uv run pytest tests/unit/test_review_app.py tests/unit/test_review_school_year_tasks.py tests/unit/test_windows_packaging_spike.py tests/unit/test_windows_distribution_verifier.py -q` → `131 passed`
- `uv run pytest tests/unit/test_windows_packaging_spike.py tests/unit/test_windows_distribution_verifier.py tests/unit/test_windows_install_validator.py -q` → `106 passed`
- `uv run pytest tests/unit/test_windows_distribution_verifier.py -q` → `35 passed`
- `uv run ruff check src/eidp/review/_pages/settings_page.py tests/unit/test_settings_page.py src/eidp/review/operator_pages.py scripts/bootstrap_pdf_pipeline.py tests/unit/test_bootstrap_pdf_pipeline.py` → passed
- `uv run ruff check scripts/verify_windows_distribution.py tests/unit/test_windows_distribution_verifier.py` → passed
- `uv run mypy src/eidp/review/_pages/settings_page.py` → passed
- `uv run mypy scripts/verify_windows_distribution.py` → passed
- Streamlit AppTest with isolated SQLite smoke DB → home page zero exceptions; Settings page navigation zero exceptions; `設定を保存` button present
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows.zip --json` on v80 → `ok=true`, `git_commit=b3821f4e77c7207860ca6b6f2a67acb84b1c9c44`, `git_dirty=false`, `sha256=4d7b291b2b67fbcfd1e82643f995a6e2dcbe47e1206320d4ca888e1b3b24c253`, `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`, no warnings
- `uv run ruff check src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py` → passed
- `uv run mypy src/eidp/scraper/pdf_discovery.py` → passed
- `uv run pytest tests/unit/test_pdf_discovery.py -q` → `24 passed, 5 warnings`
- `uv run ruff check scripts/bootstrap_pdf_pipeline.py src/eidp/review/_pages/school_year_tasks.py tests/unit/test_bootstrap_pdf_pipeline.py tests/unit/test_review_school_year_tasks.py` → passed
- `uv run mypy scripts/bootstrap_pdf_pipeline.py src/eidp/review/_pages/school_year_tasks.py` → passed
- `uv run pytest tests/unit/test_bootstrap_pdf_pipeline.py tests/unit/test_review_school_year_tasks.py -q` → `59 passed`
- `uv run pytest tests/unit/test_windows_distribution_verifier.py -q` → `34 passed`
- `uv run ruff check scripts/verify_windows_distribution.py tests/unit/test_windows_distribution_verifier.py` → passed
- `uv run mypy scripts/verify_windows_distribution.py` → passed
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows.zip --json` → `ok=true`, `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`, no warnings
- `uv run pytest tests/unit/test_review_prefecture_remarks.py tests/unit/test_review_school_year_tasks.py -q` → `34 passed`
- `uv run ruff check src/eidp/review/_pages/prefecture_remarks.py tests/unit/test_review_prefecture_remarks.py src/eidp/review/_pages/school_year_tasks.py tests/unit/test_review_school_year_tasks.py` → passed
- `uv run mypy src/eidp/review/_pages/prefecture_remarks.py src/eidp/review/_pages/school_year_tasks.py` → passed
- `uv run pytest tests/unit/test_competition_exporter.py -q` → `11 passed`
- `uv run mypy src/eidp/excel/competition_exporter.py` → passed
- `uv run pytest tests/unit/test_review_school_year_tasks.py tests/unit/test_operator_pages.py -q` → `54 passed`
- `uv run mypy src/eidp/review/_pages/school_year_tasks.py` → passed
- `uv run pytest tests/unit/test_review_pdf_manual_entry.py tests/unit/test_review_pdf_manual_entry_confidence.py -q` → `44 passed, 5 warnings`
- `uv run mypy src/eidp/review/_pages/pdf_manual_entry.py` → passed
- Windows remote ZIP smoke on v73 → SHA256 `fee2aa1b810acbdeb080fc0452174339b4559f3a6347f23cea04c6e79df5a448`, `settings_page.py` present, decoded wrapper-URL hint filtering present, strong fiscal-year hint filter present, `entry_count=2992`, `BuildCommit=02ab507a347f9540e10d0d206c52f3d7b52751a0`
- Windows remote setup smoke on v73 clean extraction → `setup_exit=0`, validator reported `OK install`, `school_count: 2418`, `school_fiscal_year_status_count: 2418`, `wheel_count: 82`
- Windows remote bounded Step 3 smoke on v73 clean install → `status=succeeded`, 47 official indexes parsed, `official_index_rows_extracted=1948`, `official_index_rows_matched=1770`, `official_school_sites_added=1306`, 25 school sites crawled, `downloaded=0`, `failed=1`, `skipped=160`, `cached_rejections=46`, `prefiltered=87`
- Windows v72-to-v73 rejection evidence comparison on the same 25-site smoke scope → total rejection rows stayed `183`, `http_error` fell `10 -> 5`, `pre_filtered_non_target_hint` rose `41 -> 55`, and `target_fiscal_year_not_detected` fell `78 -> 70`
- Windows remote ZIP smoke on v72 → SHA256 `63dfac3aef2759387986c92619f9b810ac06c5c91ee96dd0ff7994e7770b1b8a`, `settings_page.py` present, `pre_filtered_non_target_hint` code present, strong fiscal-year hint filter present, `launch.bat` has no stale `"RC=-1"` token, `entry_count=2992`, `BuildCommit=edd0a4514297ded842bd6bc68df50acb8ee973b9`
- Windows remote setup smoke on v72 clean extraction → `setup_exit=0`, validator reported `OK install`, `school_count: 2418`, `school_fiscal_year_status_count: 2418`, `wheel_count: 82`
- Windows remote bounded Step 3 smoke on v72 clean install → `status=succeeded`, 47 official indexes parsed, `official_index_rows_extracted=1948`, `official_index_rows_matched=1770`, `official_school_sites_added=1306`, 25 school sites crawled, `downloaded=0`, `failed=1`, `skipped=155`, `cached_rejections=46`, `prefiltered=74`
- Windows remote ZIP smoke on v71 → SHA256 `b9f154ea80c96252947b8bcd9955122ee304c3726c5ae3b74e32c26c85f5a5d9`, `settings_page.py` present, `pre_filtered_non_target_hint` code present, `launch.bat` has no stale `"RC=-1"` token, `entry_count=2992`, `BuildCommit=69fcdb87c0fdee1643cdf22eece773a302f231a8`
- Windows remote setup smoke on v71 clean extraction → `setup_exit=0`, validator reported `OK install`, `school_count: 2418`, `school_fiscal_year_status_count: 2418`, `wheel_count: 82`
- Windows remote bounded Step 3 smoke on v71 clean install → `status=succeeded`, 47 official indexes parsed, `official_index_rows_extracted=1948`, `official_index_rows_matched=1770`, `official_school_sites_added=1306`, 25 school sites crawled, `downloaded=0`, `failed=1`, `skipped=133`, `cached_rejections=46`, `prefiltered=41`
- Windows remote ZIP smoke on v70 → SHA256 `0b1a219e9c86148b5942da85944a49345c43ce0df59a0df16caf58681b6ac6a7`, `settings_page.py` present, `launch.bat` present, `cached_rejections` code present, `MAX_DISCOVERY_EXTRA_PAGES` fanout bound present, `BuildCommit=c671ea3de404815251924977f24791665d4a236d`
- Windows remote setup smoke on v70 clean extraction → `setup_exit=0`, validator reported `OK install`, `school_count: 2418`, `school_fiscal_year_status_count: 2418`, `wheel_count: 82`
- Windows remote setup smoke on v69 clean extraction → `setup_exit=0`, validator reported `OK install`, `school_count: 2418`, `school_fiscal_year_status_count: 2418`, `wheel_count: 82`
- Windows remote bounded Step 3 cache smoke on v69 clean install → stopped after cache behavior proof, progress reached `crawled=9`, `skipped=40`, `cached_rejections=16`; this confirms repeated old/non-target corporation PDFs are no longer downloaded/classified once per school.
- Windows remote setup smoke on v67 code path → `SETUP_EXIT=0`, `IMPORT_OK`, SQLite DB present, `SCHOOL_COUNT=2418`, `TASK_COUNT=2418`
- Windows remote official-index yield smoke on v67 smoke install → `BOOTSTRAP_SKIP_DISCOVER_EXIT=0`, 47 official indexes parsed, `official_index_rows_extracted=1948`, `official_index_rows_matched=1770`, `official_school_sites_added=1306`, `SCHOOL_SITE_TOTAL=1649`, `SCHOOL_SITE_BY_METHOD=[('corporation_pattern', 295), ('prefecture_aggregator', 1306), ('seed_csv', 48)]`

## Missing Before Goal Can Be Marked Complete

1. Validate target-year PDF yield with a full real bootstrap run.
   Official-index URL yield is now proven through Step 2b. The next proof needs
   a complete Windows initial acquisition run through PDF crawl and ingest,
   showing actual target-year PDF yield, stale rejection counts, and fallback
   search counts.
2. Run latest v80 ZIP on Windows and verify:
   setup, UI start, initial bootstrap button, weekly rediscovery button,
   official-index coverage page, school task drill-down, PDF確認, and Excel
   preview.
3. Keep R-0 naming debt controlled: compatibility wrappers and historical
   reports may keep R8 wording, but new production entrypoints must use
   target-year naming.
4. Decide university scope: keep as gated pilot for v1.1, or start the v1.2
   parser/discovery track.
5. Validate the UI with real operator feedback; current tests prove wiring and
   business rules, not usability under real workload.

## Current Conclusion

The project is materially closer to the intended automation architecture:
official government indexes are now the primary acquisition surface, stale PDFs
are demoted, target-FY tasking is visible, and Windows packaging is refreshed.

The active goal is **not complete**. The main remaining blockers are nationwide
coverage, latest Windows E2E validation, real operator UI validation, and the
explicit university rollout decision.

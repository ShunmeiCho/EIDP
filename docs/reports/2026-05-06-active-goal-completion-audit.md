# Active Goal Completion Audit — EIDP Rolling Automation

Date: 2026-05-07
Latest update: 2026-05-11
Branch: `sprint8-handoff-finalize`
Latest audited Windows package commit: `c9bb155ff6e98979275296980b8f942e6a0b4e87` (`eidp-windows-v137.zip`)

## 2026-05-11 v137 Update

v137 refreshes the Windows handoff package after adding discovery gold-set
packaging and verifier contract checks. The ZIP now carries the deterministic
`data/discovery-gold-set/` regression surface and the verifier parses the
packaged JSON entries instead of checking filenames only.

- Core ZIP: `dist/eidp-windows-v137.zip`
- Latest alias: `dist/eidp-windows.zip`
- Core ZIP SHA256: `17f76efe01c56ce5042fcc81928e533059feafa0b15508723b42dbbdeda5aefe`
- Core verifier: `OK core`, `git_commit=c9bb155ff6e98979275296980b8f942e6a0b4e87`,
  `git_dirty=false`, `entry_count=3016`, `wheel_count=78`,
  `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`,
  `prefecture_seed_downloadable=47`,
  `discovery_gold_set_entries=12`, and discovery gold-set outcomes
  `accepted_target_pdf=4`, `needs_operator_review=5`,
  `no_target_candidate_found=1`, `publication_lag_latest_public=2`.
- Playwright/Scrapling add-on: `dist/eidp-playwright-addon-windows-v106.zip`
- Add-on SHA256: `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`
- Combined verifier: `OK core` and `OK playwright-addon`; the add-on verifier
  reported `entry_count=637` and `manifest_files=636`.
- Windows remote extraction smoke on host alias `win`: copied
  `eidp-windows-v137.zip`, verified the same SHA256, expanded into the fresh
  directory `C:\EIDP-v137-c9bb155`, and ran
  `scripts\validate_windows_install.py` from the bundled runtime. Result:
  `OK install`, `build_commit=c9bb155ff6e98979275296980b8f942e6a0b4e87`,
  `build_dirty=false`, `master_xlsx_present=True`, and `wheel_count=78`.
- Windows remote first setup smoke in `C:\EIDP-v137-c9bb155`: `scripts\first_setup.bat`
  completed with offline wheelhouse install, SQLite bootstrap, master Excel
  import, and task rebuild. Validator reported `errors=[]`, `warnings=[]`,
  `school_count=2418`, `school_fiscal_year_status_count=2418`,
  `sqlite_table_count=15`, and required tables including `school_site`,
  `document`, `department_yearly`, and `manual_action_log`.
- Windows remote add-on smoke: extracted the Playwright/Scrapling add-on into
  the same fresh directory, re-ran `first_setup.bat`, and confirmed offline
  installation of `scrapling==0.4.7` and `playwright==1.58.0`.
- Windows remote browser smoke: with `EIDP_APP_ROOT=C:\EIDP-v137-c9bb155`,
  `scrapling_available=True`, `PLAYWRIGHT_BROWSERS_PATH` pointed to
  `playwright-addon\ms-playwright`, and bundled Chromium launched headless
  against a `data:` page with `playwright_title=eidp-ok`.

Interpretation: v137 moves the handoff package from "core ZIP verified" to
"core ZIP, discovery gold-set contract, extracted Windows setup, and optional
Scrapling/Playwright browser add-on verified". This improves release-handoff
confidence but does not close the product yield gate. The active goal still
requires a broader Windows acquisition run that proves true target-FY PDF
automation reaches the 60-70% line, or an explicit publication-lag policy that
keeps latest-public stale forms separate from target-FY success.

## 2026-05-10 v136 Update

v136 is now the current Windows handoff candidate on `sprint8-handoff-finalize`.
The branch has been pushed to `origin/sprint8-handoff-finalize`; `main` remains
unchanged pending real Windows yield acceptance.

- Core ZIP: `dist/eidp-windows-v136.zip`
- Core ZIP SHA256: `6a712770fabdd00bd724deafb6de63f7806198df50d632630eb6608a4d83096a`
- Playwright/Scrapling add-on: `dist/eidp-playwright-addon-windows-v106.zip`
- Add-on SHA256: `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`
- Windows setup/validator: passed on a clean v136 extraction; validator reported
  `errors=[]`, `warnings=[]`, `school_count=2418`, and
  `school_fiscal_year_status_count=2418`.
- Saitama 5-school URL crawl: `attempted=5`, `auto_registered=5`, `errors=0`,
  with 5 `school` URLs and 10 auxiliary `disclosure` URLs registered.
- Strict FY2026 PDF discovery on the same 5 schools: `downloaded=0`. Evidence
  rows were all rejected as non-target or stale, led by `classified_non_target=102`
  and `fiscal_year_mismatch:2025=10`.
- FY2025 control run on the same 5 schools: 4 target confirmation PDFs were
  accepted into `document`, proving the URL/PDF chain can download and classify
  the public latest target forms when the sites publish FY2025 material.
- Tokyo 10-school URL crawl control: 9 auto-registered, 1 queued for review,
  0 errors. The auto set includes both non-Sanko schools (日本工学院, 東京モード学園,
  HAL東京, 首都医校) and Sanko schools.
- Strict FY2026 PDF discovery on the Tokyo auto set: `downloaded=0` across
  9 schools / 15 registered URLs. Evidence contained 105 rejection rows:
  `classified_non_target=48`, `pre_filtered_non_target_hint=29`, and 20 stale
  target-form mismatches across FY2025-FY2020.
- FY2025 control run on the same Tokyo auto set: 3 target confirmation PDFs were
  accepted into `document`, all Sanko 2025 `yoshiki2025.pdf` forms.
- Cross-prefecture 25-school URL crawl control (神奈川/大阪/愛知/福岡/北海道):
  23 auto-registered, 2 queued for review, 0 errors. Strict FY2026 discovery on
  those 23 schools / 40 registered URLs downloaded 0 target PDFs; FY2025 control
  downloaded 15 target PDFs. This is the strongest current evidence that the
  URL-discovery layer works for common Sanko patterns, while the public latest
  confirmation forms in this sample are still FY2025, not FY2026.

Interpretation: v136 closes the packaging, URL crawl, Scrapling static-html, URL
review, and review-metric issues found in the v134 audit. The remaining release
gate is not packaging readiness; it is target-year policy/yield. The sampled
Sanko pages currently expose 2025 confirmation forms, while strict FY2026 mode
correctly refuses to count those stale forms as success. Non-Sanko Tokyo
schools in the small sample did not expose target confirmation candidates on the
pages discovered by the crawler.

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
| Start from official government/prefecture indexes where possible | `data/prefecture-aggregators/seed.csv`; `src/eidp/scraper/prefecture_aggregator.py`; `scripts/verify_windows_distribution.py` now reads the ZIP seed/parser source and gates 47 prefecture rows, 47 parser registrations, and 47 downloadable official artifact URLs. Latest v102 verifier details: `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`, `prefecture_seed_with_school_link_signal=37`, `prefecture_seed_supplemental_rows=1`, `prefecture_seed_school_rows_total=2148`. Windows bounded bootstrap smoke on v73 downloaded/parsed all 47 official indexes and produced `official_index_rows_extracted=1948`, `official_index_rows_matched=1770`, `official_school_sites_added=1306`, plus 48 seed URLs and 295 corporation-pattern URLs before the 25-site PDF crawl. Latest Mac Saitama smoke parsed the official Saitama index into 58 extracted rows, 51 matched school rows, and 51 official school-site URLs before crawling 80 sites. | Release-gated for nationwide official-index bootstrap presence, and official-index URL yield is proven on Windows through Step 2b from v73. Latest v102 still needs Windows revalidation. Full target-year PDF crawling/ingestion still has to prove PDF yield. |
| Show source chain / why a PDF was found | `src/eidp/review/_pages/pdf_manual_entry.py` shows selected PDF, source page, confidence, and discovery evidence log; `school_year_tasks.py` now labels crawl entry source quality. | Mostly covered locally; Windows click-through not revalidated after latest UI. |
| Minimize manual URL entry | `school_year_tasks.py` has UI buttons for initial URL/PDF bootstrap and weekly rediscovery; `URL追加` supports reusable page URLs and CSV bulk import. Web search now rejects known third-party directory/government-index URLs before registering `school_site`. Initial-bootstrap completion now preserves official-index yield details (`official_index_rows_extracted`, `official_index_rows_matched`, URL added/upgraded counts, and no-new-URL prefectures) for the operator UI. | Partial: manual entry is reduced and the reason for low yield is more visible, but prefectures without school-publication links and schools whose official page is not discoverable still need fallback discovery/operator review. |
| Avoid counting stale old-year PDFs as success | `pdf_discovery.py` strict target-FY mode; `target_year_status.py`; `excel_preview.py` warns when target FY data is missing; `school_fiscal_year_status.py` tracks stale fallback separately. `pdf_discovery.py` also pre-filters clear non-target public documents, decoded wrapper-URL filenames, and explicit stale fiscal-year link hints such as `令和7年度`, `r07`, and `2025年度` before download, while preserving post-download target-year checks for ambiguous confirmation forms. v94 additionally accepts a PDF whose body classifies as the target confirmation form when the target-year evidence appears in the official URL or anchor text instead of the PDF body; URL-year evidence alone still cannot save non-target PDFs such as student A forms or syllabi. v95 tightens the remaining image-only edge: target-year text alone no longer admits ambiguous image-only admission guides unless the URL/anchor strongly names the target confirmation form. | Mostly covered for current pipeline; bounded Windows Step 3 smoke proved `prefiltered=87` and `cached_rejections=46` on 25 real sites. Mac Saitama 80-site diagnostic smoke exposed one false positive admission guide (`2026syakai-isikai.pdf`), then strict school-id 780 retest after the v95 fix produced `downloaded=0` and `target_application_not_detected`. Full Windows PDF crawl/ingest still needs validation. |
| Make PDF確認 usable | `school_year_tasks.py` now works as the main operator task board: progress bar, work-lane buttons for URL gaps / target-year PDF wait / stale PDFs / PDF確認・手入力 / dept changes / Excel preview, preserved filters, and a CSV export for the visible source chain (`取得入口`, registration method, reusable URL, PDF URL/year, and status labels). `PDF確認・手入力` now adds queue-level next-action summaries, year buckets, editable/read-only counts, action-lane filtering (`作業レーン`), focused-doc auto expansion, evidence panel, explicit fiscal-year evidence summaries that distinguish PDF body evidence from URL/link hints, candidate-table `年度根拠` / `PDF本文年度` columns sourced from crawler JSONL, PDF preview/download, lock handling, and manual entry save path. Latest AppTest smoke renders a focused PDF review row through `render()`, OCR availability, discovery JSONL, and the PDF route info panel without exceptions. | Improved locally with UI wiring tests; user still needs final real-workload UI feedback. |
| Review school-universe changes from official remarks | `src/eidp/review/_pages/prefecture_remarks.py` now has dedicated page for official index coverage and `prefecture_remark` review items. The distribution verifier now proves the packaged official-index seed is nationwide rather than partial. | Covered locally with tests and package gate; real operator review of remark workload remains pending. |
| Excel output should use current target FY | `excel_preview.py` blocks preview generation when target-FY data is zero and shows gap metrics; `competition_exporter.py` defaults business export to `settings.target_fiscal_year`, rejects empty target-year business export, and no longer carries the old auto-select-most-populated-year helper. | Core code covered locally; remaining risk is Windows UI click-through and real template/operator validation. |
| Windows operator delivery | `dist/eidp-windows-v137.zip` rebuilt at commit `c9bb155ff6e98979275296980b8f942e6a0b4e87`, verifier `ok=true`, `git_dirty=false`, SHA256 `17f76efe01c56ce5042fcc81928e533059feafa0b15508723b42dbbdeda5aefe`, wheelhouse 78 wheels, 47 prefecture seed rows/parser registrations/downloadable artifact URLs, and packaged discovery gold-set outcomes across accepted target PDFs, operator review, no-target, and publication-lag cases. The latest alias `dist/eidp-windows.zip` has the same SHA256. `dist/eidp-playwright-addon-windows-v106.zip` verifies with SHA256 `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`, `entry_count=637`, and `manifest_files=636`. Remote Windows smoke on a clean `C:\EIDP-v137-c9bb155` extraction proved SHA256 match, setup exit success, `school_count=2418`, `school_fiscal_year_status_count=2418`, required SQLite tables, optional Scrapling/Playwright wheel install, and bundled Chromium headless launch through `PLAYWRIGHT_BROWSERS_PATH`. | Latest package and optional browser add-on are locally verified and Windows-extracted/setup verified. Full Windows PDF crawl/ingest yield and UI click-through are still not complete on v137. |
| Universities ~700 and vocational schools ~1700 | UI filters support `専門学校` / `大学`; official index parsers can parse mixed lists. | Not complete: full university rollout is explicitly v1.2; only pilot scope is planned. |

## Latest Verification Evidence

- `git push origin sprint8-handoff-finalize` → remote branch updated through
  `5037944`; `main` intentionally unchanged.
- `uv run pytest -q` after the v136 URL-review fixes → `986 passed, 5 warnings`
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v136.zip --playwright-addon dist/eidp-playwright-addon-windows-v106.zip` → `OK core`, `git_commit=b63664c613fd51fdc783912d9e1c82d83afde377`, `git_dirty=false`, `entry_count=3000`, `wheel_count=78`, 47 prefecture seed rows/parser registrations/downloadable artifact URLs, add-on SHA256 `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`
- Windows v136 clean extraction/setup/validator → `errors=[]`, `warnings=[]`,
  `school_count=2418`, `school_fiscal_year_status_count=2418`, required tables
  present, duplicate wheel distributions `{}`.
- Windows v136 Saitama 5-school URL crawl → `attempted=5`,
  `auto_registered=5`, `errors=0`, `unavailable=0`; database check found 5
  `school` URLs plus 10 `disclosure` URLs for the 5 sampled schools.
- Windows v136 strict FY2026 PDF discovery for the same 5-school sample →
  `downloaded=0`; rejection evidence was dominated by `classified_non_target=102`
  and stale-year buckets such as `fiscal_year_mismatch:2025=10`.
- Windows v136 FY2025 control run for the same 5-school sample → 4 target
  confirmation PDFs accepted into `document`, proving the acquisition chain works
  for the public latest year while strict FY2026 refuses stale success.
- Windows v136 Tokyo 10-school URL crawl →
  `attempted=10`, `auto_registered=9`, `review_enqueued=1`, `errors=0`.
  Auto results included 4 non-Sanko schools and 5 Sanko schools.
- Windows v136 strict FY2026 PDF discovery for the Tokyo auto set →
  `crawled=15`, `found=11`, `downloaded=0`, `failed=1`, `skipped=100`;
  evidence rows: `classified_non_target=48`, `pre_filtered_non_target_hint=29`,
  stale `fiscal_year_mismatch:*` rows = 20, and `no_candidates_found=4`.
- Windows v136 FY2025 control run for the Tokyo auto set →
  `downloaded=3`; DB rows were inserted for school IDs 17, 18, and 19 using
  Sanko `yoshiki2025.pdf` target confirmation forms.
- Windows v136 cross-prefecture 25-school URL crawl →
  `attempted=25`, `auto_registered=23`, `review_enqueued=2`, `errors=0`.
- Windows v136 strict FY2026 PDF discovery for those 23 auto schools →
  `crawled=40`, `found=34`, `downloaded=0`, `failed=2`, `skipped=332`;
  evidence rows: `classified_non_target=230`, `pre_filtered_non_target_hint=40`,
  stale `fiscal_year_mismatch:*` rows = 61, `target_fiscal_year_not_detected=9`,
  and `no_candidates_found=6`.
- Windows v136 FY2025 control run for the same cross-prefecture auto set →
  `downloaded=15`, all accepted target PDFs were Sanko latest-public FY2025
  forms.
- `uv run pytest -q` → `841 passed, 5 warnings`
- `uv run pytest tests/unit/test_pdf_discovery.py tests/unit/test_review_pdf_manual_entry.py -q` → `70 passed, 5 warnings`, including a Streamlit AppTest focused PDF確認 render smoke with discovery JSONL evidence
- `uv run ruff check tests/unit/test_review_pdf_manual_entry.py src/eidp/review/_pages/pdf_manual_entry.py src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py` → passed
- `uv run mypy src/eidp/review/_pages/pdf_manual_entry.py src/eidp/scraper/pdf_discovery.py` → passed
- `uv run ruff check src/eidp/scraper/pdf_discovery.py src/eidp/review/_pages/pdf_manual_entry.py tests/unit/test_pdf_discovery.py tests/unit/test_review_pdf_manual_entry.py` → passed
- `uv run mypy src/eidp/scraper/pdf_discovery.py src/eidp/review/_pages/pdf_manual_entry.py` → passed
- `uv run pytest tests/unit/test_review_pdf_manual_entry.py -q` → `40 passed, 5 warnings`
- `uv run ruff check src/eidp/review/_pages/pdf_manual_entry.py tests/unit/test_review_pdf_manual_entry.py` → passed
- `uv run mypy src/eidp/review/_pages/pdf_manual_entry.py` → passed
- `uv run pytest tests/unit/test_review_school_year_tasks.py -q` → `48 passed`
- `uv run ruff check src/eidp/review/_pages/school_year_tasks.py tests/unit/test_review_school_year_tasks.py` → passed
- `uv run mypy src/eidp/review/_pages/school_year_tasks.py` → passed
- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v102.zip --latest-alias` → wrote versioned ZIP, automatic checksum sidecar, and refreshed `dist/eidp-windows.zip`
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v102.zip` → `OK core`, `git_commit=3dc8aa98ba7e19b4813449858eb56ad25e4ea3c6`, `git_dirty=false`, `sha256=7ac5512fa81838289eb5e6e773f4ad30bedb1e166eb8f8f230f36ee15db294a5`, `entry_count=2994`, `wheel_count=82`, `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows.zip` → `OK core`, `git_commit=3dc8aa98ba7e19b4813449858eb56ad25e4ea3c6`, `git_dirty=false`, `sha256=7ac5512fa81838289eb5e6e773f4ad30bedb1e166eb8f8f230f36ee15db294a5`, `entry_count=2994`, `wheel_count=82`, `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`
- Extracted v102 ZIP smoke (`_temp/v102-extract-H4hMSp`) using the packaged `scripts/validate_windows_install.py` → `OK install`, `build_commit=3dc8aa98ba7e19b4813449858eb56ad25e4ea3c6`, `build_branch=sprint8-handoff-finalize`, `build_dirty=false`, `master_xlsx_present=True`, `wheel_count=82`
- `uv run pytest tests/unit/test_pdf_discovery.py -q` → `30 passed, 5 warnings`
- `uv run ruff check src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py src/eidp/review/operator_pages.py` → passed
- `uv run mypy src/eidp/scraper/pdf_discovery.py` → passed
- v95 strict real-site retest for Saitama `school_id=780` after image-only guard → `crawled=1`, `found=1`, `downloaded=0`, `skipped=9`; `2026syakai-isikai.pdf` rejected as `target_application_not_detected`
- Saitama 80-site diagnostic smoke before the v95 image-only guard (`_temp/bootstrap-mac-v94-saitama-OM2lEc`), scope `--pref saitama --url-search off --batch-size 80` → official index `extracted=58`, `matched=51`, `official_school_sites_added=51`, crawl `crawled=80`, `found=71`, `downloaded=1`, `failed=7`, `skipped=607`, `prefiltered=251`, `cached_rejections=114`, ingest `processed=1`, `yearly_upserted=0`; manual inspection showed the single download was `2026年度 社会人・医療機関推薦選抜募集要項`, not the target confirmation form.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v95.zip` → `OK core`, `git_commit=2822c3cde62214b578b1c4d3093586be1667dfcc`, `git_dirty=false`, `sha256=2ad26209bf3ffccbf22855ca74d29e5bb60e18de3dbd0cc520118ffb1c653263`, `entry_count=2994`, `wheel_count=82`, `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows.zip` → `OK core`, `git_commit=2822c3cde62214b578b1c4d3093586be1667dfcc`, `git_dirty=false`, `sha256=2ad26209bf3ffccbf22855ca74d29e5bb60e18de3dbd0cc520118ffb1c653263`, `entry_count=2994`, `wheel_count=82`, `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`
- Extracted v95 ZIP smoke (`_temp/v95-extract-hQKm0m`) using the packaged `scripts/validate_windows_install.py` → `OK install`, `build_commit=2822c3cde62214b578b1c4d3093586be1667dfcc`, `build_branch=sprint8-handoff-finalize`, `build_dirty=false`, `master_xlsx_present=True`, `wheel_count=82`
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v94.zip` → `OK core`, `git_commit=cb53ac502b81e1a23f262f25fa7126dc096e7366`, `git_dirty=false`, `sha256=66b42d015076a39b45f720d0484c89ef88aafb4bf7dd064029d67a378ddd031f`, `entry_count=2994`, `wheel_count=82`, `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows.zip` → `OK core`, `git_commit=cb53ac502b81e1a23f262f25fa7126dc096e7366`, `git_dirty=false`, `sha256=66b42d015076a39b45f720d0484c89ef88aafb4bf7dd064029d67a378ddd031f`, `entry_count=2994`, `wheel_count=82`, `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`
- Extracted v94 ZIP smoke (`_temp/v94-extract-ZzPjsf`) using the packaged `scripts/validate_windows_install.py` → `OK install`, `build_commit=cb53ac502b81e1a23f262f25fa7126dc096e7366`, `build_branch=sprint8-handoff-finalize`, `build_dirty=false`, `master_xlsx_present=True`, `wheel_count=82`
- `uv run pytest tests/unit/test_bootstrap_pdf_pipeline.py tests/unit/test_review_school_year_tasks.py -q` → `69 passed`
- `uv run pytest tests/unit/test_windows_install_validator.py tests/unit/test_windows_distribution_verifier.py -q` → `56 passed`
- `uv run pytest tests/unit/test_review_school_year_tasks.py tests/unit/test_settings_page.py -q` → `52 passed`
- `uv run pytest tests/unit/test_review_school_year_tasks.py -q` → `47 passed`, including Streamlit AppTests proving the task-board package identity caption renders and the task-board settings shortcut opens the settings page
- `uv run ruff check src/eidp/review/_pages/school_year_tasks.py tests/unit/test_review_school_year_tasks.py` → passed
- `uv run mypy src/eidp/review/_pages/school_year_tasks.py` → passed
- `uv run pytest tests/unit/test_windows_install_validator.py tests/unit/test_windows_distribution_verifier.py -q` → `55 passed`
- `uv run ruff check scripts/validate_windows_install.py scripts/verify_windows_distribution.py tests/unit/test_windows_install_validator.py tests/unit/test_windows_distribution_verifier.py` → passed
- `uv run mypy scripts/validate_windows_install.py scripts/verify_windows_distribution.py` → passed
- `uv run pytest tests/unit/test_review_pdf_manual_entry.py tests/unit/test_review_pdf_manual_entry_confidence.py -q` → `47 passed, 5 warnings`
- `uv run mypy src/eidp/review/_pages/pdf_manual_entry.py` → passed
- `uv run pytest tests/unit/test_operator_pages.py tests/unit/test_review_school_year_tasks.py -q` → `62 passed`
- Chrome headless CDP smoke on isolated Streamlit app → HTTP `200`, home page rendered, `初回URL/PDF取得を開始` computed style changed from transparent to `rgb(0, 0, 0)` background / `rgb(255, 255, 255)` text, screenshot captured at `_temp/ui-smoke-20260507-120558/ui-smoke-home-rendered.png`
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v93.zip` → `OK core`, `git_commit=1029cc780d667cb0e02e66adf7abc51b5fefe235`, `git_dirty=false`, `sha256=357043f8288f8ed496c0fceac293e0c33848b889d870b42116e074a9b76584c0`, `entry_count=2994`, `wheel_count=82`, `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows.zip` → `OK core`, `git_commit=1029cc780d667cb0e02e66adf7abc51b5fefe235`, `git_dirty=false`, `sha256=357043f8288f8ed496c0fceac293e0c33848b889d870b42116e074a9b76584c0`, `entry_count=2994`, `wheel_count=82`, `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`
- Extracted v93 ZIP smoke (`_temp/v93-extract-cdA9iZ`) using the packaged `scripts/validate_windows_install.py` → `OK install`, `build_commit=1029cc780d667cb0e02e66adf7abc51b5fefe235`, `build_branch=sprint8-handoff-finalize`, `build_dirty=false`, `master_xlsx_present=True`, `wheel_count=82`
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
- Latest bounded online bootstrap smoke (`_temp/bootstrap-mac-v92-saitama-uElU7k`), scope `--pref saitama --url-search off --batch-size 30` → `status=succeeded`, official Saitama index `extracted=58`, `matched=51`, `official_school_sites_added=51`, seed URLs `50`, crawl `crawled=30`, `found=25`, `downloaded=0`, `failed=3`, `skipped=226`, `prefiltered=116`, `cached_rejections=24`, ingest `processed=0`, status rows `rebuilt=2418`. Evidence reason counts: `target_fiscal_year_not_detected=86`, `pre_filtered_non_target_hint=44`, `fiscal_year_mismatch:2025=41`, `fiscal_year_mismatch:2024=21`, `classified_non_target=12`, plus smaller old-year buckets. Manual text spot-check confirmed `applicationform-r8.pdf` is student A様式1 and `R8_1A1_0420.pdf` is a syllabus, so these R8-named rejects are correct non-target decisions.
- Previous bounded online bootstrap smoke for the unchanged acquisition pipeline (`_temp/bootstrap-smoke-v88-SAF911`), scope `--pref tokyo,kanagawa,saitama --skip-known-url-discovery --url-search off --batch-size 3 --skip-ingest` → `status=succeeded`, artifacts downloaded `3/3`, official index rows `extracted=377`, `matched=354`, `official_school_sites_added=353`, DB `school_sites=353`, crawl `crawled=3`, `found=3`, `downloaded=0`, `failed=0`, `skipped=21`, `prefiltered=15`, `cached_rejections=2`, documents `0`, prefecture remark review items `2`
- Previous bounded online smoke rejection evidence for the unchanged acquisition pipeline → `fiscal_year_mismatch:2025=3`, `fiscal_year_mismatch:2024=2`, `fiscal_year_mismatch:2023=2`, `fiscal_year_mismatch:2022=2`, `fiscal_year_mismatch:2021=2`, `fiscal_year_mismatch:2020=2`, `fiscal_year_mismatch:2019=1`, `target_fiscal_year_not_detected=3`, `pre_filtered_non_target_hint=1`; this proves old-year candidates are rejected, not counted as target-year success, on the sampled live sites.
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

1. Decide and validate the target-year acceptance policy.
   v137/v136 prove the URL crawl and PDF chain can acquire published FY2025 target
   confirmation PDFs on the sampled Saitama schools, while strict FY2026 mode
   correctly rejects those stale FY2025 forms. The goal cannot be marked
   complete until either FY2026/R8 forms are publicly available at sufficient
   yield, or the product explicitly accepts a publication-lag policy that records
   latest-public FY2025 forms separately from true target-FY success.
2. Validate full Windows bootstrap yield beyond the Sanko-heavy sample.
   The next proof needs a broader Windows initial acquisition run through PDF
   crawl and ingest, showing true target-FY PDF yield, stale rejection counts,
   fallback search counts, and review workload. Current v137 evidence is enough
   for packaging/URL-crawl readiness, not enough for the 60-70% automation gate.
3. Run the latest v137 UI flow on Windows and verify:
   UI start, initial bootstrap button, weekly rediscovery button, URL candidate
   review, official-index coverage page, school task drill-down, PDF確認, and
   Excel preview.
4. Keep R-0 naming debt controlled: compatibility wrappers and historical
   reports may keep R8 wording, but new production entrypoints must use
   target-year naming.
5. Decide university scope: keep as gated pilot for v1.1, or start the v1.2
   parser/discovery track.
6. Validate the UI with real operator feedback; current tests prove wiring and
   business rules, not usability under real workload.

## Current Conclusion

The project is materially closer to the intended automation architecture:
official government indexes are now the primary acquisition surface, stale PDFs
are demoted, target-FY tasking is visible, and Windows packaging is refreshed.

The active goal is **not complete**. v137 is the strongest Windows handoff
candidate so far, and the branch is backed up remotely, but strict FY2026 yield
is still unproven on real sites. The main remaining blockers are target-year
yield/policy, broader Windows E2E validation, real operator UI validation, and
the explicit university rollout decision.

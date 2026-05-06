# Active Goal Completion Audit — EIDP Rolling Automation

Date: 2026-05-07
Branch: `sprint8-handoff-finalize`
Latest audited Windows package commit: `0a0825bbea25421b25fba8ca421bd8c065dfd0c1` (`eidp-windows-v67.zip`)

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
| Rolling target fiscal year, not hard-coded R8 | `src/eidp/config.py` uses `settings.target_fiscal_year`; `src/eidp/fiscal_year.py` derives Japanese fiscal year by April boundary and formats `2026年度（令和8年度）`. Production runners are `run_weekly_target_year_discovery.py` and `target_year_acquisition_plan.py`; R8-named scripts left in `scripts/` are compatibility wrappers, and the old R8 simulation script is archived under `deploy/legacy-spike/`. | Mostly covered locally: runtime and active entrypoints are rolling; remaining R8 strings are compatibility wrappers, historical reports/plans, or FY2026 test fixtures. |
| Start from official government/prefecture indexes where possible | `data/prefecture-aggregators/seed.csv`; `src/eidp/scraper/prefecture_aggregator.py`; `scripts/verify_windows_distribution.py` now reads the ZIP seed/parser source and gates 47 prefecture rows, 47 parser registrations, and 47 downloadable official artifact URLs. Latest v67 verifier details: `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`, `prefecture_seed_with_school_link_signal=37`, `prefecture_seed_supplemental_rows=1`, `prefecture_seed_school_rows_total=2148`. | Release-gated for nationwide official-index bootstrap presence. Product yield is now surfaced in the initial-bootstrap progress JSON/UI, but a full real bootstrap run still has to prove how much target-year PDF yield comes from each official index. |
| Show source chain / why a PDF was found | `src/eidp/review/_pages/pdf_manual_entry.py` shows selected PDF, source page, confidence, and discovery evidence log; `school_year_tasks.py` now labels crawl entry source quality. | Mostly covered locally; Windows click-through not revalidated after latest UI. |
| Minimize manual URL entry | `school_year_tasks.py` has UI buttons for initial URL/PDF bootstrap and weekly rediscovery; `URL追加` supports reusable page URLs and CSV bulk import. Web search now rejects known third-party directory/government-index URLs before registering `school_site`. Initial-bootstrap completion now preserves official-index yield details (`official_index_rows_extracted`, `official_index_rows_matched`, URL added/upgraded counts, and no-new-URL prefectures) for the operator UI. | Partial: manual entry is reduced and the reason for low yield is more visible, but prefectures without school-publication links and schools whose official page is not discoverable still need fallback discovery/operator review. |
| Avoid counting stale old-year PDFs as success | `pdf_discovery.py` strict target-FY mode; `target_year_status.py`; `excel_preview.py` warns when target FY data is missing; `school_fiscal_year_status.py` tracks stale fallback separately. | Mostly covered for current pipeline; needs Windows E2E validation with real data after latest branch. |
| Make PDF確認 usable | `school_year_tasks.py` now works as the main operator task board: progress bar, work-lane buttons for URL gaps / target-year PDF wait / stale PDFs / PDF確認・手入力 / dept changes / Excel preview, and preserved filters. `PDF確認・手入力` now adds queue-level next-action summaries, year buckets, editable/read-only counts, focused-doc auto expansion, evidence panel, PDF preview/download, lock handling, and manual entry save path. | Improved locally with UI wiring tests; user still needs final real-workload UI feedback. |
| Review school-universe changes from official remarks | `src/eidp/review/_pages/prefecture_remarks.py` now has dedicated page for official index coverage and `prefecture_remark` review items. The distribution verifier now proves the packaged official-index seed is nationwide rather than partial. | Covered locally with tests and package gate; real operator review of remark workload remains pending. |
| Excel output should use current target FY | `excel_preview.py` blocks preview generation when target-FY data is zero and shows gap metrics; `competition_exporter.py` defaults business export to `settings.target_fiscal_year`, rejects empty target-year business export, and no longer carries the old auto-select-most-populated-year helper. | Core code covered locally; remaining risk is Windows UI click-through and real template/operator validation. |
| Windows operator delivery | `dist/eidp-windows.zip` rebuilt as v67 at commit `0a0825b`, verifier `ok=true`, `git_dirty=false`, wheelhouse 82 wheels. Remote Windows smoke confirmed SHA256 match, `settings_page.py` present, no stale `"RC=-1"` launcher token, setup exit code 0, DB created, `school_count=2418`, `school_fiscal_year_status_count=2418`, settings/school-task/app import OK. | Package and setup smoke covered. Full Windows bootstrap to completion and UI click-through are still not complete. |
| Universities ~700 and vocational schools ~1700 | UI filters support `専門学校` / `大学`; official index parsers can parse mixed lists. | Not complete: full university rollout is explicitly v1.2; only pilot scope is planned. |

## Latest Verification Evidence

- `uv run pytest -q` → `804 passed, 5 warnings`
- `uv run ruff check scripts/bootstrap_pdf_pipeline.py src/eidp/review/_pages/school_year_tasks.py tests/unit/test_bootstrap_pdf_pipeline.py tests/unit/test_review_school_year_tasks.py` → passed
- `uv run mypy scripts/bootstrap_pdf_pipeline.py src/eidp/review/_pages/school_year_tasks.py` → passed
- `uv run pytest tests/unit/test_bootstrap_pdf_pipeline.py tests/unit/test_review_school_year_tasks.py -q` → `58 passed`
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
- Windows remote ZIP smoke → SHA256 `d1148d65a5cdd615f998439e661a288a2f23c8d319c0ede32dd3782d6a402c14`, `settings_page.py` present, `school_year_tasks.py` present, `bootstrap_pdf_pipeline.py` present, `BadRcMinusOne=absent`, `RcCapture=ok`, `BuildCommit=0a0825bbea25421b25fba8ca421bd8c065dfd0c1`
- Windows remote setup smoke → `SETUP_EXIT=0`, `IMPORT_OK`, SQLite DB present, `SCHOOL_COUNT=2418`, `TASK_COUNT=2418`

## Missing Before Goal Can Be Marked Complete

1. Validate official-index yield with a full real bootstrap run.
   The packaged seed/parser surface is now gated for all 47 prefectures, but
   some official artifacts do not publish school-publication URLs. The UI now
   preserves and displays official-index yield counters; the next proof needs
   a complete Windows initial acquisition run showing actual URL/PDF yield and
   fallback counts.
2. Run latest ZIP on Windows and verify:
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

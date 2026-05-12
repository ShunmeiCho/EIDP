# EIDP Current Release Status

Updated: 2026-05-12
Branch: `sprint8-handoff-finalize`
Current Mac-verifier-clean package: `dist/eidp-windows-v323.zip`
Package commit: `2f98ce43de1832e368e38331d781d2ecc3c18538`
Package SHA256: `3bcb823d1a7a4695ea5c758532098a6ea4d999a9240becbe535590134c5a4672`

## Verdict

Status: **NOT COMPLETE**

The packaging, setup, SQLite, Task Scheduler, and bounded Windows backend
pipeline are currently reproducible on `ssh win` for v323. The product goal is
still not complete: the current package has not passed browser UI operator
click-through, and the measured operator-reviewable coverage / Excel readiness
remain far below the shipping line.

## Objective Checklist

| Requirement | Current evidence | Status |
| --- | --- | --- |
| 47 prefecture official indexes seed school public URLs | v323 verifier: `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`, `prefecture_seed_school_rows_total=2148`; Windows bounded Saitama run downloaded the current official artifact and added `51` `SchoolSite` rows from `58` extracted / `51` matched rows | Evidence present |
| Discover and download current target-FY PDFs in strict mode | v323 verifier clean; discovery gold-set `22` entries; expected predictions `22/22 exact`; Windows Saitama bounded run crawled `5` official-index sites and found candidates on all `5`, but downloaded `0` strict target-FY PDFs | Mechanically proven, yield failing |
| Exclude stale-year fallback from auto-success | Ship gate now uses operator-reviewable coverage, while strict auto-yield remains diagnostic; gold-set includes `8` publication-lag cases | Partially proven |
| Extract with pdfplumber/PyMuPDF/Tesseract and write only confidence >= 0.70 rows | Unit/package gates cover OCR runtime presence and confidence contracts; Windows Saitama bounded run had `0` downloaded PDFs, so ingest executed but processed `0` documents | Partially proven |
| Append-only DepartmentYearly / SupportRecipient writes | Fresh full unit suite passed; source audits and targeted tests cover demote-plus-new-revision paths in ingest, manual entry, and fiscal-year override | Evidence present, Win UI E2E still missing |
| Excel template output | Package verifier includes Excel/export contracts; current operator-PC preview/download flow is not revalidated on v323 | Partially proven |
| ManualActionLog audit for operator actions | Package verifier includes audit contracts and outbox checks; current operator-PC run not revalidated on v323 | Partially proven |
| ZIP distribution, double-click setup, browser UI offline operation | v323 ZIP verifies clean on macOS packaging gate, was transferred to Windows with matching SHA256, extracted to `C:\Users\cyo20\EIDP-v323-2f98ce4`, and `scripts\first_setup.bat` completed successfully; browser UI click-through remains user-side/unverified | Backend Win proof present, UI proof missing |
| Shipping threshold: operator-reviewable coverage sufficient for operator manual work <=30%, plus Excel readiness | Windows after-bootstrap diagnostics report `target_pdf_auto_yield_pct=0.0` as a diagnostic metric, `operator_reviewable_yield_pct=0.2`, `ship_gate_status=below_gate`, `validate_after_bootstrap_ship_gate_rc=1`, and `ship_readiness_rc=1` | Failing |

## Current Non-Windows Evidence

Commands run for v323:

- `uv run pytest tests/unit -q` -> `1320 passed, 5 warnings`
- `uv run pytest tests/unit/test_discovery_gold_set_seed.py tests/unit/test_discovery_gold_set_summary.py -q` -> `8 passed`
- `uv run eidp eval-discovery-gold --predictions data/discovery-gold-set/expected-predictions.jsonl --fail-on-regression --json` -> `22/22 exact`
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v323.zip` -> `OK core`
- `uv run ruff check src/eidp/scraper/pdf_discovery.py scripts/ship_gate_contract.py src/eidp/reports/ship_readiness.py src/eidp/review/operator_pages.py scripts/verify_windows_distribution.py tests/unit/test_pdf_discovery.py tests/unit/test_ship_gate_contract.py tests/unit/test_reports.py tests/unit/test_cli_reports.py tests/unit/test_operator_proposals.py tests/unit/test_cli_write_lock_contract.py tests/unit/test_windows_distribution_verifier.py` -> `All checks passed`

v323 verifier exposes the current demonstration gap:

- Discovery gold-set entries: `22`
- Outcome distribution: `accepted_target_pdf=6`, `needs_operator_review=6`,
  `no_target_candidate_found=1`, `publication_lag_latest_public=8`,
  `site_fetch_error=1`
- Demonstrated extractor source: `wordpress_download_manager`
- Not yet gold-demonstrated: `data_attribute`, `embed`, `form_action`,
  `input_control`, `meta_refresh`, `onclick`, `select_option`

## Current Windows Backend Evidence

Commands and observations from `ssh win` for v323:

- Uploaded `dist/eidp-windows-v323.zip` to `C:\Users\cyo20\eidp-windows-v323.zip`.
- Windows `Get-FileHash -Algorithm SHA256` -> `3BCB823D1A7A4695EA5C758532098A6EA4D999A9240BECBE535590134C5A4672`.
- Extracted to `C:\Users\cyo20\EIDP-v323-2f98ce4`; `runtime\python\python.exe scripts\validate_windows_install.py .` -> `OK install`, build commit `2f98ce43de1832e368e38331d781d2ecc3c18538`, `build_dirty=false`.
- `scripts\first_setup.bat` -> exit `0`; after-setup validator reported:
  `school_count=2418`, `school_fiscal_year_status_count=2418`,
  `sqlite_integrity_check=ok`, required SQLite tables present,
  `department_change` void columns present, and `uq_document_file_hash` present.
- `eidp db-info` after bounded bootstrap:
  `Schools=2418`, `Departments=9719`, `DepartmentYearly=40731`,
  `SchoolYearStatus=17696`, `SupportRecipient=10022`,
  `SchoolSite=51`, `Document=0`, `CrawlJob=5`.
- `scripts\bootstrap_pdfs.bat --pref saitama --skip-known-url-discovery --url-search off --school-url-crawl off --batch-size 5 --rate-limit 0.2 --request-timeout 15` -> exit `0`.
- Bounded Saitama bootstrap results:
  official artifact `saitama.pdf` downloaded, aggregate `extracted=58`,
  `matched=51`, `added=51`, `review_items=2`; PDF discovery `crawled=5`,
  `found=5`, `downloaded=0`, `failed=0`, `skipped=344`,
  `prefiltered=314`, `candidate_budget_dropped=1725`; ingest `processed=0`.
- Generated RCA queue:
  `data\output\target-year-discovery\bootstrap-20260512_223932-discovery-rca-batch-plan.json`,
  `5` items / `5` total candidates, valid JSON by Python `json.tool`.
- RCA queue buckets from the v323 bounded run:
  school IDs `212`, `15`, `53`, `72`, and `95` are all
  `publication_lag_or_old_target_pdf`.
- Diagnostics after bootstrap:
  `validate_core_rc=0`, `validate_after_setup_rc=0`,
  `validate_after_bootstrap_rc=0`,
  `validate_after_bootstrap_ship_gate_rc=1`, `ship_readiness_rc=1`.
- The Windows scheduled task `EIDP Weekly Run` was updated by setup to
  `C:\Users\cyo20\EIDP-v323-2f98ce4\scripts\weekly_run.bat`.

## Next Required Proof

1. Run browser UI operator click-through on the current v323 Windows install:
   `EIDP-start.bat` -> operator pages -> Excel preview/download -> diagnostics.
2. Expand Windows official-index discovery beyond the 5-site Saitama bounded
   smoke and record target PDFs accepted, publication-lag queue,
   manual-required queue, and errors.
3. Use the generated RCA batch plan to classify whether the current zero
   strict-target result is due to upstream publication lag, crawler false
   negatives, or missing manual fallback/gold-set demonstrations.
4. Compare measured operator-reviewable coverage, manual workload, and Excel
   readiness against the shipping line; keep strict target-PDF acquisition as a
   diagnostic metric during the May publication-lag window.
5. Only after those numbers pass should the branch be treated as release-ready.

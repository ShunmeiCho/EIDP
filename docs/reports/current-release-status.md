# EIDP Current Release Status

Updated: 2026-05-12
Branch: `sprint8-handoff-finalize`
Current Mac-verifier-clean package: `dist/eidp-windows-v324.zip`
Package commit: `9d9b9b32eb49f29f8da81ee31bde2e6f7461c1dd`
Package SHA256: `29fd999376aacfdc40c13242c980b6fb900f84f2dfc036530d1d1dd538ecaf3e`
Latest Windows-backend-proven package: `dist/eidp-windows-v324.zip`

## Verdict

Status: **NOT COMPLETE**

The current source/ZIP snapshot is v324 and passes the default macOS package
verifier. The packaging, setup, SQLite, Task Scheduler, and bounded Windows
backend pipeline are reproducible on `ssh win` for v324. The product goal is
still not complete: v324 has not passed browser UI operator click-through, and
the measured operator-reviewable coverage / Excel readiness remain far below
the shipping line.

## Objective Checklist

| Requirement | Current evidence | Status |
| --- | --- | --- |
| 47 prefecture official indexes seed school public URLs | v324 verifier: `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`, `prefecture_seed_school_rows_total=2148`; Windows v324 bounded Saitama run downloaded the current official artifact and added `51` `SchoolSite` rows from `58` extracted / `51` matched rows | Evidence present |
| Discover and download current target-FY PDFs in strict mode | v324 verifier clean by default; discovery gold-set `22` entries; expected predictions `22/22 exact`; Windows v324 Saitama bounded run crawled `5` official-index sites and found candidates on all `5`, but downloaded `0` strict target-FY PDFs | Mechanically proven, yield failing |
| Exclude stale-year fallback from auto-success | Ship gate uses operator-reviewable coverage, while strict auto-yield remains diagnostic; gold-set includes `8` publication-lag cases | Partially proven |
| Extract with pdfplumber/PyMuPDF/Tesseract and write only confidence >= 0.70 rows | Unit/package gates cover OCR runtime presence and confidence contracts; Windows Saitama bounded run had `0` downloaded PDFs, so ingest executed but processed `0` documents | Partially proven |
| Append-only DepartmentYearly / SupportRecipient writes | Fresh full unit suite passed; source audits and targeted tests cover demote-plus-new-revision paths in ingest, manual entry, and fiscal-year override | Evidence present, Win UI E2E still missing |
| Excel template output | v324 package verifier includes Excel/export contracts and centralized confidence threshold contract; current operator-PC preview/download flow is not revalidated on v324 | Partially proven |
| ManualActionLog audit for operator actions | v324 package verifier includes audit contracts and outbox checks; current operator-PC run not revalidated through browser UI on v324 | Partially proven |
| ZIP distribution, double-click setup, browser UI offline operation | v324 ZIP verifies clean on macOS packaging gate, was transferred to Windows with matching SHA256, extracted to `C:\Users\cyo20\EIDP-v324-9d9b9b3`, and `scripts\first_setup.bat` completed successfully; browser UI click-through remains user-side/unverified | Backend Win proof present, UI proof missing |
| Shipping threshold: operator-reviewable coverage sufficient for operator manual work <=30%, plus Excel readiness | Windows after-bootstrap diagnostics report `target_pdf_auto_yield_pct=0.0` as a diagnostic metric, `operator_reviewable_yield_pct=0.2`, `ship_gate_status=below_gate`, `validate_after_bootstrap_ship_gate_rc=1`, and `ship_readiness_rc=1` | Failing |

## Current Non-Windows Evidence

Commands run for v324:

- `uv run pytest tests/unit -q` -> `1327 passed, 5 warnings`
- `uv run eidp eval-discovery-gold --predictions data/discovery-gold-set/expected-predictions.jsonl --fail-on-regression --json` -> `22/22 exact`
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v324.zip` -> `OK core`
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v324.zip --require-demonstrated-discovery-patterns` -> expected `FAIL core` because `data_attribute`, `embed`, `form_action`, `input_control`, `meta_refresh`, `onclick`, and `select_option` have no discovery gold-set demonstrations yet
- `uv run ruff check scripts/verify_windows_distribution.py tests/unit/test_windows_distribution_verifier.py` -> `All checks passed`

v324 verifier exposes the current demonstration gap:

- Discovery gold-set entries: `22`
- Outcome distribution: `accepted_target_pdf=6`, `needs_operator_review=6`,
  `no_target_candidate_found=1`, `publication_lag_latest_public=8`,
  `site_fetch_error=1`
- Demonstrated extractor source: `wordpress_download_manager`
- Not yet gold-demonstrated: `data_attribute`, `embed`, `form_action`,
  `input_control`, `meta_refresh`, `onclick`, `select_option`

## Current Windows Backend Evidence

Commands and observations from `ssh win` for v324:

- Uploaded `dist/eidp-windows-v324.zip` to `C:\Users\cyo20\eidp-windows-v324.zip`.
- Windows `Get-FileHash -Algorithm SHA256` -> `29FD999376AACFDC40C13242C980B6FB900F84F2DFC036530D1D1DD538ECAF3E`.
- Extracted to `C:\Users\cyo20\EIDP-v324-9d9b9b3`; `runtime\python\python.exe scripts\validate_windows_install.py .` -> `OK install`, build commit `9d9b9b32eb49f29f8da81ee31bde2e6f7461c1dd`, `build_dirty=false`.
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
  `data\output\target-year-discovery\bootstrap-20260512_231557-discovery-rca-batch-plan.json`,
  `5` items / `5` total candidates, valid JSON by Python `json.tool`.
- RCA queue buckets from the v324 bounded run:
  all `5` items are `publication_lag_or_old_target_pdf`, with candidate
  counts `1992`, `31`, `28`, `24`, and `9`.
- Diagnostics after bootstrap:
  `validate_core_rc=0`, `validate_after_setup_rc=0`,
  `validate_after_bootstrap_rc=0`,
  `validate_after_bootstrap_ship_gate_rc=1`, `ship_readiness_rc=1`.
- The Windows scheduled task `EIDP Weekly Run` was updated by setup to
  `C:\Users\cyo20\EIDP-v324-9d9b9b3\scripts\weekly_run.bat`.

## Next Required Proof

1. Run browser UI operator click-through on the current Windows install:
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

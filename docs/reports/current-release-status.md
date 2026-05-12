# EIDP Current Release Status

Updated: 2026-05-12
Branch: `sprint8-handoff-finalize`
Current Mac-verifier-clean package: `dist/eidp-windows-v325.zip`
Package commit: `8670acca932ec857785ade1a02339fc0080aaec4`
Package SHA256: `96bdc4685bd915bc3d0c7385b208c7922e0666ab53f434690ebcf22d321a3cf7`
Latest Windows-backend-proven package: `dist/eidp-windows-v324.zip`
Latest Windows-core-validated package: `dist/eidp-windows-v325.zip`

## Verdict

Status: **NOT COMPLETE**

The current source/ZIP snapshot is v325 and passes the default macOS package
verifier. v325 also passes the Windows core install validator after ZIP
extraction on `ssh win`. The packaging, setup, SQLite, Task Scheduler, and
bounded Windows backend pipeline are reproducible on `ssh win` for v324. The
product goal is still not complete: v325 has not passed browser UI operator
click-through or full Windows setup/bootstrap, and
the measured operator-reviewable coverage / Excel readiness remain far below
the shipping line.

## Objective Checklist

| Requirement | Current evidence | Status |
| --- | --- | --- |
| 47 prefecture official indexes seed school public URLs | v324 verifier: `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`, `prefecture_seed_school_rows_total=2148`; Windows v324 bounded Saitama run downloaded the current official artifact and added `51` `SchoolSite` rows from `58` extracted / `51` matched rows | Evidence present |
| Discover and download current target-FY PDFs in strict mode | v325 verifier clean by default; discovery gold-set `22` entries; expected predictions `22/22 exact`; Windows v324 Saitama 25-site run crawled `25` official-index sites, found candidates on `24`, downloaded `3`, ingested `3`, and produced `2` Excel-ready schools | Mechanically proven, yield failing |
| Exclude stale-year fallback from auto-success | Ship gate uses operator-reviewable coverage, while strict auto-yield remains diagnostic; gold-set includes `8` publication-lag cases; post-v324 source fix `8670acc` rejects explicit stale link labels such as `R7確認申請書類` even when prefecture-index evidence is trusted | Partially proven |
| Extract with pdfplumber/PyMuPDF/Tesseract and write only confidence >= 0.70 rows | Unit/package gates cover OCR runtime presence and confidence contracts; Windows v324 Saitama 25-site run processed `3` documents, created `9` departments, and wrote `10` yearly rows; one downloaded document was `review_pending` rather than Excel-ready | Partially proven |
| Append-only DepartmentYearly / SupportRecipient writes | Fresh full unit suite passed; source audits and targeted tests cover demote-plus-new-revision paths in ingest, manual entry, and fiscal-year override | Evidence present, Win UI E2E still missing |
| Excel template output | v325 package verifier includes Excel/export contracts and centralized confidence threshold contract; current operator-PC preview/download flow is not revalidated on v325 | Partially proven |
| ManualActionLog audit for operator actions | v325 package verifier includes audit contracts and outbox checks; current operator-PC run not revalidated through browser UI on v325 | Partially proven |
| ZIP distribution, double-click setup, browser UI offline operation | v324 ZIP verifies clean on macOS packaging gate, was transferred to Windows with matching SHA256, extracted to `C:\Users\cyo20\EIDP-v324-9d9b9b3`, and `scripts\first_setup.bat` completed successfully; browser UI click-through remains user-side/unverified | Backend Win proof present, UI proof missing |
| Shipping threshold: operator-reviewable coverage sufficient for operator manual work <=30%, plus Excel readiness | Windows v324 25-site diagnostics report `target_pdf_auto_yield_pct=0.1` as a diagnostic metric, `operator_reviewable_yield_pct=0.8`, `ship_gate_status=below_gate`, `validate_after_bootstrap_ship_gate_rc=1`, and `ship_readiness_rc=1` | Failing |

## Current Non-Windows Evidence

Commands run for v325 source/package:

- `uv run pytest tests/unit -q` -> `1329 passed, 5 warnings`
- `uv run eidp eval-discovery-gold --predictions data/discovery-gold-set/expected-predictions.jsonl --fail-on-regression --json` -> `22/22 exact`
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v325.zip` -> `OK core`
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v325.zip --require-demonstrated-discovery-patterns` -> expected `FAIL core` because `data_attribute`, `embed`, `form_action`, `input_control`, `meta_refresh`, `onclick`, and `select_option` have no discovery gold-set demonstrations yet
- `uv run ruff check src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py` -> `All checks passed`

v325 verifier exposes the current demonstration gap:

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

Additional v324 25-site backend run:

- `scripts\bootstrap_pdfs.bat --pref saitama --skip-known-url-discovery --url-search off --school-url-crawl off --batch-size 25 --rate-limit 0.2 --request-timeout 15` -> exit `0`.
- PDF discovery: `crawled=25`, `found=24`, `downloaded=3`, `failed=2`,
  `skipped=1050`, `prefiltered=775`, `cached_rejections=694`,
  `candidate_budget_dropped=5245`.
- Ingest: `processed=3`, `departments_created=9`, `yearly_upserted=10`,
  `skipped=0`.
- Rebuilt status: `excel_ready=2`, `target_pdf_auto_acquired_count=2`,
  `operator_reviewable_count=19`, `operator_reviewable_yield_pct=0.8`,
  `ship_gate_status=below_gate`.
- Evidence review found one stale-label acceptance in v324:
  `R7確認申請書類 様式第2号` was accepted via
  `prefecture_index_current_year`; source commit `8670acc` fixes this by
  rejecting explicit stale era labels before trusted index evidence can
  promote the candidate.

Windows core validation for v325:

- Uploaded `dist/eidp-windows-v325.zip` to
  `C:\Users\cyo20\eidp-windows-v325.zip`.
- Windows `Get-FileHash -Algorithm SHA256` ->
  `96BDC4685BD915BC3D0C7385B208C7922E0666AB53F434690EBCF22D321A3CF7`.
- Extracted to `C:\Users\cyo20\EIDP-v325-8670acc`;
  `runtime\python\python.exe scripts\validate_windows_install.py .` ->
  `OK install`, build commit `8670acca932ec857785ade1a02339fc0080aaec4`,
  `build_dirty=false`.

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

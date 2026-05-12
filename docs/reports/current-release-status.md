# EIDP Current Release Status

Updated: 2026-05-13
Branch: `sprint8-handoff-finalize`
Current Mac-verifier-clean package: `dist/eidp-windows-v330.zip`
Package commit: `1de0ec75adbb936b36abc215255790e21bdaba24`
Package SHA256: `79e383312c57413a2dfdffa39cdf7bb8d87e5b89a3118a4a17ae705d425ce1ad`
Latest Windows-core-validated package: `dist/eidp-windows-v330.zip`
Latest Windows-setup-proven package: `dist/eidp-windows-v330.zip`
Latest Windows-bounded-bootstrap-proven package: `dist/eidp-windows-v330.zip`

## Verdict

Status: **NOT COMPLETE**

The current source/ZIP snapshot is v330 and passes the default macOS package
verifier. v330 keeps the v326 strict-mode fix for opaque WordPress Download
Manager wrappers, the v328 cross-school candidate rejection, and the v329
actionable RCA counts. It also fixes a Windows-discovered blocker where raw URL
control characters could pass `urlparse()`-based safety checks and crash
`httpx` during PDF download. v330 setup, SQLite initialization, diagnostics,
and a bounded 50-site Saitama bootstrap are reproducible on `ssh win`. The
product goal is still not complete: browser UI operator click-through is
missing, and the measured operator-reviewable coverage / Excel readiness remain
far below the shipping line.

## Objective Checklist

| Requirement | Current evidence | Status |
| --- | --- | --- |
| 47 prefecture official indexes seed school public URLs | v330 verifier: `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`, `prefecture_seed_school_rows_total=2148`; Windows v330 Saitama run downloaded the current official artifact and added `51` `SchoolSite` rows from `58` extracted / `51` matched rows | Evidence present |
| Discover and download current target-FY PDFs in strict mode | v330 verifier clean by default; discovery gold-set `22` entries; Windows v330 Saitama 50-site run crawled `50` official-index sites, found candidates on `47`, downloaded `7`, processed `7`, and produced `5` Excel-ready schools | Mechanically proven, yield failing |
| Exclude stale-year fallback from auto-success | Ship gate uses operator-reviewable coverage, while strict auto-yield remains diagnostic; gold-set includes `8` publication-lag cases; Windows v330 evidence shows stale target PDFs rejected as `fiscal_year_mismatch:*`; malformed raw URLs are now recorded as `unsafe_url` instead of aborting the batch | Partially proven |
| Extract with pdfplumber/PyMuPDF/Tesseract and write only confidence >= 0.70 rows | Unit/package gates cover OCR runtime presence and confidence contracts; Windows v330 Saitama 50-site run processed `7` documents, ingested `5`, and wrote `18` yearly rows; `5` schools are Excel-ready | Partially proven |
| Append-only DepartmentYearly / SupportRecipient writes | Fresh full unit suite passed; source audits and targeted tests cover demote-plus-new-revision paths in ingest, manual entry, and fiscal-year override | Evidence present, Win UI E2E still missing |
| Excel template output | v330 package verifier includes Excel/export contracts and centralized confidence threshold contract; current operator-PC preview/download flow is not revalidated on v330 | Partially proven |
| ManualActionLog audit for operator actions | v330 package verifier includes audit contracts and outbox checks; current operator-PC run not revalidated through browser UI on v330 | Partially proven |
| ZIP distribution, double-click setup, browser UI offline operation | v330 ZIP verifies clean on macOS packaging gate, was transferred to Windows with matching SHA256, extracted to `C:\Users\cyo20\EIDP-v330-1de0ec7`, and `scripts\first_setup.bat` completed successfully; browser UI click-through remains unverified | Backend Win setup proof present, UI proof missing |
| Shipping threshold: operator-reviewable coverage sufficient for operator manual work <=30%, plus Excel readiness | Windows v330 50-site diagnostics report `target_pdf_auto_yield_pct=0.2` as a diagnostic metric, `operator_reviewable_yield_pct=1.6`, `excel_ready=5`, `ship_gate_status=below_gate`, `validate_after_bootstrap_ship_gate_rc=1`, and `ship_readiness_rc=1` | Failing |

## Current Non-Windows Evidence

Commands run for v330 source/package:

- `uv run pytest tests/unit -q` -> `1336 passed, 5 warnings`
- `uv run pytest tests/unit/test_url_discovery.py tests/unit/test_pdf_discovery.py -q` -> `161 passed, 5 warnings`
- `uv run ruff check src/eidp/scraper/url_discovery.py src/eidp/scraper/pdf_discovery.py tests/unit/test_url_discovery.py tests/unit/test_pdf_discovery.py` -> `All checks passed`
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v330.zip` -> `OK core`
- One-off strict download check for `https://i-heiseigakuen.ac.jp/download/%e6%a7%98%e5%bc%8f%ef%bc%92/?wpdmdl=4821&refresh=6a0340a79aaeb1778598055` with anchor `ダウンロード` -> `(None, None, 0, 'target', 'target_fiscal_year_not_detected')`
- Rebuilt the v326 Windows Saitama RCA batch plan locally with v327 code and
  verified publication-lag packets now surface `fiscal_year_mismatch:*` rows
  before `candidate_budget_dropped` rows.

v330 verifier exposes the current demonstration gap:

- Discovery gold-set entries: `22`
- Outcome distribution: `accepted_target_pdf=6`, `needs_operator_review=6`,
  `no_target_candidate_found=1`, `publication_lag_latest_public=8`,
  `site_fetch_error=1`
- Demonstrated extractor source: `wordpress_download_manager`
- Not yet gold-demonstrated: `data_attribute`, `embed`, `form_action`,
  `input_control`, `meta_refresh`, `onclick`, `select_option`

## Current Windows Backend Evidence

Commands and observations from `ssh win` for v330 setup/bootstrap:

- Uploaded `dist/eidp-windows-v330.zip` to
  `C:\Users\cyo20\eidp-windows-v330.zip`.
- Windows `Get-FileHash -Algorithm SHA256` ->
  `79E383312C57413A2DFDFFA39CDF7BB8D87E5B89A3118A4A17AE705D425CE1AD`.
- Extracted to `C:\Users\cyo20\EIDP-v330-1de0ec7`.
- `scripts\first_setup.bat` -> exit `0`; after-setup validator reported:
  `school_count=2418`, `school_fiscal_year_status_count=2418`,
  `sqlite_integrity_check=ok`, required SQLite tables present,
  `department_change` void columns present, and `uq_document_file_hash` present.
- The Windows scheduled task `EIDP Weekly Run` was updated by setup to
  `C:\Users\cyo20\EIDP-v330-1de0ec7\scripts\weekly_run.bat`.
- Targeted strict-mode check for the prior 入間看護専門学校 false-positive URL
  `https://i-heiseigakuen.ac.jp/download/%e6%a7%98%e5%bc%8f%ef%bc%92/?wpdmdl=4821&refresh=6a0340a79aaeb1778598055`
  with opaque anchor `download` returned
  `(None, None, 0, 'target', 'target_fiscal_year_not_detected')`.

- `scripts\bootstrap_pdfs.bat --pref saitama --skip-known-url-discovery --url-search off --school-url-crawl off --batch-size 50 --rate-limit 0.2 --request-timeout 15` -> exit `0`.
- Official Saitama artifact downloaded; aggregate `extracted=58`,
  `matched=51`, `added=51`, `review_items=2`.
- PDF discovery: `crawled=50`, `found=47`, `downloaded=7`, `failed=6`,
  `skipped=1218`, `prefiltered=904`, `cached_rejections=286`,
  `candidate_school_mismatch=5160`, `candidate_budget_dropped=853`,
  `rejection_reason_fiscal_year_mismatch=319`,
  `rejection_reason_target_fiscal_year_not_detected=21`,
  `rejection_reason_unsafe_url=1`.
- Ingest: `processed=7`, `departments_created=12`, `yearly_upserted=18`,
  `skipped=1`.
- Rebuilt status: `excel_ready=5`, `target_pdf_auto_acquired_count=5`,
  `operator_reviewable_count=39`, `operator_reviewable_yield_pct=1.6`,
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
- The v330 RCA batch plan has `10` items / `43` actionable candidates. Top
  buckets include `target_form_without_year_evidence` for 浦和専門学校 and
  大宮歯科衛生士専門学校, `non_target_candidates_only` for several schools,
  and `publication_lag_or_old_target_pdf` for 東京IT会計公務員専門学校大宮校.

## Next Required Proof

1. Run browser UI operator click-through on the current Windows install:
   `EIDP-start.bat` -> operator pages -> Excel preview/download -> diagnostics.
2. Expand Windows official-index discovery beyond the 50-site Saitama bounded
   smoke and record target PDFs accepted, publication-lag queue,
   manual-required queue, and errors.
3. Use the generated RCA batch plan to classify whether the current low
   strict-target result is due to upstream publication lag, crawler false
   negatives, or missing manual fallback/gold-set demonstrations.
4. Compare measured operator-reviewable coverage, manual workload, and Excel
   readiness against the shipping line; keep strict target-PDF acquisition as a
   diagnostic metric during the May publication-lag window.
5. Only after those numbers pass should the branch be treated as release-ready.

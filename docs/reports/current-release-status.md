# EIDP Current Release Status

Updated: 2026-05-13
Branch: `sprint8-handoff-finalize`
Current Mac-verifier-clean package: `dist/eidp-windows-v329.zip`
Package commit: `3e1afc532f99b52927854d792259abdb13282fea`
Package SHA256: `e923d02506dd2b9a3abb078a152421381573544ab3f1de9c0b12dffc02d6b1b2`
Latest Windows-core-validated package: `dist/eidp-windows-v329.zip`
Latest Windows-setup-proven package: `dist/eidp-windows-v328.zip`
Latest Windows-bounded-bootstrap-proven package: `dist/eidp-windows-v328.zip`

## Verdict

Status: **NOT COMPLETE**

The current source/ZIP snapshot is v329 and passes the default macOS package
verifier. v329 keeps the v326 strict-mode fix for opaque WordPress Download
Manager wrappers, improves RCA packet evidence sampling so candidate-budget
noise does not hide fiscal-year mismatch / missing-year evidence during manual
investigation, and rejects candidates whose anchor/URL explicitly names a
different school before download. v329 also adds actionable RCA counts so
already-explained budget/cross-school noise does not inflate manual workload
estimates. v329 extracts and passes the core
Windows install validator on `ssh win`. The setup, SQLite, Task Scheduler, and
bounded Windows bootstrap pipeline are reproducible on `ssh win` for v328. The
product goal is still not complete:
browser UI operator click-through is missing, and the measured
operator-reviewable coverage / Excel readiness remain far below the shipping
line.

## Objective Checklist

| Requirement | Current evidence | Status |
| --- | --- | --- |
| 47 prefecture official indexes seed school public URLs | v328 verifier: `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`, `prefecture_seed_school_rows_total=2148`; Windows v328 Saitama run downloaded the current official artifact and added `51` `SchoolSite` rows from `58` extracted / `51` matched rows | Evidence present |
| Discover and download current target-FY PDFs in strict mode | v328 verifier clean by default; discovery gold-set `22` entries; expected predictions `22/22 exact`; Windows v328 Saitama 25-site run crawled `25` official-index sites, found candidates on `24`, downloaded `1`, ingested `1`, and produced `1` Excel-ready school | Mechanically proven, yield failing |
| Exclude stale-year fallback from auto-success | Ship gate uses operator-reviewable coverage, while strict auto-yield remains diagnostic; gold-set includes `8` publication-lag cases; Windows v328 evidence shows stale target PDFs rejected as `fiscal_year_mismatch:*` and the ambiguous 入間看護専門学校 `wpdmdl=4821` wrapper rejected as `target_fiscal_year_not_detected` instead of trusting prefecture-index evidence alone | Partially proven |
| Extract with pdfplumber/PyMuPDF/Tesseract and write only confidence >= 0.70 rows | Unit/package gates cover OCR runtime presence and confidence contracts; Windows v328 Saitama 25-site run processed `1` document and wrote `1` yearly row; the downloaded document was Excel-ready | Partially proven |
| Append-only DepartmentYearly / SupportRecipient writes | Fresh full unit suite passed; source audits and targeted tests cover demote-plus-new-revision paths in ingest, manual entry, and fiscal-year override | Evidence present, Win UI E2E still missing |
| Excel template output | v328 package verifier includes Excel/export contracts and centralized confidence threshold contract; current operator-PC preview/download flow is not revalidated on v328 | Partially proven |
| ManualActionLog audit for operator actions | v328 package verifier includes audit contracts and outbox checks; current operator-PC run not revalidated through browser UI on v328 | Partially proven |
| ZIP distribution, double-click setup, browser UI offline operation | v328 ZIP verifies clean on macOS packaging gate, was transferred to Windows with matching SHA256, extracted to `C:\Users\cyo20\EIDP-v328-3368047`, and `scripts\first_setup.bat` completed successfully; browser UI click-through remains unverified | Backend Win setup proof present, UI proof missing |
| Shipping threshold: operator-reviewable coverage sufficient for operator manual work <=30%, plus Excel readiness | Windows v328 25-site diagnostics report `target_pdf_auto_yield_pct=0.0` as a diagnostic metric, `operator_reviewable_yield_pct=0.8`, `excel_ready=1`, `ship_gate_status=below_gate`, `validate_after_bootstrap_ship_gate_rc=1`, and `ship_readiness_rc=1` | Failing |

## Current Non-Windows Evidence

Commands run for v329 source/package:

- `uv run pytest tests/unit -q` -> `1334 passed, 5 warnings`
- `uv run pytest tests/unit/test_cli_discovery_rca_packet.py tests/unit/test_discovery_evidence_summary.py -q` -> `34 passed`
- `uv run pytest tests/unit/test_pdf_discovery.py -q` -> `145 passed, 5 warnings`
- `uv run eidp eval-discovery-gold --predictions data/discovery-gold-set/expected-predictions.jsonl --fail-on-regression --json` -> `22/22 exact`
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v329.zip` -> `OK core`
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v329.zip --require-demonstrated-discovery-patterns` -> expected `FAIL core` because `data_attribute`, `embed`, `form_action`, `input_control`, `meta_refresh`, `onclick`, and `select_option` have no discovery gold-set demonstrations yet
- `uv run ruff check src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py` -> `All checks passed`
- One-off strict download check for `https://i-heiseigakuen.ac.jp/download/%e6%a7%98%e5%bc%8f%ef%bc%92/?wpdmdl=4821&refresh=6a0340a79aaeb1778598055` with anchor `ダウンロード` -> `(None, None, 0, 'target', 'target_fiscal_year_not_detected')`
- Rebuilt the v326 Windows Saitama RCA batch plan locally with v327 code and
  verified publication-lag packets now surface `fiscal_year_mismatch:*` rows
  before `candidate_budget_dropped` rows.

v329 verifier exposes the current demonstration gap:

- Discovery gold-set entries: `22`
- Outcome distribution: `accepted_target_pdf=6`, `needs_operator_review=6`,
  `no_target_candidate_found=1`, `publication_lag_latest_public=8`,
  `site_fetch_error=1`
- Demonstrated extractor source: `wordpress_download_manager`
- Not yet gold-demonstrated: `data_attribute`, `embed`, `form_action`,
  `input_control`, `meta_refresh`, `onclick`, `select_option`

## Current Windows Backend Evidence

Commands and observations from `ssh win` for v329 package-level validation:

- Uploaded `dist/eidp-windows-v329.zip` to
  `C:\Users\cyo20\eidp-windows-v329.zip`.
- Windows `Get-FileHash -Algorithm SHA256` ->
  `E923D02506DD2B9A3ABB078A152421381573544AB3F1DE9C0B12DFFC02D6B1B2`.
- Extracted to `C:\Users\cyo20\EIDP-v329-3e1afc5`;
  `runtime\python\python.exe scripts\validate_windows_install.py .` ->
  `OK install`, build commit `3e1afc532f99b52927854d792259abdb13282fea`,
  `build_dirty=false`, `wheel_count=78`.

Commands and observations from `ssh win` for v328 setup/bootstrap:

- `scripts\first_setup.bat` -> exit `0`; after-setup validator reported:
  `school_count=2418`, `school_fiscal_year_status_count=2418`,
  `sqlite_integrity_check=ok`, required SQLite tables present,
  `department_change` void columns present, and `uq_document_file_hash` present.
- The Windows scheduled task `EIDP Weekly Run` was updated by setup to
  `C:\Users\cyo20\EIDP-v328-3368047\scripts\weekly_run.bat`.
- Targeted strict-mode check for the prior 入間看護専門学校 false-positive URL
  `https://i-heiseigakuen.ac.jp/download/%e6%a7%98%e5%bc%8f%ef%bc%92/?wpdmdl=4821&refresh=6a0340a79aaeb1778598055`
  with opaque anchor `download` returned
  `(None, None, 0, 'target', 'target_fiscal_year_not_detected')`.

- `scripts\bootstrap_pdfs.bat --pref saitama --skip-known-url-discovery --url-search off --school-url-crawl off --batch-size 25 --rate-limit 0.2 --request-timeout 15` -> exit `0`.
- Official Saitama artifact downloaded; aggregate `extracted=58`,
  `matched=51`, `added=51`, `review_items=2`.
- PDF discovery: `crawled=25`, `found=24`, `downloaded=1`, `failed=2`,
  `skipped=895`, `prefiltered=638`, `cached_rejections=286`,
  `candidate_school_mismatch=5160`, `candidate_budget_dropped=625`,
  `rejection_reason_fiscal_year_mismatch=245`,
  `rejection_reason_target_fiscal_year_not_detected=10`.
- Ingest: `processed=1`, `departments_created=0`, `yearly_upserted=1`,
  `skipped=0`.
- Rebuilt status: `excel_ready=1`, `target_pdf_auto_acquired_count=1`,
  `operator_reviewable_count=20`, `operator_reviewable_yield_pct=0.8`,
  `ship_gate_status=below_gate`.
- Diagnostics after bootstrap:
  `validate_core_rc=0`, `validate_after_setup_rc=0`,
  `validate_after_bootstrap_rc=0`,
  `validate_after_bootstrap_ship_gate_rc=1`, `ship_readiness_rc=1`.
- DB evidence after the 25-site run has `Document=1` and `CrawlJob=25`; the
  accepted download is only `上尾中央看護専門学校`.
- DB status for `school_id=760` / 入間看護専門学校 is
  `pdf_status=publication_lag`, `blocking_reason=publication_lag_latest_public`,
  and `excel_ready=0`.
- Evidence review confirmed stale-label rejection: the prior v324 false
  acceptance `R7確認申請書類 様式第2号` is now recorded as
  `fiscal_year_mismatch:2025`.
- Rebuilding the v328 Saitama RCA batch plan locally with v329 code preserved
  total evidence counts while adding actionable counts; for example, the three
  O-Hara publication-lag packets remain `candidate_count=1992` but now report
  only `actionable_candidate_count=86-93`.

## Next Required Proof

1. Run browser UI operator click-through on the current Windows install:
   `EIDP-start.bat` -> operator pages -> Excel preview/download -> diagnostics.
2. Expand Windows official-index discovery beyond the 25-site Saitama bounded
   smoke and record target PDFs accepted, publication-lag queue,
   manual-required queue, and errors.
3. Use the generated RCA batch plan to classify whether the current zero
   strict-target result is due to upstream publication lag, crawler false
   negatives, or missing manual fallback/gold-set demonstrations.
4. Compare measured operator-reviewable coverage, manual workload, and Excel
   readiness against the shipping line; keep strict target-PDF acquisition as a
   diagnostic metric during the May publication-lag window.
5. Only after those numbers pass should the branch be treated as release-ready.

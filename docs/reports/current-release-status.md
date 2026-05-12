# EIDP Current Release Status

Updated: 2026-05-13
Branch: `sprint8-handoff-finalize`
Current Mac-verifier-clean package: `dist/eidp-windows-v332.zip`
Package commit: `9fe773e972f76043fd5d3d96431b18754ee05711`
Package SHA256: `5af664c961768b9003ebbb9191d3ed5ef2fffdd76337b09cba92f14eaf97c5a2`
Latest Windows-core-validated package: `dist/eidp-windows-v332.zip`
Latest Windows-setup-proven package: `dist/eidp-windows-v332.zip`
Latest Windows-bounded-bootstrap-proven package: `dist/eidp-windows-v332.zip`

## Verdict

Status: **NOT COMPLETE**

The current source/ZIP snapshot is v332 and passes the default macOS package
verifier. v332 keeps the v326 strict-mode fix for opaque WordPress Download
Manager wrappers, the v328 cross-school candidate rejection, the v329
actionable RCA counts, the v330 raw-control-character URL guard, and the v331
one-retry guard for transient registered-page timeouts plus structured
`discovery_error` evidence (`error_code`, `retryable`). It adds a committed
HAL東京/NKZ embed-subpage discovery demonstration so the `<embed>` extractor is
no longer only unit-test covered. Windows setup, SQLite initialization,
diagnostics, and a bounded 50-site Saitama bootstrap are proven on v332. The
product goal is still not complete: browser UI operator click-through is
missing, and the measured
operator-reviewable coverage / Excel readiness remain far below the shipping
line.

## Objective Checklist

| Requirement | Current evidence | Status |
| --- | --- | --- |
| 47 prefecture official indexes seed school public URLs | v332 verifier: `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`, `prefecture_seed_school_rows_total=2148`; Windows v332 Saitama run downloaded the current official artifact and added `51` `SchoolSite` rows from `58` extracted / `51` matched rows | Evidence present |
| Discover and download current target-FY PDFs in strict mode | v332 verifier clean by default; discovery gold-set `23` entries; Windows v332 Saitama 50-site run crawled `50` official-index sites, found candidates on `49`, downloaded `7`, processed `7`, and produced `5` Excel-ready schools | Mechanically proven, yield failing |
| Exclude stale-year fallback from auto-success | Ship gate uses operator-reviewable coverage, while strict auto-yield remains diagnostic; gold-set includes `9` publication-lag cases; Windows v332 evidence shows stale target PDFs rejected as `fiscal_year_mismatch:*`; malformed raw URLs are recorded as `unsafe_url` instead of aborting the batch | Partially proven |
| Extract with pdfplumber/PyMuPDF/Tesseract and write only confidence >= 0.70 rows | Unit/package gates cover OCR runtime presence and confidence contracts; Windows v332 Saitama 50-site run processed `7` documents, ingested `5`, and wrote `18` yearly rows; `5` schools are Excel-ready | Partially proven |
| Append-only DepartmentYearly / SupportRecipient writes | Fresh full unit suite passed; source audits and targeted tests cover demote-plus-new-revision paths in ingest, manual entry, and fiscal-year override | Evidence present, Win UI E2E still missing |
| Excel template output | v332 package verifier includes Excel/export contracts and centralized confidence threshold contract; current operator-PC preview/download flow is not revalidated on v332 | Partially proven |
| ManualActionLog audit for operator actions | v332 package verifier includes audit contracts and outbox checks; current operator-PC run not revalidated through browser UI on v332 | Partially proven |
| ZIP distribution, double-click setup, browser UI offline operation | v332 ZIP verifies clean on macOS packaging gate, was transferred to Windows with matching SHA256, extracted to `C:\Users\cyo20\EIDP-v332-9fe773e`, and `scripts\first_setup.bat` completed successfully; browser UI click-through remains unverified | Backend Win setup proof present, UI proof missing |
| Shipping threshold: operator-reviewable coverage sufficient for operator manual work <=30%, plus Excel readiness | Windows v332 50-site diagnostics report `target_pdf_auto_yield_pct=0.2` as a diagnostic metric, `operator_reviewable_yield_pct=1.7`, `excel_ready=5`, `ship_gate_status=below_gate`, `validate_after_bootstrap_ship_gate_rc=1`, and `ship_readiness_rc=1` | Failing |

## Current Non-Windows Evidence

Commands run for v332 source/package:

- `uv run pytest tests/unit -q` -> `1338 passed, 5 warnings`
- `uv run pytest tests/unit/test_pdf_discovery.py -q` -> `148 passed, 5 warnings`
- `uv run ruff check src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py` -> `All checks passed`
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v332.zip` -> `OK core`
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v332.zip --require-demonstrated-discovery-patterns` -> expected failure for the six remaining undemonstrated sources
- One-off strict download check for `https://i-heiseigakuen.ac.jp/download/%e6%a7%98%e5%bc%8f%ef%bc%92/?wpdmdl=4821&refresh=6a0340a79aaeb1778598055` with anchor `ダウンロード` -> `(None, None, 0, 'target', 'target_fiscal_year_not_detected')`
- Rebuilt the v326 Windows Saitama RCA batch plan locally with v327 code and
  verified publication-lag packets now surface `fiscal_year_mismatch:*` rows
  before `candidate_budget_dropped` rows.

v332 verifier exposes the current demonstration gap:

- Discovery gold-set entries: `23`
- Outcome distribution: `accepted_target_pdf=6`, `needs_operator_review=6`,
  `no_target_candidate_found=1`, `publication_lag_latest_public=9`,
  `site_fetch_error=1`
- Demonstrated extractor sources: `embed`, `wordpress_download_manager`
- Not yet gold-demonstrated: `data_attribute`, `form_action`,
  `input_control`, `meta_refresh`, `onclick`, `select_option`

## Current Windows Backend Evidence

Commands and observations from `ssh win` for v332 setup/bootstrap:

- Uploaded `dist/eidp-windows-v332.zip` to
  `C:\Users\cyo20\eidp-windows-v332.zip`.
- Windows `Get-FileHash -Algorithm SHA256` ->
  `5AF664C961768B9003EBBB9191D3ED5EF2FFFDD76337B09CBA92F14EAF97C5A2`.
- Extracted to `C:\Users\cyo20\EIDP-v332-9fe773e`.
- `scripts\first_setup.bat` -> exit `0`; after-setup validator reported
  commit `9fe773e972f76043fd5d3d96431b18754ee05711`,
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
- Local evidence snapshot was pulled to `_temp/win-v332-evidence/`, including
  `bootstrap-pdfs-20260513-035633.log`, `bootstrap-pdfs-20260513-035633.json`,
  `diagnostics-20260513-041410.txt`, the RCA batch plan, and a copy of
  `eidp.sqlite3`. SQLite checks on that snapshot report `2418` schools,
  `51` school sites, `7` documents, `18` current 2026 DepartmentYearly rows,
  `2418` 2026 school status rows, `5` Excel-ready schools, and `2` pending
  review items.

## Previous Windows Bootstrap Evidence

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
3. Use the generated RCA batch plan to classify whether the current low
   strict-target result is due to upstream publication lag, crawler false
   negatives, or missing manual fallback/gold-set demonstrations.
4. Compare measured operator-reviewable coverage, manual workload, and Excel
   readiness against the shipping line; keep strict target-PDF acquisition as a
   diagnostic metric during the May publication-lag window.
5. Only after those numbers pass should the branch be treated as release-ready.

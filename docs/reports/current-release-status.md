# EIDP Current Release Status

Updated: 2026-05-12
Branch: `sprint8-handoff-finalize`
Current Mac-verifier-clean package: `dist/eidp-windows-v320.zip`
Package commit: `17413896efc7ed58e76a42841287d2de934d9f26`
Package SHA256: `1b5b3bfecdd581bcb48b792310acbe62a66162d99e043b9f77899c82616a7c41`

## Verdict

Status: **NOT COMPLETE**

The code and package gates are in a strong state, and v320 now has a current
Windows SSH backend smoke for setup plus a bounded Saitama official-index PDF
bootstrap. The product goal is still not proven complete: the current package
has not passed a browser UI operator click-through, and the measured strict
target-PDF auto-acquisition remains far below the 60-70% shipping line.

## Objective Checklist

| Requirement | Current evidence | Status |
| --- | --- | --- |
| 47 prefecture official indexes seed school public URLs | v320 verifier: `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`, `prefecture_seed_school_rows_total=2148`; Windows bounded Saitama run downloaded the current official artifact and added `51` `SchoolSite` rows from `58` extracted / `51` matched rows | Evidence present |
| Discover and download current target-FY PDFs in strict mode | v320 verifier clean; discovery gold-set `20` entries; expected predictions `20/20 exact`; Windows Saitama bounded run crawled `5` official-index sites and found candidates on all `5`, but downloaded `0` strict target-FY PDFs | Mechanically proven, yield failing |
| Exclude stale-year fallback from auto-success | Ship gate now uses operator-reviewable coverage, while strict auto-yield remains diagnostic; gold-set includes publication-lag cases | Partially proven |
| Extract with pdfplumber/PyMuPDF/Tesseract and write only confidence >= 0.70 rows | Unit/package gates cover OCR runtime presence and confidence contracts; Windows Saitama bounded run had `0` downloaded PDFs, so ingest executed but processed `0` documents | Partially proven |
| Append-only DepartmentYearly / SupportRecipient writes | Fresh non-Windows audit: targeted Ruff clean and append-only/confidence/fiscal-year tests `116 passed`; source inspection confirmed demote-plus-new-revision paths in ingest, manual entry, and fiscal-year override | Evidence present, Win E2E still missing |
| Excel template output | Package verifier includes Excel/export contracts; current operator-PC preview/download flow is not revalidated on v320 | Partially proven |
| ManualActionLog audit for operator actions | Package verifier includes audit contracts and outbox checks; current operator-PC run not revalidated on v320 | Partially proven |
| ZIP distribution, double-click setup, browser UI offline operation | v320 ZIP verifies clean on macOS packaging gate, was transferred to Windows with matching SHA256, extracted to `C:\Users\cyo20\EIDP-v320-1741389`, and `scripts\first_setup.bat` completed successfully; browser UI click-through remains user-side/unverified | Backend Win proof present, UI proof missing |
| Shipping threshold: true target PDF 60-70% auto-acquired, operator manual work <=30% | Windows after-bootstrap diagnostics report `target_pdf_auto_yield_pct=0.0`, `operator_reviewable_yield_pct=0.2`, `ship_gate_status=below_gate`, `validate_after_bootstrap_ship_gate_rc=1`, and `ship_readiness_rc=1` | Failing |

## Current Non-Windows Evidence

Commands run for v320:

- `uv run pytest tests/unit -q` -> `1317 passed, 5 warnings`
- `uv run eidp eval-discovery-gold --predictions data/discovery-gold-set/expected-predictions.jsonl --fail-on-regression --json` -> `20/20 exact`
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v320.zip` -> `OK core`
- `zipinfo -1 dist/eidp-windows-v320.zip | rg "docs/runbooks/eidp-(windows|operator-e2e-template)\.md"` -> both runbook files present
- `uv run pytest tests/unit/test_windows_packaging_spike.py tests/unit/test_windows_distribution_verifier.py -q` -> `143 passed`
- `uv run eidp report ship-readiness --json --fail-on-missing-goal` -> exit `2` with `database_not_ready` on the uninitialized local DB
- `uv run eidp discovery-gold-set --json` -> `pattern_source_counts={"wordpress_download_manager": 1}`
- `uv run eidp discovery-gold-set --json --fail-on-undemonstrated-pattern-sources` -> non-zero with the same `undemonstrated_pattern_sources` payload
- `uv run ruff check tests/unit/test_current_read_paths.py tests/unit/test_fiscal_year_override.py` -> `All checks passed`
- `uv run pytest tests/unit/test_ingest_confidence_gating.py tests/unit/test_manual_entry_contract.py tests/unit/test_fiscal_year_override.py tests/unit/test_extraction_confidence.py tests/unit/test_current_read_paths.py -q` -> `116 passed`

v320 verifier exposes the current demonstration gap:

- Demonstrated extractor source: `wordpress_download_manager`
- Not yet gold-demonstrated: `data_attribute`, `embed`, `form_action`,
  `input_control`, `meta_refresh`, `onclick`, `select_option`

## Current Windows Backend Evidence

Commands and observations from `ssh win` for v320:

- Uploaded `dist/eidp-windows-v320.zip` to `C:\Users\cyo20\eidp-windows-v320.zip`.
- Windows `Get-FileHash -Algorithm SHA256` -> `1B5B3BFECDD581BCB48B792310ACBE62A66162D99E043B9F77899C82616A7C41`.
- Extracted to `C:\Users\cyo20\EIDP-v320-1741389`; `runtime\python\python.exe scripts\validate_windows_install.py .` -> `OK install`.
- `scripts\first_setup.bat` -> exit `0`; after-setup validator reported:
  `school_count=2418`, `school_fiscal_year_status_count=2418`,
  `sqlite_integrity_check=ok`, required SQLite tables present,
  `department_change` void columns present, and `uq_document_file_hash` present.
- `eidp db-info` after setup:
  `Schools=2418`, `Departments=9719`, `DepartmentYearly=40731`,
  `SchoolYearStatus=17696`, `SupportRecipient=10022`,
  `SchoolSite=0`, `Document=0`.
- `scripts\bootstrap_pdfs.bat --pref saitama --skip-known-url-discovery --url-search off --school-url-crawl off --batch-size 5 --rate-limit 0.2 --request-timeout 15` -> exit `0`.
- Bounded Saitama bootstrap results:
  official artifact `saitama.pdf` downloaded, aggregate `extracted=58`,
  `matched=51`, `added=51`, `review_items=2`; PDF discovery `crawled=5`,
  `found=5`, `downloaded=0`, `failed=0`, `skipped=344`,
  `prefiltered=314`, `candidate_budget_dropped=1725`; ingest `processed=0`.
- Generated RCA queue:
  `data\output\target-year-discovery\bootstrap-20260512_214530-discovery-rca-batch-plan.json`,
  `5` items / `5` total candidates, valid JSON by Python `json.tool`.
- Diagnostics after bootstrap:
  `validate_core_rc=0`, `validate_after_setup_rc=0`,
  `validate_after_bootstrap_rc=0`,
  `validate_after_bootstrap_ship_gate_rc=1`, `ship_readiness_rc=1`.
- The Windows scheduled task `EIDP Weekly Run` was updated by setup to
  `C:\Users\cyo20\EIDP-v320-1741389\scripts\weekly_run.bat`
  (previous observed target was `EIDP-v245-e7c6c9c`).

## Next Required Proof

1. Run browser UI operator click-through on the current v320 Windows install:
   `EIDP-start.bat` -> operator pages -> Excel preview/download -> diagnostics.
2. Expand Windows official-index discovery beyond the 5-site Saitama bounded
   smoke and record target PDFs accepted, publication-lag queue,
   manual-required queue, and errors.
3. Use the generated RCA batch plan to classify whether the current zero
   strict-target result is due to upstream publication lag, crawler false
   negatives, or missing manual fallback/gold-set demonstrations.
4. Compare the measured auto-acquisition and manual workload against the
   60-70% / <=30% shipping line.
5. Only after those numbers pass should the branch be treated as release-ready.

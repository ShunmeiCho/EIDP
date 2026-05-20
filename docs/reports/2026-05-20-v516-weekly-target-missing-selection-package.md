# v516 Weekly Target-Missing Selection Package

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
Package: `dist/eidp-windows-v516.zip`
Package source commit: `3b31eed865e57b0668345899f0de40001452b191`
Package SHA256: `ddb173208453b4ae6f071752d0b9e0191e18fb8770a68e2789ac5e4308847c22`

## Summary

v516 is a Mac-side package rebuild after fixing the weekly target-missing
selection query. The v515 RCA still showed 東京モード学園 and HAL東京 as
`no_pdf_candidates`, but the sandbox database already had current-FY target
documents and Excel-ready fiscal-year status rows for both schools:

| School ID | School | Document status | FY status |
| ---: | --- | --- | --- |
| 4 | 東京モード学園 | `fiscal_year=2026`, `pdf_type=target`, `ingest_status=review_pending` | `confirmed_target`, `parsed`, `excel_ready=1` |
| 7 | HAL東京 | `fiscal_year=2026`, `pdf_type=target`, `ingest_status=review_pending` | `confirmed_target`, `parsed`, `excel_ready=1` |

The weekly selection query only excluded current-FY target documents with
`ingest_status="ingested"`. That did not match
`SchoolFiscalYearStatus._pdf_status()`, which treats current-FY target PDFs in
`review_pending`, `parse_failed`, and `support_only` states as confirmed target
PDFs because the target PDF has already been found and should surface through
operator review/extraction status instead of re-entering acquisition.

v516 moves the confirmed-target ingest-status sets into shared constants in
`eidp.pipeline.school_fiscal_year_status` and reuses those constants in
`scripts/run_weekly_target_year_discovery.py`.

This is a denominator and queue-quality fix. It prevents already confirmed
schools from consuming target-missing crawl slots and from showing as RCA
`no_pdf_candidates`. It does not claim new FY2026/R8 strict target-PDF
availability.

## Sandbox Selection Evidence

Against the v515 canary sandbox database at
`_temp/v515-mac-limit50-sanko-child/data/eidp.sqlite3`, the updated selector
returns a limit-50 queue that excludes school IDs 4 and 7:

```json
{
  "count": 50,
  "selected_ids": [
    1, 2, 3, 5, 8, 11, 12, 13, 14, 15,
    16, 17, 18, 19, 20, 21, 22, 23, 24, 25,
    26, 27, 28, 29, 30, 31, 32, 33, 34, 35,
    36, 37, 38, 39, 40, 41, 42, 43, 44, 45,
    46, 47, 48, 49, 50, 51, 52, 53, 54, 55
  ],
  "contains_4": false,
  "contains_7": false
}
```

This replaces the v515 selected queue, where school IDs 4 and 7 appeared in
the RCA batch as `no_pdf_candidates` only because duplicate-hash evidence
pointed at already existing current-FY target documents.

## Verification

| Check | Result |
| --- | --- |
| Red test before fix | `test_select_target_missing_school_ids_excludes_review_pending_current_target_docs` failed with selected IDs `[1, 2, 3]` instead of `[2, 3]` |
| Weekly runner unit suite | `uv run pytest tests/unit/test_run_weekly_target_year_discovery.py -q` -> `32 passed` |
| Focused weekly + status tests | `uv run pytest tests/unit/test_run_weekly_target_year_discovery.py tests/unit/test_ingest_confidence_gating.py -q` -> `63 passed` |
| Mypy | `uv run mypy scripts/run_weekly_target_year_discovery.py src/eidp/pipeline/school_fiscal_year_status.py` -> pass |
| Ruff | `uv run ruff check scripts/run_weekly_target_year_discovery.py src/eidp/pipeline/school_fiscal_year_status.py tests/unit/test_run_weekly_target_year_discovery.py` -> pass |
| Whitespace check | `git diff --check` -> pass |
| Build | `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v516.zip --latest-alias` -> wrote v516 ZIP and refreshed latest alias |
| Core + OCR add-on verifier | `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v516.zip --ocr-addon dist/eidp-ocr-addon-windows-v497-smoke.zip --json` -> core `ok=true`, OCR add-on `ok=true` |
| Non-Windows release gate | `logs/win-v516-stage6-v516-non-windows-release-gates-20260520.json` -> `ok=true`, package/source fresh, full unit `1892 passed` |
| Post-docs-only release gate | `logs/win-v516-stage6-v516-post-docs-only-gates-20260520.json` -> `ok=true`, `docs_only_stale=true`, full unit `1892 passed` |

## Release Boundary

v516 is the latest package/source candidate. It has not completed Windows
side-by-side validation because the Windows OpenSSH/IP blocker remains
unresolved.

v502 remains the latest partial Windows side-by-side setup/canary package, and
v501 remains the latest complete Windows side-by-side smoke package.

v1.0 remains blocked until the FY2026/R8 strict-yield issue is resolved or the
`publication_lag` exception is explicitly approved, and until owner real-cycle
sign-off is returned.

# v506 Operator URL Audit Package

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
Package: `dist/eidp-windows-v506.zip`
Package source commit: `2d266c5f39399e71d19f12b2d99aa87f5e1333e8`
Package SHA256: `f2221af5d82352085bbf470335d3c726eb9b31ce133d876ec6e4e5c74df8927e`

## Summary

v506 is a Mac-side package rebuild after extending the operator audit surface:
manual URL registration now records accepted `登録 + 検証` writes in
`ManualActionLog` as `operator_url_submitted`, and CSV bulk URL import records
accepted `CSVを一括登録` writes as `operator_url_bulk_imported`.

The single-URL audit row targets `school_site` and records the school, URL,
classifier, validation result, file size, SHA256, and whether the row was newly
created. The CSV audit row targets `school_site` at batch scope and records
inserted, updated, skipped, and error counts with a bounded error sample.

This closes another operator-visible write path without changing strict
FY2026/R8 target-PDF discovery rules. It does not resolve the current release
blocker.

## Verification

| Check | Result |
| --- | --- |
| Red test before implementation | `uv run pytest tests/unit/test_operator_pages.py::test_submit_operator_url_inserts_verified_school_site tests/unit/test_operator_pages.py::test_import_operator_url_csv_inserts_reusable_manual_urls -q` -> failed with missing `ManualActionLog` rows |
| Operator URL audit tests | same focused command after implementation -> `2 passed` |
| Operator pages focused suite | `uv run pytest tests/unit/test_operator_pages.py -q` -> `27 passed` |
| Ruff | `uv run ruff check src/eidp/review/operator_pages.py tests/unit/test_operator_pages.py` -> pass |
| Mypy | `uv run mypy src/eidp/review/operator_pages.py` -> pass |
| Whitespace check | `git diff --check` -> pass |
| Build | `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v506.zip --latest-alias` -> wrote v506 ZIP and refreshed latest alias |
| Non-Windows release gate | `logs/win-v506-stage6-v506-non-windows-release-gates-20260520.json` -> `ok=true`, package/source fresh, full unit `1886 passed` |
| Core + OCR add-on verifier | `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v506.zip --ocr-addon dist/eidp-ocr-addon-windows-v497-smoke.zip --json` -> core `ok=true`, OCR add-on `ok=true` |

## Release Boundary

v506 is the latest package/source candidate. It has not completed Windows
side-by-side validation because the Windows OpenSSH/IP blocker is still
unresolved.

v502 remains the latest partial Windows side-by-side setup/canary package, and
v501 remains the latest complete Windows side-by-side smoke package.

v1.0 remains blocked until the FY2026/R8 strict-yield issue is resolved or the
`publication_lag` exception is explicitly approved, and until owner real-cycle
sign-off is returned.

# v508 Excel Export Audit Package

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
Package: `dist/eidp-windows-v508.zip`
Package source commit: `c9516555938c5a871d6faeb82648abffaaab4c30`
Package SHA256: `1704c690a3deeb1240e012a4918941a1b7aa959a36963320f385c5ecdfa47f93`

## Summary

v508 is a Mac-side package rebuild after extending the operator audit surface:
administrator-triggered Excel exports now record `ManualActionLog` rows when
operators click `マスターExcelを生成` or `競合校Excelを生成` on the detailed export
page.

The audit action type is `excel_export_generated`, targeting `excel_export`.
The payload records export kind, output path, target fiscal year, and the export
result summary returned by the workbook generator.

This closes another operator-visible Excel write path without changing strict
FY2026/R8 target-PDF discovery rules. It does not resolve the current release
blocker.

## Verification

| Check | Result |
| --- | --- |
| Red tests before implementation | `uv run pytest tests/unit/test_operator_pages.py::test_audit_excel_export_generated_writes_manual_action_log tests/unit/test_operator_pages.py::test_page_exports_records_generated_workbooks_in_manual_action_log -q` -> failed because helper/calls were missing |
| Excel export audit tests | same focused command after implementation -> `2 passed` |
| Operator pages focused suite | `uv run pytest tests/unit/test_operator_pages.py -q` -> `29 passed` |
| Ruff | `uv run ruff check src/eidp/review/operator_pages.py tests/unit/test_operator_pages.py` -> pass |
| Mypy | `uv run mypy src/eidp/review/operator_pages.py` -> pass |
| Whitespace check | `git diff --check` -> pass |
| Build | `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v508.zip --latest-alias` -> wrote v508 ZIP and refreshed latest alias |
| Non-Windows release gate | `logs/win-v508-stage6-v508-non-windows-release-gates-20260520.json` -> `ok=true`, package/source fresh, full unit `1888 passed` |
| Core + OCR add-on verifier | `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v508.zip --ocr-addon dist/eidp-ocr-addon-windows-v497-smoke.zip --json` -> core `ok=true`, OCR add-on `ok=true` |

## Release Boundary

v508 is the latest package/source candidate. It has not completed Windows
side-by-side validation because the Windows OpenSSH/IP blocker is still
unresolved.

v502 remains the latest partial Windows side-by-side setup/canary package, and
v501 remains the latest complete Windows side-by-side smoke package.

v1.0 remains blocked until the FY2026/R8 strict-yield issue is resolved or the
`publication_lag` exception is explicitly approved, and until owner real-cycle
sign-off is returned.

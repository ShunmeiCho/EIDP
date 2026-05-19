# v504 Excel Preview Audit Package

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
Package: `dist/eidp-windows-v504.zip`
Package source commit: `7ad57cc39b433164bcb8d92facf07184ef7331d6`
Package SHA256: `9329630e7026c3e568bf78643f4a0e6e0941d4d695030dfdb362e1dc2f20439f`

## Summary

v504 is a Mac-side package rebuild after extending the operator audit surface:
the Excel preview page now records successful `プレビュー workbook を生成`
actions in `ManualActionLog` as `excel_preview_generated`.

The audit payload records the target-year export gap counters, generated sheet
row counts, and quality-warning counts. The workbook generation path now
acquires the shared `ui_excel_preview` lock before generating the workbook and
writing the audit row.

This does not change strict FY2026/R8 target-PDF discovery rules, and it does
not resolve the current release blocker.

## Verification

| Check | Result |
| --- | --- |
| Excel preview audit tests | `uv run pytest tests/unit/test_review_excel_preview.py::test_audit_excel_preview_generated_writes_manual_action_log tests/unit/test_review_excel_preview.py::test_render_records_excel_preview_generation_in_manual_action_log_contract -q` -> `2 passed` |
| Excel preview/export focused suite | `uv run pytest tests/unit/test_review_excel_preview.py tests/unit/test_excel_exporter.py -q` -> `31 passed` |
| Ruff | `uv run ruff check src/eidp/review/_pages/excel_preview.py tests/unit/test_review_excel_preview.py` -> pass |
| Mypy | `uv run mypy src/eidp/review/_pages/excel_preview.py` -> pass |
| Build | `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v504.zip --latest-alias` -> wrote v504 ZIP and refreshed latest alias |
| Non-Windows release gate | `logs/win-v504-stage6-v504-non-windows-release-gates-20260520.json` -> `ok=true`, package/source fresh, full unit `1884 passed` |
| Core + OCR add-on verifier | `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v504.zip --ocr-addon dist/eidp-ocr-addon-windows-v497-smoke.zip --json` -> core `ok=true`, OCR add-on `ok=true` |

## Release Boundary

v504 is the latest package/source candidate. It has not completed Windows
side-by-side validation because the Windows OpenSSH/IP blocker is still
unresolved.

v502 remains the latest partial Windows side-by-side setup/canary package, and
v501 remains the latest complete Windows side-by-side smoke package.

v1.0 remains blocked until the FY2026/R8 strict-yield issue is resolved or the
`publication_lag` exception is explicitly approved, and until owner real-cycle
sign-off is returned.

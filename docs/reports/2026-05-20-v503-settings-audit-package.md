# v503 Settings Audit Package

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
Package: `dist/eidp-windows-v503.zip`
Package source commit: `990060129da1a118835a4a2ab64ef8c081f4c336`
Package SHA256: `66a118d2ab16d2f314c25e00c7e0acbead288f0755e67a7f8ae24b3e93b8c52c`

## Summary

v503 is a Mac-side package rebuild after tightening the operator audit surface:
the settings page now records successful `設定を保存` writes in
`ManualActionLog` as `operator_settings_saved`.

The audit payload records the target fiscal year, non-secret runtime settings,
and school-year task rebuild counts when the target year changes. API-key
values are not persisted in the audit JSON; set secret fields are recorded as
`[set]`.

This does not change the FY2026/R8 strict PDF discovery rules, and it does not
resolve the current release blocker.

## Verification

| Check | Result |
| --- | --- |
| Settings audit redaction test | `uv run pytest tests/unit/test_settings_page.py::test_audit_operator_settings_saved_redacts_secret_values tests/unit/test_settings_page.py::test_render_records_settings_save_in_manual_action_log_contract -q` -> `2 passed` |
| Settings/verifier focused suite | `uv run pytest tests/unit/test_settings_page.py tests/unit/test_windows_distribution_verifier.py::test_verify_core_zip_requires_settings_page_module tests/unit/test_windows_distribution_verifier.py::test_verify_core_zip_requires_settings_page_target_year_bounds tests/unit/test_windows_distribution_verifier.py::test_verify_core_zip_requires_operator_action_audit_contracts -q` -> `14 passed` |
| Ruff | `uv run ruff check src/eidp/review/_pages/settings_page.py tests/unit/test_settings_page.py` -> pass |
| Mypy | `uv run mypy src/eidp/review/_pages/settings_page.py` -> pass |
| Build | `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v503.zip --latest-alias` -> wrote v503 ZIP and refreshed latest alias |
| Non-Windows release gate | `logs/win-v503-stage6-v503-non-windows-release-gates-20260520.json` -> `ok=true`, package/source fresh, full unit `1882 passed` |
| Core + OCR add-on verifier | `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v503.zip --ocr-addon dist/eidp-ocr-addon-windows-v497-smoke.zip --json` -> core `ok=true`, OCR add-on `ok=true` |

## Release Boundary

v503 is the latest package/source candidate. It has not completed Windows
side-by-side validation because the Windows OpenSSH/IP blocker is still
unresolved.

v501 remains the latest complete Windows side-by-side smoke package, and v502
remains the latest partial Windows side-by-side setup/canary package.

v1.0 remains blocked until the FY2026/R8 strict-yield issue is resolved or the
`publication_lag` exception is explicitly approved, and until owner real-cycle
sign-off is returned.

# v505 School Task Rebuild Audit Package

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
Package: `dist/eidp-windows-v505.zip`
Package source commit: `22c3f7aa5fb986cb516541ad49e54c4b29644d78`
Package SHA256: `6b588d6300b6793f3d63ea625563bf6fcda6c1246aaf17f9cf1b715ec03f102a`

## Summary

v505 is a Mac-side package rebuild after extending the operator audit surface:
the school-year task board now records successful `年度タスクを再計算` actions in
`ManualActionLog` as `school_year_tasks_rebuilt`.

The audit payload records the fiscal year, school type, rebuilt row count, and
Excel-ready row count returned by the rebuild job. This closes another
operator-visible write path without changing strict FY2026/R8 target-PDF
discovery rules.

This does not resolve the current release blocker.

## Verification

| Check | Result |
| --- | --- |
| School task rebuild audit tests | `uv run pytest tests/unit/test_review_school_year_tasks.py::test_audit_school_year_tasks_rebuilt_writes_manual_action_log tests/unit/test_review_school_year_tasks.py::test_rebuild_button_records_manual_action_log_contract -q` -> `2 passed` |
| School task page focused suite | `uv run pytest tests/unit/test_review_school_year_tasks.py -q` -> `65 passed` |
| Ruff | `uv run ruff check src/eidp/review/_pages/school_year_tasks.py tests/unit/test_review_school_year_tasks.py` -> pass |
| Mypy | `uv run mypy src/eidp/review/_pages/school_year_tasks.py` -> pass |
| Whitespace check | `git diff --check` -> pass |
| Build | `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v505.zip --latest-alias` -> wrote v505 ZIP and refreshed latest alias |
| Non-Windows release gate | `logs/win-v505-stage6-v505-non-windows-release-gates-20260520.json` -> `ok=true`, package/source fresh, full unit `1886 passed` |
| Core + OCR add-on verifier | `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v505.zip --ocr-addon dist/eidp-ocr-addon-windows-v497-smoke.zip --json` -> core `ok=true`, OCR add-on `ok=true` |

## Release Boundary

v505 is the latest package/source candidate. It has not completed Windows
side-by-side validation because the Windows OpenSSH/IP blocker is still
unresolved.

v502 remains the latest partial Windows side-by-side setup/canary package, and
v501 remains the latest complete Windows side-by-side smoke package.

v1.0 remains blocked until the FY2026/R8 strict-yield issue is resolved or the
`publication_lag` exception is explicitly approved, and until owner real-cycle
sign-off is returned.

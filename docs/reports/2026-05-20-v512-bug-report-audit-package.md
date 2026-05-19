# v512 Bug Report Audit Package

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
Package: `dist/eidp-windows-v512.zip`
Package source commit: `51a3c771dd2c15e831d9f1e2b96119d11b9eadbd`
Package SHA256: `6548e79d51378281c20cbe97bd1a652453f8b207efa391db1f3e40ccd8744d34`

## Summary

v512 is a Mac-side package rebuild after extending the operator audit surface
to local bug-report ZIP generation. When the Streamlit bug-report page receives
a DB session and the operator clicks `ローカルレポートZIPを作成`, the page now
records a `ManualActionLog` row with `action_type=bug_report_generated` and
`target_table=bug_report`.

The audit payload stores the archive name/path, detected signal count, and
whether an operator note was present. It intentionally does not store the raw
operator note text because support notes can include tracebacks, local paths,
or other sensitive context.

This does not change strict FY2026/R8 target-PDF discovery rules, extraction
confidence gates, Excel generation, or Windows setup behavior.

## Verification

| Check | Result |
| --- | --- |
| Red test before implementation | `uv run pytest tests/unit/test_review_bug_report.py::test_bug_report_page_builds_downloadable_zip_when_clicked -q` -> failed because ZIP generation did not insert `ManualActionLog` |
| Bug-report audit focused test | same focused command after implementation -> `1 passed` |
| Red audit vocabulary test | `uv run pytest tests/unit/test_review_audit_log.py::test_action_types_and_target_tables_are_pinned -q` -> failed until `bug_report_generated` and `bug_report` were exposed |
| Bug-report + audit-log suites | `uv run pytest tests/unit/test_review_bug_report.py tests/unit/test_review_audit_log.py -q` -> `16 passed` |
| Ruff | `uv run ruff check src/eidp/review/_pages/bug_report.py src/eidp/review/_pages/audit_log.py tests/unit/test_review_bug_report.py tests/unit/test_review_audit_log.py` -> pass |
| Mypy | `uv run mypy src/eidp/review/_pages/bug_report.py src/eidp/review/_pages/audit_log.py` -> pass |
| Static audit vocabulary coverage probe | `missing_actions=[]`, `missing_target_tables=[]`; known dynamic sites remain covered by existing constants and tests |
| Whitespace check | `git diff --check` -> pass |
| Build | `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v512.zip --latest-alias` -> wrote v512 ZIP and refreshed latest alias |
| Non-Windows release gate | `logs/win-v512-stage6-v512-non-windows-release-gates-20260520.json` -> `ok=true`, package/source fresh, full unit `1889 passed` |
| Core + OCR add-on verifier | `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v512.zip --ocr-addon dist/eidp-ocr-addon-windows-v497-smoke.zip --json` -> core `ok=true`, OCR add-on `ok=true` |

## Release Boundary

v512 is the latest package/source candidate. It has not completed Windows
side-by-side validation because the Windows OpenSSH/IP blocker is still
unresolved.

v502 remains the latest partial Windows side-by-side setup/canary package, and
v501 remains the latest complete Windows side-by-side smoke package.

v1.0 remains blocked until the FY2026/R8 strict-yield issue is resolved or the
`publication_lag` exception is explicitly approved, and until owner real-cycle
sign-off is returned.

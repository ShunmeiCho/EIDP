# v509 Audit Log Filter Package

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
Package: `dist/eidp-windows-v509.zip`
Package source commit: `0f6ee0f26d008682992fea8dffb617d443dd12f7`
Package SHA256: `a43d0f7e91cdcacbd8ce40b949290582990f0c1dae677c885ba38dd4c61ee701`

## Summary

v509 is a Mac-side package rebuild after extending the operator audit-log UI
filters. The `監査ログ` page now exposes the current `ManualActionLog`
`action_type` and `target_table` vocabulary in its dropdowns, including recent
settings, URL, prefecture remark, school code, Excel preview/export, and
school-year task audit rows.

This improves operator reviewability of the audit trail. It does not change
strict FY2026/R8 target-PDF discovery rules, extraction confidence gates, Excel
generation, or Windows setup behavior.

## Verification

| Check | Result |
| --- | --- |
| Red test before implementation | `uv run pytest tests/unit/test_review_audit_log.py::test_action_types_and_target_tables_are_pinned -q` -> failed because the audit-log dropdown vocabulary was missing current action types and target tables |
| Focused vocabulary test | same focused command after implementation -> `1 passed` |
| Audit-log focused suite | `uv run pytest tests/unit/test_review_audit_log.py -q` -> `12 passed` |
| Ruff | `uv run ruff check src/eidp/review/_pages/audit_log.py tests/unit/test_review_audit_log.py` -> pass |
| Mypy | `uv run mypy src/eidp/review/_pages/audit_log.py` -> pass |
| Static audit vocabulary coverage probe | `missing_actions=[]`, `missing_target_tables=[]`; the dynamic `prefecture_remark_{resolution}` site is covered by `prefecture_remark_approved` and `prefecture_remark_rejected` |
| Whitespace check | `git diff --check` -> pass |
| Build | `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v509.zip --latest-alias` -> wrote v509 ZIP and refreshed latest alias |
| Non-Windows release gate | `logs/win-v509-stage6-v509-non-windows-release-gates-20260520.json` -> `ok=true`, package/source fresh, full unit `1888 passed` |
| Core + OCR add-on verifier | `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v509.zip --ocr-addon dist/eidp-ocr-addon-windows-v497-smoke.zip --json` -> core `ok=true`, OCR add-on `ok=true` |

## Release Boundary

v509 is the latest package/source candidate. It has not completed Windows
side-by-side validation because the Windows OpenSSH/IP blocker is still
unresolved.

v502 remains the latest partial Windows side-by-side setup/canary package, and
v501 remains the latest complete Windows side-by-side smoke package.

v1.0 remains blocked until the FY2026/R8 strict-yield issue is resolved or the
`publication_lag` exception is explicitly approved, and until owner real-cycle
sign-off is returned.

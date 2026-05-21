# v510 School Alias Audit Package

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
Package: `dist/eidp-windows-v510.zip`
Package source commit: `110bef2c24f2ef8722172ca2ddf27f81ae3a9813`
Package SHA256: `50567f74722ff85fd04c0a73d562b6d0110322685c864bfa627e7ed41f076e4a`

## Summary

v510 is a Mac-side package rebuild after closing an operator audit gap in the
matching proposal review flow. When an operator approves a school alias
proposal, the `SchoolAlias` insert now records a `ManualActionLog` row with
`action_type=school_alias_approved` and `target_table=school_alias`.

The audit payload records the school id, alias name, alias type, and proposal
source. The Streamlit UI passes the current operator actor into the audit row.
The audit-log filter vocabulary also includes the new action type and target
table.

This does not change strict FY2026/R8 target-PDF discovery rules, extraction
confidence gates, Excel generation, or Windows setup behavior.

## Verification

| Check | Result |
| --- | --- |
| Red test before implementation | `uv run pytest tests/unit/test_operator_proposals.py::test_apply_school_alias_inserts_when_absent -q` -> failed because no `ManualActionLog` row existed for school alias approval |
| School alias audit focused test | same focused command after implementation -> `1 passed` |
| Red audit vocabulary test | `uv run pytest tests/unit/test_review_audit_log.py::test_action_types_and_target_tables_are_pinned -q` -> failed until `school_alias_approved` and `school_alias` were exposed |
| Proposal + audit-log suites | `uv run pytest tests/unit/test_operator_proposals.py tests/unit/test_review_audit_log.py -q` -> `33 passed` |
| Ruff | `uv run ruff check src/eidp/review/operator_pages.py src/eidp/review/_pages/audit_log.py tests/unit/test_operator_proposals.py tests/unit/test_review_audit_log.py` -> pass |
| Mypy | `uv run mypy src/eidp/review/operator_pages.py src/eidp/review/_pages/audit_log.py` -> pass |
| Static audit vocabulary coverage probe | `missing_actions=[]`, `missing_target_tables=[]`; the dynamic `prefecture_remark_{resolution}` site is covered by `prefecture_remark_approved` and `prefecture_remark_rejected` |
| Whitespace check | `git diff --check` -> pass |
| Build | `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v510.zip --latest-alias` -> wrote v510 ZIP and refreshed latest alias |
| Non-Windows release gate | `logs/win-v510-stage6-v510-non-windows-release-gates-20260520.json` -> `ok=true`, package/source fresh, full unit `1888 passed` |
| Core + OCR add-on verifier | `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v510.zip --ocr-addon dist/eidp-ocr-addon-windows-v497-smoke.zip --json` -> core `ok=true`, OCR add-on `ok=true` |

## Release Boundary

v510 is the latest package/source candidate. It has not completed Windows
side-by-side validation because the Windows OpenSSH/IP blocker is still
unresolved.

v502 remains the latest partial Windows side-by-side setup/canary package, and
v501 remains the latest complete Windows side-by-side smoke package.

v1.0 remains blocked until the FY2026/R8 strict-yield issue is resolved or the
`publication_lag` exception is explicitly approved, and until owner real-cycle
sign-off is returned.

# v511 Proposal Decision Audit Package

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
Package: `dist/eidp-windows-v511.zip`
Package source commit: `057bcb53ece789d7e766091e87c86f41b117aea8`
Package SHA256: `fbe868839d19249383445105b5d0caab0e2303e38116df4a2b448c92cf0276ea`

## Summary

v511 is a Mac-side package rebuild after extending the matching proposal review
audit surface. Proposal review decisions still write to
`output/proposal_decisions.jsonl`, and now the same UI decision also records a
`ManualActionLog` row with `action_type=proposal_decision_recorded` and
`target_table=proposal_decision` whenever the Streamlit page provides a DB
session.

This captures operator decisions such as school alias approval, existing-row
acknowledgement, and deferral in the DB audit stream, not only in the sidecar
JSONL file. The audit payload stores the proposal kind, template name, decision,
target id, operator name, note, and timestamp.

This does not change strict FY2026/R8 target-PDF discovery rules, extraction
confidence gates, Excel generation, or Windows setup behavior.

## Verification

| Check | Result |
| --- | --- |
| Red test before implementation | `uv run pytest tests/unit/test_operator_proposals.py::test_record_decision_can_write_manual_action_log -q` -> failed because `_record_decision` did not accept `session` or write `ManualActionLog` |
| Proposal decision audit focused test | same focused command after implementation -> `1 passed` |
| Red audit vocabulary test | `uv run pytest tests/unit/test_review_audit_log.py::test_action_types_and_target_tables_are_pinned -q` -> failed until `proposal_decision_recorded` and `proposal_decision` were exposed |
| Proposal + audit-log suites | `uv run pytest tests/unit/test_operator_proposals.py tests/unit/test_review_audit_log.py -q` -> `34 passed` |
| Ruff | `uv run ruff check src/eidp/review/operator_pages.py src/eidp/review/_pages/audit_log.py tests/unit/test_operator_proposals.py tests/unit/test_review_audit_log.py` -> pass |
| Mypy | `uv run mypy src/eidp/review/operator_pages.py src/eidp/review/_pages/audit_log.py` -> pass |
| Static audit vocabulary coverage probe | `missing_actions=[]`, `missing_target_tables=[]`; the dynamic `prefecture_remark_{resolution}` site is covered by `prefecture_remark_approved` and `prefecture_remark_rejected` |
| Whitespace check | `git diff --check` -> pass |
| Build | `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v511.zip --latest-alias` -> wrote v511 ZIP and refreshed latest alias |
| Non-Windows release gate | `logs/win-v511-stage6-v511-non-windows-release-gates-20260520.json` -> `ok=true`, package/source fresh, full unit `1889 passed` |
| Core + OCR add-on verifier | `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v511.zip --ocr-addon dist/eidp-ocr-addon-windows-v497-smoke.zip --json` -> core `ok=true`, OCR add-on `ok=true` |

## Release Boundary

v511 is the latest package/source candidate. It has not completed Windows
side-by-side validation because the Windows OpenSSH/IP blocker is still
unresolved.

v502 remains the latest partial Windows side-by-side setup/canary package, and
v501 remains the latest complete Windows side-by-side smoke package.

v1.0 remains blocked until the FY2026/R8 strict-yield issue is resolved or the
`publication_lag` exception is explicitly approved, and until owner real-cycle
sign-off is returned.

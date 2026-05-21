# v507 Prefecture Remark Audit Package

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
Package: `dist/eidp-windows-v507.zip`
Package source commit: `0ddc6570c294667a3802f7f3b45a5f53a5d6e9b1`
Package SHA256: `e73ffe8112d0468e6d0e49654d8e287002e5a6dc20a1e0e023a240939a71d675`

## Summary

v507 is a Mac-side package rebuild after extending the operator audit surface:
official prefecture index remark decisions now record `ManualActionLog` rows
when operators click `確認済みにする` or `対象外として閉じる`.

The audit action type is `prefecture_remark_approved` or
`prefecture_remark_rejected`, targeting `review_item`. The payload records the
review item, school id, resolution, notes, parsed remark tags, remark text, and
evidence URL.

This closes another operator-visible write path without changing strict
FY2026/R8 target-PDF discovery rules. It does not resolve the current release
blocker.

## Verification

| Check | Result |
| --- | --- |
| Red test before implementation | `uv run pytest tests/unit/test_review_prefecture_remarks.py::test_resolve_prefecture_remark_review_closes_pending_item -q` -> failed with missing `ManualActionLog` row |
| Prefecture remark audit test | same focused command after implementation -> `1 passed` |
| Prefecture remark focused suite | `uv run pytest tests/unit/test_review_prefecture_remarks.py -q` -> `5 passed` |
| Ruff | `uv run ruff check src/eidp/review/_pages/prefecture_remarks.py tests/unit/test_review_prefecture_remarks.py` -> pass |
| Mypy | `uv run mypy src/eidp/review/_pages/prefecture_remarks.py` -> pass |
| Whitespace check | `git diff --check` -> pass |
| Build | `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v507.zip --latest-alias` -> wrote v507 ZIP and refreshed latest alias |
| Non-Windows release gate | `logs/win-v507-stage6-v507-non-windows-release-gates-20260520.json` -> `ok=true`, package/source fresh, full unit `1886 passed` |
| Core + OCR add-on verifier | `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v507.zip --ocr-addon dist/eidp-ocr-addon-windows-v497-smoke.zip --json` -> core `ok=true`, OCR add-on `ok=true` |

## Release Boundary

v507 is the latest package/source candidate. It has not completed Windows
side-by-side validation because the Windows OpenSSH/IP blocker is still
unresolved.

v502 remains the latest partial Windows side-by-side setup/canary package, and
v501 remains the latest complete Windows side-by-side smoke package.

v1.0 remains blocked until the FY2026/R8 strict-yield issue is resolved or the
`publication_lag` exception is explicitly approved, and until owner real-cycle
sign-off is returned.

# v524 Owner Return Verifier Hardening Package

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
Package: `dist/eidp-windows-v524.zip`
Package source commit: `7751e948a2f78d9c8126a55d26c78b455a61965b`
Package SHA256: `6647e32c5785cf147e7fce1e8e3c0091635ce10da80a64fc012ed9d671ad7a8a`

## Scope

v524 hardens the returned owner/operator evidence verifier. It closes part of
the v523 verifier coverage gap by requiring completed Excel and audit/outbox
proof rows in `eidp-operator-e2e-template.md`.

The new verifier rejects a return packet unless the owner/operator template
contains:

- `Excel ready 率` KPI row,
- always-pass `Excel 整合性` KPI row,
- nonblank `出力ファイル:` proof block,
- `監査ログページ表示`,
- numeric `manual_action_log 件数`,
- `JSONL outbox 未送信件数` proving after-flush count `0`,
- `audit-flush 実行` as `pass` or `not needed`, and
- `JSONL action_id 重複` as `none`.

This does not change discovery logic and does not improve FY2026/R8 strict
PDF acquisition yield.

## Verification

| Check | Result |
| --- | --- |
| Red test | `test_verify_stage6_return_rejects_missing_excel_and_audit_proof_rows` initially failed because the old verifier returned `ok=true` for missing Excel/audit proof |
| Focused verifier unit | `uv run pytest tests/unit/test_stage6_return_verifier.py -q` -> `14 passed` |
| Packaging contract slice | `uv run pytest tests/unit/test_windows_packaging_spike.py tests/unit/test_ci_workflow_contract.py -q` -> `100 passed` |
| Type check | `uv run mypy scripts/verify_stage6_return.py` -> pass |
| Ruff | `uv run ruff check scripts/verify_stage6_return.py scripts/verify_windows_distribution.py tests/unit/test_stage6_return_verifier.py` -> pass |
| Build | `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v524.zip --latest-alias` -> wrote v524 ZIP and refreshed latest alias |
| SHA256 sidecar | `shasum -a 256 -c dist/eidp-windows-v524.zip.sha256` -> `dist/eidp-windows-v524.zip: OK` |
| Core + OCR add-on verifier | `logs/win-v524-stage6-v524-verify-windows-distribution-with-ocr-addon-20260520.json` -> core `ok=true`, OCR add-on `ok=true` |
| Non-Windows release gate | `logs/win-v524-stage6-v524-non-windows-release-gates-20260520.json` -> `ok=true`, package/source fresh, full unit `1898 passed` |
| Real unapproved template rejection | `logs/win-v524-stage6-v524-verify-stage6-return-not-approved-exception-20260520.json` -> rc `1`, `ok=false`, and includes the new missing Excel/audit proof errors |

## Package Details

- `BUILD_INFO.git_commit`: `7751e948a2f78d9c8126a55d26c78b455a61965b`
- `BUILD_INFO.git_branch`: `sprint8-handoff-finalize`
- `BUILD_INFO.git_dirty`: `false`
- ZIP size: `212165312` bytes
- ZIP entries: `3106`
- wheelhouse entries accepted by verifier: `84`
- packaged prefecture seed rows: `47`
- packaged prefecture seed school rows: `2148`
- discovery gold entries: `45`
- discovery gold expected predictions: `45/45`

## Current Decision

v524 is the latest package/source-verified and Windows side-by-side validated
candidate for owner-return verifier hardening. The complete Windows smoke is
recorded in `docs/reports/2026-05-20-v524-full-windows-side-by-side-smoke.md`.

Do not treat v524 as v1.0 approval. The release still requires either strict
FY2026/R8 production-scale success or an approved `publication_lag` exception
plus owner real-cycle evidence verified by the hardened
`scripts/verify_stage6_return.py`.

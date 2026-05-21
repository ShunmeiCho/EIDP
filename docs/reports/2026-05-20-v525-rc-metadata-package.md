# v525 RC Metadata Package And Windows Smoke Evidence

Date: 2026-05-20
Package: `dist/eidp-windows-v525.zip`
Package SHA256: `5e0ed056e37c5b105b38de033062c4f7a7a8f0966509adb0251cade8f151efc4`
Source commit: `73392f7a246b4dcd7396524b87e2db48b25dec61`

## Scope

v525 rebuilds the Windows package after the project version was bumped to
`1.0.0rc1` and `CHANGELOG.md` was added. The rebuild is required because the
project wheel changed from `eidp-0.2.0-py3-none-any.whl` to
`eidp-1.0.0rc1-py3-none-any.whl`.

This is not v1.0 GA approval. FY2026/R8 strict yield and owner sign-off remain
blocked.

## Mac / Package Evidence

| Check | Evidence |
| --- | --- |
| Build | `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v525.zip --latest-alias` |
| SHA256 | `shasum -a 256 -c dist/eidp-windows-v525.zip.sha256` -> OK |
| Core + OCR verifier | `logs/win-v525-stage6-v525-verify-windows-distribution-with-ocr-addon-20260520.json` -> core `ok=true`, OCR add-on `ok=true` |
| Non-Windows release gate | `logs/win-v525-stage6-v525-non-windows-release-gates-20260520.json` -> `ok=true`, package/source fresh, full unit `1898 passed` |
| Package source check | package commit and source commit both `73392f7a246b4dcd7396524b87e2db48b25dec61`, `source_dirty=false`, `stale=false` |
| Installed metadata | `importlib.metadata.version("eidp")` -> `1.0.0rc1` |

## Windows Side-By-Side Evidence

Windows root: `C:\Users\cyo20\EIDP-v525-73392f7-env0`

| Check | Evidence |
| --- | --- |
| Setup summary | `logs/win-v525-stage6/win-v525-stage6-v525-setup-summary-20260520.json` -> `ok=true`, setup/validate/OCR/recovery rc all `0` |
| Setup validator | `logs/win-v525-stage6/win-v525-stage6-v525-env0-validate-after-setup-20260520.json` -> `ok=true`, `school_count=2418`, `school_fiscal_year_status_count=2418`, SQLite integrity `ok`, build commit `73392f7a246b4dcd7396524b87e2db48b25dec61` |
| OCR runtime | `logs/win-v525-stage6/win-v525-stage6-v525-env0-validate-ocr-runtime-20260520.json` -> `ok=true`, Tesseract `5.4.0.20240606`, `jpn` and `jpn_vert` present |
| UI smoke | `logs/win-v525-stage6/win-v525-stage6-v525-ui-smoke-20260520.json` -> `ok=true`, port `8525`, health `200/ok`, root `200`, no traceback, listener stopped |
| Weekly canary | `logs/win-v525-stage6/win-v525-stage6-v525-weekly-canary-limit50-summary-20260520.json` -> `ok=true`, weekly rc `0`, validate-after-weekly rc `0`, recovery rc `0` |
| Last run | `logs/win-v525-stage6/win-v525-stage6-v525-last-run-after-weekly-canary-limit50-20260520.json` -> `status=success`, `current_fy=2026`, strict `5/50 (10.0%)`, operator-reviewable `50/50 (100.0%)`, `ship_gate_status=below_gate` |
| Excel smoke | `logs/win-v525-stage6/win-v525-stage6-v525-excel-summary-20260520.json` -> `ok=true`, master workbook, competition workbook, and gap report generated |
| Stage 6 recovery | `logs/win-v525-stage6/stage6-recovery-20260520-v525.json` -> `ok=true`, active task matches expected v485 weekly action |
| Residual cleanup | `logs/win-v525-stage6/stage6-residual-cleanup-20260520-v525.json` -> dry run `ok=true`, `existing_count=0`, `moved_count=0` |
| Stage 6 bundle | `logs/win-v525-stage6/stage6-evidence-20260520-081227.zip`, SHA256 `6c6d48d3049360cd48990f5705c49b900e137ab3e791ac8d9071c7860617c982` |
| Stage 6 verifier | `logs/win-v525-stage6/stage6-evidence-verify-20260520-171227.json` -> `ok=true`, required labels present, no unsafe or forbidden entries |

## Release Boundary

v525 supersedes v524 as the latest package/source and complete Windows
side-by-side smoke package. It preserves the same business blocker:

- FY2026/R8 strict current-year target PDF yield remains `5/50 (10.0%)`,
  below the 60% release line.
- Owner real-cycle evidence and sign-off are still missing.
- `docs/reports/2026-05-19-publication-lag-release-exception-record.md` remains
  `NOT_APPROVED`.

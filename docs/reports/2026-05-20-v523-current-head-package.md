# v523 Current-Head Windows Package

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
Package: `dist/eidp-windows-v523.zip`
Package source commit: `9a5cefc74751ec849daff86d68ff552f79f376e0`
Package SHA256: `5d47ca9e016aa6aadf3608b5799c773a769af585d158813eada1f80cebe762ce`

## Scope

v523 is a Mac-side package rebuild from the current PR head after the v520,
v521, and v522 source-side discovery/RCA follow-ups. It includes:

- v520 Katayanagi exact URL boundary hardening,
- v521 same-school corporation-root suppression when exact school-domain
  overrides exist,
- v522 stale-labeled yearless RCA bucket classification, and
- v522 Windows connectivity and same-domain FY2026 negative-probe status docs.

This package rebuild removes the previous "source-side only" gap for v520-v522.
It does not create FY2026/R8 strict target-PDF success. Windows side-by-side
validation later completed and is recorded separately in
`docs/reports/2026-05-20-v523-full-windows-side-by-side-smoke.md`.

## Verification

| Check | Result |
| --- | --- |
| Build | `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v523.zip --latest-alias` -> wrote v523 ZIP and refreshed latest alias |
| SHA256 sidecar | `shasum -a 256 -c dist/eidp-windows-v523.zip.sha256` -> `dist/eidp-windows-v523.zip: OK` |
| Core + OCR add-on verifier | `logs/win-v523-stage6-v523-verify-windows-distribution-with-ocr-addon-20260520.json` -> core `ok=true`, OCR add-on `ok=true` |
| Non-Windows release gate | `logs/win-v523-stage6-v523-non-windows-release-gates-20260520.json` -> `ok=true`, package/source fresh, full unit `1897 passed` |
| Post-docs-only release gate | `logs/win-v523-stage6-v523-post-docs-only-gates-20260520.json` -> `ok=true`, `docs_only_stale=true`, full unit `1897 passed` |

## Package Details

- `BUILD_INFO.git_commit`: `9a5cefc74751ec849daff86d68ff552f79f376e0`
- `BUILD_INFO.git_branch`: `sprint8-handoff-finalize`
- `BUILD_INFO.git_dirty`: `false`
- ZIP size: `212163938` bytes
- ZIP entries: `3106`
- wheelhouse entries accepted by verifier: `84`
- packaged prefecture seed rows: `47`
- packaged prefecture seed school rows: `2148`
- discovery gold entries: `45`
- discovery gold expected predictions: `45/45`

## Current Decision

v523 is now the latest package/source candidate and latest complete Windows
side-by-side smoke package. Windows setup, OCR runtime proof, UI smoke, Excel
smoke, Stage 6 evidence bundling, and recovery are recorded in
`docs/reports/2026-05-20-v523-full-windows-side-by-side-smoke.md`. Owner
real-cycle sign-off remains missing.

Do not merge PR #2, tag v1.0, or request owner sign-off from v523 alone. The
release still requires either strict FY2026/R8 production-scale success or an
approved `publication_lag` exception plus owner real-cycle evidence verified by
`scripts/verify_stage6_return.py`.

# v518 Gold-Set Publication-Lag Package

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
Package: `dist/eidp-windows-v518.zip`
Package source commit: `5c9abe27a0b2f60effa4bb071f2796d4251754c9`
Package SHA256: `d5ea5a6d0aed71fc9d5e581aca336cbd04045de4bc66d1efd8ecb91ccac5723c`

## Scope

v518 is a Mac-side package rebuild after adding the Sanko Tokyo child-school
publication-lag case to the discovery gold set. The case was exposed by the
v517 targeted school ID 55 smoke: the exact school URL now crawls
`https://www.sanko.ac.jp/tokyo-child/`, reaches
`https://www.sanko.ac.jp/disclosure/tokyo-child/`, and finds the latest public
target-form PDF `yoshiki2025.pdf`.

The new gold-set entry preserves the important release boundary: that PDF is
valid stale/current-public evidence for operator review, but it is not FY2026/R8
strict success.

## Changed Evidence Contract

- Added gold-set entry:
  `data/discovery-gold-set/entries/sanko-tokyo-child-publication-lag-2026.json`
- Added expected prediction:
  `sanko-tokyo-child-publication-lag-2026`
- Discovery gold set now contains 45 entries:
  - accepted target PDFs: 10
  - publication-lag latest-public cases: 18
  - needs-operator-review cases: 15
  - no-target-candidate cases: 1
  - site-fetch-error cases: 1
- Expected predictions now evaluate as 45 exact matches, 0 failures.

This is a regression-proofing package change, not a strict-yield improvement.
The FY2026/R8 ship gate remains below the required current-year line.

## Verification

| Check | Result |
| --- | --- |
| Focused gold-set tests | `uv run pytest tests/unit/test_discovery_gold_set_seed.py tests/unit/test_discovery_gold_set_summary.py tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_eval.py tests/unit/test_cli_discovery_gold_set.py tests/unit/test_cli_eval_discovery_gold.py -q` -> `49 passed` |
| Focused Ruff | `uv run ruff check tests/unit/test_discovery_gold_set_seed.py tests/unit/test_discovery_gold_set_summary.py tests/unit/test_discovery_gold_set_eval.py tests/unit/test_cli_discovery_gold_set.py tests/unit/test_cli_eval_discovery_gold.py` -> `All checks passed!` |
| Discovery gold summary | `uv run python -m eidp.cli discovery-gold-set --json` -> `total_entries=45`, `publication_lag_latest_public=18`, `undemonstrated_pattern_sources=[]` |
| Expected predictions gate | `uv run python -m eidp.cli eval-discovery-gold --predictions data/discovery-gold-set/expected-predictions.jsonl --fail-on-regression --json` -> `exact_matches=45`, `failed_predictions=0` |
| Build | `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v518.zip --latest-alias` -> wrote v518 ZIP and refreshed latest alias |
| Core + OCR add-on verifier | `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v518.zip --ocr-addon dist/eidp-ocr-addon-windows-v497-smoke.zip --json` -> core `ok=true`, OCR add-on `ok=true` |
| Non-Windows release gate | `logs/win-v518-stage6-v518-non-windows-release-gates-20260520.json` -> `ok=true`, package/source fresh, full unit `1892 passed` |
| Post-docs-only release gate | `logs/win-v518-stage6-v518-post-docs-only-gates-20260520.json` -> `ok=true`, `docs_only_stale=true`, full unit `1892 passed` |

## Current Decision

v518 is the latest Mac-side package/source candidate. It includes all v517
package features plus a packaged gold-set regression case for Sanko Tokyo child
publication-lag behavior.

v518 has not completed Windows side-by-side validation because the Windows
OpenSSH/IP blocker remains unresolved. v502 remains the latest partial Windows
side-by-side setup/canary package, and v501 remains the latest complete Windows
side-by-side smoke package.

Do not merge PR #2, tag v1.0, or request owner sign-off from v518 alone. The
release still requires either strict FY2026/R8 production-scale success or an
approved `publication_lag` exception plus owner real-cycle evidence verified by
`scripts/verify_stage6_return.py`.

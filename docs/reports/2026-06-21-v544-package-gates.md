# v544 Package Gate Record

Date: 2026-06-21

Classification: P1 release hardening

Release Forecast: NOT_READY

## Summary

`v544` refreshes the Windows ZIP from current `main` after adding
false-reject worksheet triage guidance. This package keeps the FY2026/R8
strict evidence gate unchanged; it only moves the latest helper and guidance
source into a package that can be Windows-canary tested.

## Package

- ZIP: `dist/eidp-windows-v544.zip`
- SHA256: `781da0a3c1a3f4ae80536c68de2971a1ae431a01c7eb2d58001de061f62df0c1`
- Latest alias: `dist/eidp-windows.zip`
- Package source commit: `74325bc278c3e96052ef27e67cd554e426c87c60`
- `BUILD_INFO.json`: `git_branch=main`, `git_dirty=false`
- Size: `210931224` bytes

## Local Checks

Commands run:

```bash
uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v544.zip --latest-alias
uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v544.zip --require-demonstrated-discovery-patterns --json > logs/eidp-windows-v544-distribution-verify-20260621.json
uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v544.zip --json --output logs/eidp-windows-v544-release-gates-20260621.json
```

Results:

- SHA256 sidecar: `OK`
- Package/source freshness: `ok=true`
  - package commit: `74325bc278c3e96052ef27e67cd554e426c87c60`
  - source commit: `74325bc278c3e96052ef27e67cd554e426c87c60`
  - source dirty: `false`
  - stale: `false`
- Distribution verifier: `ok=true`
  - `entry_count=3118`
  - `wheel_count=84`
  - `has_runtime=true`
  - `prefecture_seed_rows=47`
  - `prefecture_seed_school_rows_total=2148`
  - `mext_target_total_rows=3132`
  - `discovery_gold_expected_predictions=45`
  - `discovery_gold_undemonstrated_pattern_sources=[]`
- Non-Windows release gates: `ok=true`
  - `unit_full`: `2049 passed, 5 warnings`
  - `validator_distribution_unit`: `196 passed`
  - `validator_distribution_mypy`: `Success: no issues found`
  - `validator_distribution_ruff`: `All checks passed`
  - `discovery_gold_summary`: `45` entries, `10` strict target-year successes
  - `discovery_gold_expected_predictions`: `45/45` exact matches
  - `package_verify`: `0`
  - `package_verify_demonstrated_patterns`: `0`

Evidence files:

- `logs/eidp-windows-v544-distribution-verify-20260621.json`
- `logs/eidp-windows-v544-release-gates-20260621.json`

## Release Boundary

This is package and non-Windows release-gate evidence only. It does not approve
v1.0, does not prove owner/operator acceptance, and does not change the release
forecast. Windows setup/canary evidence is recorded separately in
`docs/reports/2026-06-21-v544-triage-helper-windows-canary.md`.

The release remains blocked by FY2026/R8 strict Excel-ready yield below gate,
missing owner real Windows cycle/sign-off, unresolved publication-lag decision,
and unresolved OCR scope.

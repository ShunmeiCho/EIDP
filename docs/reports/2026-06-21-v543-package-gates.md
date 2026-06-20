# v543 Package Gate Record

Date: 2026-06-21

Classification: P1 release hardening

Release Forecast: NOT_READY

## Summary

`v543` refreshes the Windows ZIP from current `main` after packaging the
false-reject audit helper required by `scripts/verify_stage6_return.py`.

This closes a package/source helper gap: `verify_stage6_return.py` dynamically
loads `scripts/build_false_reject_audit.py` when `--false-reject-evidence-zip`
and `--false-reject-review-csv` are supplied, so the helper must be shipped in
the Windows operator ZIP.

## Package

- ZIP: `dist/eidp-windows-v543.zip`
- SHA256: `c3b80835225864f57f62c33fa87cde2cdb5b2006ee2da0fdfa726cccfdc5a094`
- Latest alias: `dist/eidp-windows.zip`
- Package source commit: `6aa5735d164101cbe6ec85648bcb8b6f46168c63`
- `BUILD_INFO.json`: `git_branch=main`, `git_dirty=false`
- Size: `210930229` bytes

## Local Checks

Commands run:

```bash
uv run pytest tests/unit/test_false_reject_audit.py tests/unit/test_stage6_return_verifier.py -q
uv run pytest tests/unit/test_windows_distribution_verifier.py -q
uv run pytest tests/unit/test_governance_rolling_fiscal_year_contract.py tests/unit/test_windows_distribution_verifier.py -q
uv run pytest tests/unit/test_governance_rolling_fiscal_year_contract.py tests/unit/test_windows_distribution_verifier.py tests/unit/test_false_reject_audit.py tests/unit/test_stage6_return_verifier.py -q
uv run ruff check scripts/build_windows_zip.py scripts/verify_windows_distribution.py tests/unit/test_windows_distribution_verifier.py tests/unit/test_governance_rolling_fiscal_year_contract.py
uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v543.zip --latest-alias
shasum -a 256 -c dist/eidp-windows-v543.zip.sha256
unzip -p dist/eidp-windows-v543.zip BUILD_INFO.json
unzip -Z1 dist/eidp-windows-v543.zip | rg '^(scripts/build_false_reject_audit.py|scripts/verify_stage6_return.py|BUILD_INFO.json)$'
uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v543.zip --json --require-demonstrated-discovery-patterns > logs/eidp-windows-v543-distribution-verify-20260621.json
uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v543.zip --output logs/eidp-windows-v543-release-gates-20260621.json
```

Results:

- false-reject / Stage 6 verifier tests: `78 passed`
- Windows distribution verifier unit tests: `138 passed`
- governance / Windows distribution verifier tests: `146 passed`
- final targeted governance / distribution / false-reject / Stage 6 verifier
  suite: `224 passed`
- Ruff: passed
- SHA256 sidecar: `OK`
- ZIP contains:
  - `BUILD_INFO.json`
  - `scripts/verify_stage6_return.py`
  - `scripts/build_false_reject_audit.py`
- ZIP hygiene scan found no `__MACOSX` or AppleDouble entries.
- Distribution verifier: `ok=true`, `entry_count=3118`, `wheel_count=84`,
  `has_runtime=true`, and `discovery_gold_undemonstrated_pattern_sources=[]`.
- Non-Windows release gates: `ok=true`.
  - `unit_full`: `2049 passed`
  - `validator_distribution_unit`: `196 passed`
  - `validator_distribution_mypy`: `Success: no issues found`
  - `validator_distribution_ruff`: `All checks passed`
  - `discovery_gold_summary`: `45` entries, `10` strict target-year successes
  - `discovery_gold_expected_predictions`: `45/45` exact matches
  - `package_verify`: `0`
  - `package_verify_demonstrated_patterns`: `0`

Evidence files:

- `logs/eidp-windows-v543-distribution-verify-20260621.json`
- `logs/eidp-windows-v543-release-gates-20260621.json`

## Release Boundary

This is Mac-side package and release-gate evidence only. It does not replace the
latest bounded Windows canary, which remains v542, and it does not approve
v1.0. v543 still needs Windows setup/canary evidence before it can become the
current Windows-validated package.

The release remains blocked by FY2026/R8 strict Excel-ready yield below gate,
missing owner real Windows cycle/sign-off, unresolved publication-lag decision,
and unresolved OCR scope.

# v535 AppleDouble-Clean Package

Date: 2026-06-20
Branch: `main`
Package: `dist/eidp-windows-v535.zip`
SHA256: `72ef94f35a2cd482eb9650d1a466cb8441f7d96a660a8901710d96603e7d8e9f`
Package/source commit: `d742327570a08a8f9d6ade7adfc81da8940294b4`
Status: package/source verified on macOS; not Windows side-by-side validated
Classification: P1 release hardening

## Purpose

v535 rebuilds the Windows ZIP after hardening the builder and verifier against
macOS AppleDouble sidecar files under `wheelhouse/._*.whl`. v534 carried the
right specialty-school release-proof scope gate, but was rejected after the
hardened verifier found AppleDouble wheelhouse sidecars in the ZIP.

v535 is the current Mac/package-source candidate. It is not Windows release
evidence until transferred and validated on Windows.

## Verification

Package build:

```text
uv run python scripts/build_windows_zip.py \
  --out-zip dist/eidp-windows-v535.zip \
  --latest-alias
```

Result:

```text
OK: wheelhouse contains 84 accepted wheels
OK: wrote dist/eidp-windows-v535.zip (201.1 MB)
OK: wrote checksum sidecar dist/eidp-windows-v535.zip.sha256
OK: refreshed latest alias /Users/shunmei/workspace/EIDP/dist/eidp-windows.zip
```

ZIP-side AppleDouble check:

```text
appledouble 0
wheelhouse whl 84
```

Checksum:

```text
shasum -a 256 -c dist/eidp-windows-v535.zip.sha256
```

Result:

```text
dist/eidp-windows-v535.zip: OK
```

Package verifier:

```text
uv run python scripts/verify_windows_distribution.py \
  dist/eidp-windows-v535.zip \
  --json
```

Key verified details:

```text
ok: true
git_commit: d742327570a08a8f9d6ade7adfc81da8940294b4
git_dirty: false
sha256: 72ef94f35a2cd482eb9650d1a466cb8441f7d96a660a8901710d96603e7d8e9f
entry_count: 3116
wheel_count: 84
project_wheel_count: 1
has_runtime: true
mext_target_total_rows: 3132
mext_target_university_rows: 769
mext_target_specialty_rows: 2067
mext_target_short_college_rows: 239
mext_target_kosen_rows: 57
prefecture_seed_rows: 47
prefecture_seed_school_rows_total: 2148
```

Full non-Windows release gate:

```text
uv run python scripts/run_non_windows_release_gates.py \
  dist/eidp-windows-v535.zip \
  --json \
  --output logs/win-v535-stage6-v535-non-windows-release-gates-20260620.json
```

Result:

```text
ok: true
package_source_check.ok: true
package_source_check.stale: false
package_source_check.source_dirty: false
unit_full: 2016 passed
validator_distribution_unit: 196 passed
validator_distribution_mypy: success
validator_distribution_ruff: success
discovery_gold_expected_predictions: exact_matches=45, failed_predictions=0
package_verify: ok
package_verify_demonstrated_patterns: ok
```

## Artifact Cleanup

Generated release ZIPs are stored on the external SSD through the repository
`dist` symlink:

```text
dist -> /Volumes/M1nG-ssd/EIDP-artifacts/dist
```

After v535 verification, `scripts/prune_release_artifacts.py` was run with
`--keep-latest 1 --keep-version 533 --apply`. It deleted the invalid v534 core
ZIP and sidecar, leaving:

```text
dist/eidp-windows-v533.zip
dist/eidp-windows-v535.zip
dist/eidp-windows.zip
```

## Release Boundary

v535 is not v1.0 release approval. Before using v535 for owner/operator
validation, it still needs Windows transfer, setup validation, UI smoke,
bounded weekly canary, Excel smoke, Stage 6 bundle creation, and Stage 6
evidence verification.

The release decision remains `NOT_READY` because:

- FY2026/Reiwa 8 strict current-year acquisition remains below the release
  gate in the latest Windows canary evidence.
- Owner/operator real Windows cycle sign-off is missing.
- The `publication_lag` release exception is not approved.
- OCR scope remains unresolved without a validated OCR add-on or a written
  release-scope decision.

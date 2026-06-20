# v534 Specialty-Scope Gate Package

Date: 2026-06-20
Branch: `main`
Package: `dist/eidp-windows-v534.zip`
SHA256: `734918dbe2213723936aa9148f4260256845f7cfd5044ca0c486bdd237335c05`
Package/source commit: `aeff9be53e6429f0c3116dfb50f5d35930aa923e`
Status: rejected by hardened package verifier; do not use for Windows validation
Classification: P1 release hardening

## Purpose

v534 rebuilt the Windows ZIP from current `main` after the post-v533
release-proof hardening. The package carried the verifier contract that v1
release evidence must stay scoped to `専門学校` and must not be satisfied by
university or mixed-scope evidence.

During follow-up inspection, the ZIP was found to contain macOS AppleDouble
sidecar files under `wheelhouse/._*.whl`. The package verifier has since been
hardened to reject those sidecars, so v534 must not be transferred or validated
on Windows. The latest complete Windows side-by-side smoke remains v533 until a
clean successor package is built and validated.

## Initial Verification

Package build:

```text
uv run python scripts/build_windows_zip.py \
  --out-zip dist/eidp-windows-v534.zip \
  --latest-alias
```

Result:

```text
OK: wrote dist/eidp-windows-v534.zip (201.2 MB)
OK: wrote checksum sidecar dist/eidp-windows-v534.zip.sha256
OK: refreshed latest alias /Users/shunmei/workspace/EIDP/dist/eidp-windows.zip
```

Checksum:

```text
shasum -a 256 -c dist/eidp-windows-v534.zip.sha256
```

Result:

```text
dist/eidp-windows-v534.zip: OK
```

Package verifier:

```text
uv run python scripts/verify_windows_distribution.py \
  dist/eidp-windows-v534.zip \
  --json
```

Key verified details:

```text
ok: true
git_commit: aeff9be53e6429f0c3116dfb50f5d35930aa923e
git_dirty: false
sha256: 734918dbe2213723936aa9148f4260256845f7cfd5044ca0c486bdd237335c05
entry_count: 3200
wheel_count: 168
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
  dist/eidp-windows-v534.zip \
  --json \
  --output logs/win-v534-stage6-v534-non-windows-release-gates-20260620.json
```

Result:

```text
ok: true
package_source_check.ok: true
package_source_check.stale: false
package_source_check.source_dirty: false
unit_full: 2013 passed
validator_distribution_unit: 195 passed
validator_distribution_mypy: success
validator_distribution_ruff: success
discovery_gold_expected_predictions: exact_matches=45, failed_predictions=0
package_verify: ok
package_verify_demonstrated_patterns: ok
```

## Rejection After Verifier Hardening

The hardened package verifier was rerun against the v534 ZIP:

```text
uv run python scripts/verify_windows_distribution.py \
  dist/eidp-windows-v534.zip \
  --json
```

Result:

```text
ok: false
wheel_count: 84
error: wheelhouse contains AppleDouble sidecar files: ['wheelhouse/._alembic-1.18.4-py3-none-any.whl', ...]
```

Root cause:

```text
dist/ is a symlink to /Volumes/M1nG-ssd/EIDP-artifacts/dist.
The external volume produced AppleDouble sidecar files for wheelhouse entries.
The old builder collected every *.whl, including wheelhouse/._*.whl.
The old verifier counted those sidecars as wheels instead of rejecting them.
```

Fix:

```text
scripts/build_windows_zip.py ignores wheelhouse/._*.whl during wheelhouse
verification and ZIP member collection.
scripts/verify_windows_distribution.py rejects any packaged
wheelhouse/._* entry.
```

## Release Boundary

v534 is not a valid package candidate. Before using a successor package for
owner/operator validation, it still needs Windows transfer, setup validation,
UI smoke, bounded weekly canary, Excel smoke, Stage 6 bundle creation, and
Stage 6 evidence verification.

The release decision remains `NOT_READY` because:

- FY2026/Reiwa 8 strict current-year acquisition remains below the release
  gate in the latest Windows canary evidence.
- Owner/operator real Windows cycle sign-off is missing.
- The `publication_lag` release exception is not approved.
- OCR scope remains unresolved without a validated OCR add-on or a written
  release-scope decision.

## Artifact Cleanup

The generated `dist/` directory is a symlink to
`/Volumes/M1nG-ssd/EIDP-artifacts/dist`, so release ZIPs are stored on the
external SSD rather than the Mac internal SSD.

After v534 verification, the release-artifact pruner was run with
`--keep-latest 2 --apply`. It deleted the local v532 core ZIP and sidecar:

```text
dist/eidp-windows-v532.zip
dist/eidp-windows-v532.zip.sha256
```

The kept local core packages are:

```text
dist/eidp-windows-v533.zip
```

After the AppleDouble fix landed and v535 was built, the pruner was run again
with `--keep-latest 1 --keep-version 533 --apply`. It deleted the invalid local
v534 core ZIP and sidecar, leaving v533 and v535 as the kept core packages.

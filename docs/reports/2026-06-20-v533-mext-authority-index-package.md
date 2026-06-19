# v533 MEXT Authority Index Package Gate

Date: 2026-06-20
Branch: `main`
Package: `dist/eidp-windows-v533.zip`
SHA256: `0d4ca81a9032db1d8b98bf69ba76a4181d99d6bb8cd0091de22df211dc5d5f57`
Package/source commit: `f83f1dc5439156bb9909ea1df5132bed3a7e9b85`
Status: package/source verified; not Windows side-by-side validated

## Purpose

This package adds a source-side and package-verifier gate for the MEXT T0
target-institution official index. The goal is to prevent the university scope
from being claimed through broad web/PDF search and to require a packaged,
official, auditable source catalog before downstream discovery work.

This does not complete the university lane. It proves the official index and
package boundary only. University target-document discovery, extraction, and
Excel mapping still need separate implementation and Windows evidence.

## Packaged Official Sources

The v533 ZIP now includes:

- `data/authority-index/sources.csv`
- `data/mext/target_institutions_page.html`
- `data/mext/target_institutions.xlsx`

The source catalog row uses the MEXT official page:

`https://www.mext.go.jp/a_menu/koutou/hutankeigen/1421838.htm`

The row is classified as:

- `authority_type=mext`
- `trust_tier=t0_mext`
- `auto_accept_allowed=yes`
- institution types include `大学` and `専門学校`

## Verification

Focused source verification before the package rebuild:

```text
uv run pytest tests/unit/test_windows_packaging_spike.py::test_reset_wheelhouse_removes_appledouble_files \
  tests/unit/test_windows_packaging_spike.py::test_collect_zip_members_includes_alembic_and_weekly_runner \
  tests/unit/test_windows_distribution_verifier.py -q
```

Result:

```text
135 passed
```

Focused quality checks:

```text
uv run ruff check scripts/build_windows_zip.py scripts/verify_windows_distribution.py \
  tests/unit/test_windows_distribution_verifier.py tests/unit/test_windows_packaging_spike.py
uv run mypy scripts/build_windows_zip.py scripts/verify_windows_distribution.py
```

Results:

```text
All checks passed!
Success: no issues found in 2 source files
```

Package integrity:

```text
shasum -a 256 dist/eidp-windows-v533.zip
cat dist/eidp-windows-v533.zip.sha256
python3 -m zipfile -t dist/eidp-windows-v533.zip
```

Results:

```text
0d4ca81a9032db1d8b98bf69ba76a4181d99d6bb8cd0091de22df211dc5d5f57
Done testing
```

Package verifier:

```text
uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v533.zip --json
```

Key verified details:

```text
entry_count: 3200
wheel_count: 168
mext_target_total_rows: 3132
mext_target_university_rows: 769
mext_target_specialty_rows: 2067
mext_target_short_college_rows: 239
mext_target_kosen_rows: 57
prefecture_seed_rows: 47
prefecture_seed_school_rows_total: 2148
```

Non-Windows release gate:

```text
uv run python scripts/run_non_windows_release_gates.py \
  dist/eidp-windows-v533.zip \
  --skip-full-unit \
  --json \
  --output logs/win-v533-stage6-v533-non-windows-release-gates-20260620.json
```

Result:

```text
ok: true
package_source_check.ok: true
source_dirty: false
validator_distribution_unit: 191 passed
validator_distribution_mypy: success
validator_distribution_ruff: success
discovery_gold_expected_predictions: 45/45 exact
package_verify: pass
```

## Storage Hygiene

The package was built through repository symlinks that point to the external
SSD:

```text
dist -> /Volumes/M1nG-ssd/EIDP-artifacts/dist
logs -> /Volumes/M1nG-ssd/EIDP-artifacts/logs
```

The external volume generated macOS AppleDouble `._*` metadata files during the
wheelhouse/package rebuild. `scripts/build_windows_zip.py` now tolerates these
files during wheelhouse cleanup with `missing_ok=True`, and the generated
`._*` files under `/Volumes/M1nG-ssd/EIDP-artifacts/dist` were removed after
the build.

## Remaining Blockers

- v533 has not completed Windows side-by-side setup, UI, weekly canary, Excel,
  OCR, or Stage 6 evidence validation.
- The latest complete Windows side-by-side smoke remains v532.
- v532 remains blocked by FY2026/R8 strict yield `12/50 (24.0%)`, missing owner
  real-cycle sign-off, unapproved `publication_lag`, and missing OCR add-on
  runtime proof.
- The university lane still needs official-index to site-entry mapping,
  target-document discovery, extraction, reconciliation, and Excel proof.

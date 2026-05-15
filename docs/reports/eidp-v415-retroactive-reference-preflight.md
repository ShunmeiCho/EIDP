# EIDP v415 Retroactive Reference Preflight

Date: 2026-05-15
Package: `dist/eidp-windows-v415.zip`
Package snapshot: `09ad5e6bfa80c8a03ab6f60b2f39a39333fdd42c`
Package SHA256: `25478903757785bec4ab34583878e0af344ceffc1f153a7de5ef219584d11ffd`
Current source snapshot when recorded: `1d6b714e2cddb566378cc5783305414dd868ffb8`

## Purpose

This report refreshes the Mac-side FY2024/FY2023 retroactive
reference-preparation diagnostics against the current v415 delivery candidate.
It is not a Stage 6 Windows operator-PC sign-off and it is not a current
FY2026/R8 yield measurement.

The FY2025/R7 canonical reference gate already passes against the proven v408
CLI export through `logs/release-gate-v415-retroactive.json`. FY2024 and FY2023
were intentionally checked against the raw
`sample/◆2025専門学校無償化情報公開まとめ.xlsx` workbook to confirm the remaining
reference-preparation work on the current package.

## Commands

FY2024 raw-sample preflight:

```bash
uv run python scripts/run_non_windows_release_gates.py \
  dist/eidp-windows-v415.zip \
  --skip-full-unit \
  --allow-docs-only-stale-package \
  --keep-going \
  --retroactive-excel-reference 'sample/◆2025専門学校無償化情報公開まとめ.xlsx' \
  --retroactive-fiscal-year 2024 \
  --retroactive-numeric-tolerance 1e-9 \
  --json \
  --output logs/release-gate-v415-retroactive-fy2024-sample.json
```

FY2024 machine-readable diff payload:

```bash
uv run eidp diff-excel \
  _temp/non-windows-retroactive-fy2024-20260515-125437/output/retroactive-fy2024-export.xlsx \
  --original 'sample/◆2025専門学校無償化情報公開まとめ.xlsx' \
  --business-values \
  --numeric-tolerance 1e-9 \
  --max-diffs 20 \
  --json > _temp/fy2024-v415-raw-sample-business-diff.json
```

FY2023 raw-sample preflight:

```bash
uv run python scripts/run_non_windows_release_gates.py \
  dist/eidp-windows-v415.zip \
  --skip-full-unit \
  --allow-docs-only-stale-package \
  --keep-going \
  --retroactive-excel-reference 'sample/◆2025専門学校無償化情報公開まとめ.xlsx' \
  --retroactive-fiscal-year 2023 \
  --retroactive-numeric-tolerance 1e-9 \
  --json \
  --output logs/release-gate-v415-retroactive-fy2023-sample.json
```

FY2023 machine-readable diff payload:

```bash
uv run eidp diff-excel \
  _temp/non-windows-retroactive-fy2023-20260515-125526/output/retroactive-fy2023-export.xlsx \
  --original 'sample/◆2025専門学校無償化情報公開まとめ.xlsx' \
  --business-values \
  --numeric-tolerance 1e-9 \
  --max-diffs 20 \
  --json > _temp/fy2023-v415-raw-sample-business-diff.json
```

## Results

Both FY2024 and FY2023 preflights verified v415 ZIP integrity, accepted the
current docs-only stale source state, passed the validator/distribution unit
slice, passed validator mypy/Ruff, passed discovery-gold expected predictions,
and passed package verification including demonstrated discovery patterns.

Both isolated app roots bootstrapped SQLite, imported `data/master.xlsx`, and
exported workbooks successfully:

| Fiscal year | App root | Export workbook | Export row counts |
| --- | --- | --- | --- |
| FY2024 | `_temp/non-windows-retroactive-fy2024-20260515-125437` | `output/retroactive-fy2024-export.xlsx` | `採録状況=2418`, `対象比率=10022`, `学科別=9719`, `在籍のみ抜粋=9719` |
| FY2023 | `_temp/non-windows-retroactive-fy2023-20260515-125526` | `output/retroactive-fy2023-export.xlsx` | `採録状況=2418`, `対象比率=10022`, `学科別=9719`, `在籍のみ抜粋=9719` |

The raw-sample business-value comparisons intentionally failed:

| Fiscal year | JSON payload | Missing rows | Extra rows | Differing fields | Primary interpretation |
| --- | --- | ---: | ---: | ---: | --- |
| FY2024 | `_temp/fy2024-v415-raw-sample-business-diff.json` | 1097 | 1557 | 12548 | Raw sample has duplicate keys, formula-error/unknown placeholders, name drift, and field-year schema drift. |
| FY2023 | `_temp/fy2023-v415-raw-sample-business-diff.json` | 1097 | 1557 | 9718 | Same reference issues; fewer differing fields because later-year columns are outside the FY2023 export surface. |

Per-sheet duplicate-key evidence from the raw sample:

| Fiscal year | Sheet | Original duplicate keys | Original duplicate rows | Exported duplicate keys |
| --- | --- | ---: | ---: | ---: |
| FY2024 | `対象比率` | 13 | 13 | 0 |
| FY2024 | `学科別` | 22 | 23 | 0 |
| FY2024 | `在籍のみ抜粋` | 22 | 23 | 0 |
| FY2023 | `対象比率` | 13 | 13 | 0 |
| FY2023 | `学科別` | 22 | 23 | 0 |
| FY2023 | `在籍のみ抜粋` | 22 | 23 | 0 |

The largest field-diff categories remain reference-policy issues:

| Fiscal year | Sheet | Category highlights |
| --- | --- | --- |
| FY2024 | `対象比率` | `export_blank_vs_original_error_or_unknown=3014`, `export_blank_vs_original_value=73`, `numeric_mismatch=4` |
| FY2024 | `学科別` | `export_blank_vs_original_error_or_unknown=5750`, `export_blank_vs_original_value=2910`, `numeric_mismatch=87` |
| FY2024 | `在籍のみ抜粋` | `export_blank_vs_original_error_or_unknown=22`, `export_blank_vs_original_value=47`, `numeric_mismatch=27` |
| FY2023 | `対象比率` | `export_blank_vs_original_error_or_unknown=3014`, `export_blank_vs_original_value=73`, `numeric_mismatch=4` |
| FY2023 | `学科別` | `export_blank_vs_original_error_or_unknown=3871`, `export_blank_vs_original_value=2111`, `numeric_mismatch=82` |
| FY2023 | `在籍のみ抜粋` | `export_blank_vs_original_error_or_unknown=19`, `export_blank_vs_original_value=45`, `numeric_mismatch=21` |

## Interpretation

Do not promote the raw sample workbook to an FY2024/FY2023 pass/fail reference.
The evidence proves that v415 can generate the retroactive workbooks in isolated
Mac app roots, and it keeps the remaining N=3 backtest work tied to the latest
delivery package.

The next useful Mac-only step is to create canonical FY2024/FY2023 reference
workbooks by resolving duplicate business keys, formula-error placeholders,
unknown-string placeholders, name drift, and field-year schema policy. Only
after those references are prepared should `--retroactive-excel-reference` be
expected to return `ok=true` for FY2024 and FY2023.

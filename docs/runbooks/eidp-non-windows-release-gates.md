# EIDP Non-Windows Release Gates

This runbook defines the checks that can run on macOS or Linux before a Windows
operator package is handed to a Windows PC.

These gates do **not** replace Windows setup, Task Scheduler, browser UI, or
operator click-through evidence. They only prove the source/package/gold-set
contracts that do not require Windows.

## Full Gate

Use this before calling a package Mac-verifier-clean:

```bash
uv run python scripts/run_non_windows_release_gates.py \
  dist/eidp-windows-v351.zip \
  --json \
  --output _temp/v351-non-windows-release-gates-full.json
```

Expected result:

- top-level `ok=true`
- SHA256 sidecar matches the ZIP bytes
- `package_source_check.ok=true`: the ZIP `BUILD_INFO.json` commit matches the
  current source `HEAD`, and the current source tree has no uncommitted tracked
  changes
- full unit suite passes
- validator/distribution unit tests pass
- validator/distribution mypy and Ruff pass
- discovery gold-set summary reports no undemonstrated production pattern sources
- committed expected predictions replay exactly
- package verifier passes
- package verifier with `--require-demonstrated-discovery-patterns` passes

If this check fails with `package_source_check.stale=true`, the ZIP is a
historical package and must not be called Mac-verifier-clean for the current
source tree. Build an approved new ZIP only when the release lane explicitly
permits it.

`scripts/build_windows_zip.py` also refuses to build a Windows ZIP from
uncommitted tracked source by default. Use `--allow-dirty` only for diagnostic
builds that will not be treated as current release evidence.

For archaeology or historical report regeneration only, rerun with
`--allow-stale-package`. That flag intentionally bypasses the current-source
commit and dirty-tree checks, so do not use it for current release readiness.

If a ZIP was already built and the only later tracked changes are evidence
documentation under `docs/`, use the narrower
`--allow-docs-only-stale-package` flag. That flag still rejects dirty tracked
source, unknown commits, non-ancestor package commits, and any non-`docs/`
changed path between the ZIP `BUILD_INFO.json` commit and current `HEAD`.

## Bounded Evidence Replay

When bounded Windows evidence JSONL already exists locally, include it in the
same helper:

```bash
uv run python scripts/run_non_windows_release_gates.py \
  dist/eidp-windows-v351.zip \
  --skip-full-unit \
  --pdf-evidence _temp/win-v342-tokyo-probe/discovery_rejections_tokyo_v342_30.jsonl \
  --pdf-evidence _temp/win-v342-evidence/discovery_rejections.jsonl \
  --json \
  --output _temp/v351-non-windows-release-gates-evidence.json
```

For bounded evidence replays, missing gold-set entries are allowed because a
bounded run covers only part of the gold-set. Failed predictions or unexpected
predictions are not allowed and make the helper fail.

Current expected local replay results:

- Tokyo v342 30-site evidence: `4` exact, `0` failed predictions
- Saitama v342 bounded evidence: `16` exact, `0` failed predictions

## Optional Retroactive Excel Gate

When a previously proven R7/FY2025 workbook is available locally, add an
isolated retroactive Excel business-value gate:

```bash
uv run python scripts/run_non_windows_release_gates.py \
  dist/eidp-windows-v420.zip \
  --retroactive-excel-reference _temp/v408-r7-cli-export.xlsx \
  --retroactive-fiscal-year 2025 \
  --json \
  --output logs/release-gate-v420-retroactive.json
```

This option creates a temporary `_temp/non-windows-retroactive-*` app root,
copies `data/master.xlsx`, bootstraps a SQLite database, imports the workbook,
exports the requested fiscal year, and runs `eidp diff-excel --business-values
--fail-on-diff` against the reference workbook. The auto-generated app root is
removed after the gate run by default; pass `--keep-retroactive-app-root` only
when you intentionally need to inspect the isolated SQLite or exported workbook.

If a legacy reference workbook differs only by harmless floating-point
rounding, pass `--retroactive-numeric-tolerance <value>` to forward an absolute
numeric tolerance to `diff-excel`. Keep the default `0.0` for release snapshots;
this option does not ignore missing/extra rows, duplicate business keys, formula
errors, or other real business-value differences.

Use this as an algorithm regression gate for rolling-FY Excel output. It does
not replace the Windows transfer/setup/UI gates, and it does not prove the
current FY2026/R8 60-70% target-PDF acquisition line.

The current Mac-side regression lane has v420 FY2025/FY2024/FY2023 proof:

| Fiscal year | Reference workbook | Gate output |
| --- | --- | --- |
| FY2025 / R7 | `_temp/v408-r7-cli-export.xlsx` | `logs/release-gate-v420-retroactive-fy2025-reference.json` |
| FY2024 / R6 | `_temp/non-windows-retroactive-fy2024-20260515-125437/output/retroactive-fy2024-export.xlsx` | `logs/release-gate-v420-retroactive-fy2024-reference.json` |
| FY2023 / R5 | `_temp/non-windows-retroactive-fy2023-20260515-125526/output/retroactive-fy2023-export.xlsx` | `logs/release-gate-v420-retroactive-fy2023-reference.json` |

The FY2024/FY2023 references are generated stable references. Do not substitute
the raw `sample/◆2025専門学校無償化情報公開まとめ.xlsx` workbook as a pass/fail
reference until its duplicate keys, formula-error placeholders, unknown values,
name drift, and field-year policy have been canonicalized.

To rerun the three-year lane without copying three separate release-gate
commands, use the matrix runner:

```bash
uv run python scripts/run_retroactive_excel_matrix.py \
  dist/eidp-windows-v420.zip \
  --allow-docs-only-stale-package \
  --case 2025=_temp/v408-r7-cli-export.xlsx \
  --case 2024=_temp/non-windows-retroactive-fy2024-20260515-125437/output/retroactive-fy2024-export.xlsx \
  --case 2023=_temp/non-windows-retroactive-fy2023-20260515-125526/output/retroactive-fy2023-export.xlsx \
  --json \
  --output logs/release-gate-v420-retroactive-matrix.json
```

The runner writes per-year JSON outputs using the package label and fiscal year,
then writes the optional matrix summary to `--output`.

### Local Artifact Cleanup

Release gates and retroactive Excel checks can create disposable app roots and
probe artifacts under `_temp/`. Current `run_non_windows_release_gates.py`
removes its auto-generated retroactive app root by default, but historical
probes, explicitly kept roots, and manually generated references still need
periodic cleanup. Do not let those directories accumulate between release
candidates.

After recording the gate JSONs you need, run a dry-run cleanup first:

```bash
uv run python scripts/cleanup_local_artifacts.py --aggressive --json
```

Then delete only generated artifacts, preserving the current retroactive
references:

```bash
uv run python scripts/cleanup_local_artifacts.py --aggressive --apply \
  --keep _temp/v408-r7-cli-export.xlsx \
  --keep _temp/non-windows-retroactive-fy2025-<stamp> \
  --keep _temp/non-windows-retroactive-fy2024-<stamp> \
  --keep _temp/non-windows-retroactive-fy2023-<stamp>
```

The cleanup helper is dry-run by default, scans only top-level entries under
`_temp/`, refuses symlinks, and never touches `data/master.xlsx`,
`data/eidp.sqlite3`, `data/pdfs/`, `dist/`, or Windows operator deployments.

For release ZIP/deploy retention, use the separate release-artifact pruner.
This tool is also dry-run by default and only matches versioned EIDP package
names or extracted deploy directories:

```bash
uv run python scripts/prune_release_artifacts.py \
  --keep-latest 1 \
  --keep-version 442 \
  --json
```

When the dry-run output is correct, add `--apply`. On a Windows staging or
operator-PC test host, pass the staging and deploy roots explicitly:

```powershell
python scripts\prune_release_artifacts.py `
  --dist-dir C:\EIDP-staging `
  --deploy-parent C:\Users\cyo20 `
  --keep-latest 1 `
  --keep-version 442 `
  --json
```

Use `--keep-version` for a non-latest fallback package with stronger evidence,
such as v442. The pruner does not scan `data\`, `logs\`, `output\`, SQLite
files, `master.xlsx`, or audit JSONL.

## What This Proves

- The ZIP has the expected source, data, wheelhouse, runbook, and validator
  structure.
- The ZIP belongs to the same clean tracked source tree being gated, unless the
  run was explicitly marked as historical with `--allow-stale-package` or the
  only stale delta was audited as docs-only with
  `--allow-docs-only-stale-package`.
- The package carries 47 prefecture seed rows and a complete discovery gold-set.
- Production-tracked discovery pattern sources are demonstrated in the gold-set.
- Existing bounded discovery evidence still maps to the expected gold outcomes.
- Stale-year fallback and synthetic-only extractor sources are guarded before
  Windows handoff.
- With `--retroactive-excel-reference`, the current source can rebuild a
  previous-year database from `master.xlsx` and reproduce the already proven
  retroactive Excel business values.

## What This Does Not Prove

- Windows ZIP extraction works on the operator PC.
- `EIDP-setup.bat`, `EIDP-start.bat`, or `EIDP-diagnose.bat` work on Windows.
- Browser UI workflows work for the operator.
- Task Scheduler behavior is correct.
- Strict current-FY target PDF acquisition has reached the 60-70% ship line.

Those remain Windows-side gates and must be recorded in
`docs/runbooks/eidp-operator-e2e-template.md` and
`docs/reports/current-release-status.md`.

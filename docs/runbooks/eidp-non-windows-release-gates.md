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

For archaeology or historical report regeneration only, rerun with
`--allow-stale-package`. That flag intentionally bypasses the current-source
commit and dirty-tree checks, so do not use it for current release readiness.

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

## What This Proves

- The ZIP has the expected source, data, wheelhouse, runbook, and validator
  structure.
- The ZIP belongs to the same clean tracked source tree being gated, unless the
  run was explicitly marked as historical with `--allow-stale-package`.
- The package carries 47 prefecture seed rows and a complete discovery gold-set.
- Production-tracked discovery pattern sources are demonstrated in the gold-set.
- Existing bounded discovery evidence still maps to the expected gold outcomes.
- Stale-year fallback and synthetic-only extractor sources are guarded before
  Windows handoff.

## What This Does Not Prove

- Windows ZIP extraction works on the operator PC.
- `EIDP-setup.bat`, `EIDP-start.bat`, or `EIDP-diagnose.bat` work on Windows.
- Browser UI workflows work for the operator.
- Task Scheduler behavior is correct.
- Strict current-FY target PDF acquisition has reached the 60-70% ship line.

Those remain Windows-side gates and must be recorded in
`docs/runbooks/eidp-operator-e2e-template.md` and
`docs/reports/current-release-status.md`.

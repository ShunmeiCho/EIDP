# Current-Source Retroactive Excel Matrix

Date: 2026-05-17
Branch: `sprint8-handoff-finalize`
Scope: current source tree, not a Windows package freshness gate

## Purpose

This matrix verifies that the current source tree still reproduces the mature
FY2025/FY2024/FY2023 Excel business values after the Stage 6 release-exception,
v465 promotion-runbook, CI/package, portability, weekly-progress, bug-report,
target-FY override, and shared-origin discovery changes.

It intentionally does not count as fresh v465 package evidence:
`dist/eidp-windows-v465.zip` was built at package/source commit
`be32eb29212f71f72e6ab7e6d2a4f013ccb66e42`, while the current working tree has
tracked source/docs changes. The package matrix runner correctly treats that as
a package-source freshness boundary.

Negative freshness check:
`uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v465.zip --skip-full-unit --json --output logs/release-gate-v465-current-stale-check-20260517.json`
exited `1` with `sha256_check.ok=true` but `package_source_check.ok=false`,
`source_dirty=true`, and error `current source tree has uncommitted tracked
changes`.

Current distribution-contract check:
`uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v465.zip`
also exited `1`. The ZIP SHA and `BUILD_INFO.json` were valid, but v465 was
built before the source-side publication-lag exception contract; it lacks
`release_exception_reason`, `SHIP_GATE_EXCEPTION_REASONS`,
`MATURE_YEAR_SHIP_GATE_METRIC_BASIS`, `publication_lag`, and
`is_ship_gate_exception_reason`.

## Evidence

Local JSON summary:
`logs/release-gate-current-source-retroactive-matrix-20260517.json`

Refreshed at: `2026-05-17T15:06:16+0900`

The run used the same lower-level retroactive commands as
`scripts/run_non_windows_release_gates.py`: prepare isolated app root, SQLite
bootstrap, import `data/master.xlsx`, export the retroactive fiscal-year
workbook, business-value diff against the frozen reference workbook, then clean
up the temporary app root.

| Fiscal year | Reference workbook | Import | Export | Diff | Cleanup | Result |
| --- | --- | ---: | ---: | ---: | --- | --- |
| FY2025 | `_temp/v459-reference2-fy2025/output/retroactive-fy2025-v459-reference.xlsx` | rc=0 / 35.868s | rc=0 / 6.895s | rc=0 / 18.074s | ok=true | pass |
| FY2024 | `_temp/v459-reference2-fy2024/output/retroactive-fy2024-v459-reference.xlsx` | rc=0 / 28.626s | rc=0 / 5.764s | rc=0 / 14.568s | ok=true | pass |
| FY2023 | `_temp/v459-reference2-fy2023/output/retroactive-fy2023-v459-reference.xlsx` | rc=0 / 29.173s | rc=0 / 5.179s | rc=0 / 12.979s | ok=true | pass |

For every fiscal year, `retroactive_excel_diff_reference` reported:

```text
missing_sheets: 0
extra_sheets: 0
missing_rows: 0
extra_rows: 0
differing_fields: 0
```

Sheet-level summaries for `対象比率`, `学科別`, and `在籍のみ抜粋` also reported
zero missing rows, zero extra rows, zero missing soft matches, zero extra soft
matches, and zero duplicate keys.

## Conclusion

The current source tree still passes the mature-year Excel algorithm regression
for FY2025/FY2024/FY2023. This supports the publication-lag split: current
FY2026/R8 live yield should be recorded during the May lag window, while
mature-year evidence remains the algorithm proof.

This does not approve release, switch the active Windows lane, or replace the
owner/operator real-cycle evidence requirement.

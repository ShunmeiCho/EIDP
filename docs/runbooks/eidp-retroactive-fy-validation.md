# Retroactive Fiscal-Year Validation

Use this runbook when the current target fiscal year is still in the publication-lag window and many
schools have not yet published the current confirmation-application PDF.

The goal is to validate EIDP's rolling fiscal-year mechanics and operator workflow against a prior
year with more complete public disclosure. This is useful evidence, but it must not be reported as
current-year yield.

## Scope

- Safe for: Stage 6 browser click-through rehearsal, report/ship-readiness diagnostics, Excel preview flow,
  audit logging, and discovery behavior on already-published PDFs.
- Not proof of: current target-FY ship yield, current-year Excel readiness, or current-year publication coverage.
- Recommended isolation: use a copied install directory or a copied SQLite DB. Do not overwrite the operator's
  current-season working DB unless the owner explicitly approves.

## Recommended FY2025 Smoke

For v364 and newer packages, `EIDP-diagnose.bat` automatically adds a read-only previous-year
snapshot to the diagnostics log. With the default FY2026/R8 configuration, the log section
`[retroactive fiscal-year ship readiness]` runs FY2025/R7 and records:

- `retroactive_fiscal_year=2025`
- the JSON output from `report ship-readiness --fy 2025 --json`
- `retroactive_ship_readiness_rc`

Use that section as the quickest operator-PC evidence. Use the explicit commands below when you need
to run a full UI rehearsal with the whole process configured to the retroactive year.

For PowerShell:

```powershell
$env:EIDP_TARGET_FISCAL_YEAR = "2025"
.\EIDP-diagnose.bat
.\.venv\Scripts\python.exe -m eidp.cli report ship-readiness --json
.\.venv\Scripts\python.exe -m eidp.cli report coverage --json
```

For macOS/Linux source verification:

```bash
EIDP_TARGET_FISCAL_YEAR=2025 uv run eidp report ship-readiness --json
EIDP_TARGET_FISCAL_YEAR=2025 uv run eidp report coverage --json
```

Record the output separately from the current-year Stage 6 evidence.

In the `report ship-readiness --json` output, verify:

- `fiscal_year` is the retroactive year under test, for example `2025`.
- `calendar_current_fiscal_year` is the real current Japanese fiscal year.
- `is_retroactive_fiscal_year` is `true`.
- `is_configured_target_fiscal_year` is `false` when `--fy 2025` is used against a normal current-year install.

## Stage 6 Interpretation

If FY2025 passes the operator workflow:

- Count it as proof that the app can switch target years and execute the operator workflow.
- Count it as proof that previous-year public disclosure can be processed by the same pipeline.
- Do not count it as proof that FY2026/R8 has reached the 60-70% current-year acquisition gate.

If FY2025 fails:

- Treat it as a real pipeline/UI defect, because FY2025 should have substantially more public data available.
- Keep the failure separate from current-year publication lag.

## Returning To Current Year

Close the terminal or remove the temporary environment variable before returning to normal operations. If `.env`
was edited for a persistent smoke, restore it as a plain env-file line:

```dotenv
EIDP_TARGET_FISCAL_YEAR=2026
```

Then rerun diagnostics and confirm that the report payload is back to the intended current target FY.

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

# EIDP v465 Active-Promotion Runbook

Updated: 2026-05-17

This runbook prepares the v465 lane for owner-cycle use. It is not approval to
switch the Windows Scheduled Task by itself; run the task-switch section only
after explicit active-lane approval.

## Promotion Reason

The current active owner-cycle lane is v460. Its URL-rich FY2026 weekly probe
started at `2026-05-16 19:24:43` JST, was stopped at `2026-05-17 05:06` JST
after about 9h41m, wrote no new `data\output\last_run.json`, and generated
`234238` discovery-rejection rows / `101997049` bytes. The log showed repeated
shared corporation-domain crawls such as O-Hara `robots.txt=152`,
`sitemap.xml=52`, and `about/joho/=283`.

v465 is the current non-active candidate for removing that active-lane deadlock.
It should be promoted before any new unbounded owner weekly run is requested.

Post-2026-05-17 contract note: after the source-side publication-lag exception
and mature-year gate contract were added, the current distribution verifier
rejects `dist/eidp-windows-v465.zip` because that ZIP was built before those
tokens existed. Treat v465 as the cache/performance-fix lane only. A release
candidate that includes the new exception verifier contract needs a clean
rebuilt successor package.

Before transferring a successor release package, rebuild from a clean committed
source snapshot and run `scripts/verify_windows_distribution.py`. A dirty
diagnostic ZIP may prove packaging feasibility, but it is not a release
artifact and must not be used for owner transfer.

## Candidate Package

| Item | Value |
| --- | --- |
| Package | `dist/eidp-windows-v465.zip` |
| Package/source commit | `be32eb29212f71f72e6ab7e6d2a4f013ccb66e42` |
| SHA256 | `b8b6157261aae4986cab0050fa980265ddd6075660577157fe5a3360a04af041` |
| Target Windows root | `%USERPROFILE%\EIDP-v465-be32eb2` |
| Existing active fallback | `%USERPROFILE%\EIDP-v460-01e4427` |
| Current contract status | perf-fix candidate, not current release-candidate package |

Keep v460 as fallback for at least 30 days. Do not delete v460 data, logs,
SQLite, audit JSONL, or evidence bundles during v465 promotion.

## Mac Preflight

```bash
shasum -a 256 dist/eidp-windows-v465.zip
uv run pytest tests/unit/test_pdf_discovery.py -k "repeated_http_gets or cached_rejection" -q
uv run pytest tests/unit/test_run_weekly_target_year_discovery.py::test_run_weekly_passes_current_fy_to_ingestion -q
```

Expected:

| Check | Expected |
| --- | --- |
| ZIP SHA256 | `b8b6157261aae4986cab0050fa980265ddd6075660577157fe5a3360a04af041` |
| shared-domain cache regression | pass |
| weekly target-FY propagation | pass |
| current distribution verifier | expected fail until rebuilt successor includes publication-lag contract |

## Windows Setup Preflight

Run from PowerShell on the operator PC. If the root already exists, do not
delete or overwrite it; skip extraction and continue with validation.

Important: `EIDP-setup.bat` rewrites `EIDP Weekly Run` to the extracted root.
For a side-by-side preflight before active-lane approval, back up the current
scheduled task first and restore it immediately after setup validation.

```powershell
$zip = "C:\EIDP-staging\eidp-windows-v465.zip"
$deployParent = $env:USERPROFILE
$root = Join-Path $deployParent "EIDP-v465-be32eb2"
$fallbackRoot = Join-Path $deployParent "EIDP-v460-01e4427"
$fallbackAction = Join-Path $fallbackRoot "scripts\weekly_run.bat"
$expected = "b8b6157261aae4986cab0050fa980265ddd6075660577157fe5a3360a04af041"
$taskName = "EIDP Weekly Run"
$preflightBackupXml = "C:\EIDP-staging\EIDP-Weekly-Run-before-v465-preflight.xml"
$actual = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $expected) { throw "SHA256 mismatch: $actual" }

schtasks /Query /TN "\EIDP Weekly Run" /XML | Set-Content -Path $preflightBackupXml -Encoding UTF8

if (-not (Test-Path $root)) {
  New-Item -ItemType Directory -Path $root | Out-Null
  Expand-Archive -Path $zip -DestinationPath $root
}

try {
  Set-Location $root
  .\EIDP-setup.bat
  .\scripts\validate_install.bat --after-setup --json
  .\scripts\diagnose.bat
} finally {
  Register-ScheduledTask -TaskName $taskName `
    -Xml (Get-Content $preflightBackupXml | Out-String) `
    -Force

  Set-Location $fallbackRoot
  .\scripts\stage6_recovery_check.bat $fallbackAction
}
```

After the restore, confirm the recovery check returns `ok=true` and
`action_matches_expected=true` for the v460 fallback action.
Do not run the unbounded FY2026 weekly probe from v460 again. A new owner cycle
should use v465 only after the task switch below is approved.

## Active Task Switch

Approval boundary: this section changes external Windows state. Run it only
after explicit instruction to promote v465 to active.

```powershell
$taskName = "EIDP Weekly Run"
$backupXml = "C:\EIDP-staging\EIDP-Weekly-Run-before-v465.xml"
$root = Join-Path $env:USERPROFILE "EIDP-v465-be32eb2"
$expectedAction = Join-Path $root "scripts\weekly_run.bat"

schtasks /Query /TN "\EIDP Weekly Run" /XML | Set-Content -Path $backupXml -Encoding UTF8
$action = New-ScheduledTaskAction `
  -Execute $expectedAction `
  -WorkingDirectory $root
Set-ScheduledTask -TaskName $taskName -Action $action

Set-Location $root
.\scripts\stage6_recovery_check.bat $expectedAction
```

Expected recovery result: `ok=true` and `action_matches_expected=true`.

Rollback, if needed:

```powershell
Register-ScheduledTask -TaskName "EIDP Weekly Run" `
  -Xml (Get-Content "C:\EIDP-staging\EIDP-Weekly-Run-before-v465.xml" | Out-String) `
  -Force
```

## Retroactive Excel Algorithm Evidence

FY2026/R8 live yield in mid-May is publication-lag sensitive and should be
recorded, not treated as the only algorithm gate. Use FY2025/R7 mature data to
prove the Excel business-value path, but do not confuse Excel diff evidence
with target-PDF acquisition evidence.

Mac-side matrix command, from the package snapshot or a freshly rebuilt package
matching the current source:

```bash
uv run python scripts/run_retroactive_excel_matrix.py dist/eidp-windows-v465.zip \
  --skip-full-unit \
  --case 2025=_temp/v459-reference2-fy2025/output/retroactive-fy2025-v459-reference.xlsx \
  --case 2024=_temp/v459-reference2-fy2024/output/retroactive-fy2024-v459-reference.xlsx \
  --case 2023=_temp/v459-reference2-fy2023/output/retroactive-fy2023-v459-reference.xlsx \
  --output logs/release-gate-v465-retroactive-matrix-refresh.json
```

Treat retroactive matrix output as algorithm evidence only. It is not a fresh
v465 package evidence bundle when the source tree has moved after the v465
package commit, and it is not accepted by `verify_stage6_return.py` as mature
year acquisition proof.

## Mature-Year Acquisition Proof

The `publication_lag` exception requires a mature-year weekly acquisition proof
JSON built from real `last_run.json` metrics, not from Excel matrix diff JSON:

```bash
uv run python scripts/build_mature_year_acquisition_proof.py \
  --case 2025=logs/<mature-year-weekly-run>/last_run.json \
  --output logs/mature-year-acquisition-proof.json \
  --json
```

The proof builder requires:

- `target_pdf_auto_yield_pct >= 60.0`
- `operator_reviewable_yield_pct >= 70.0`
- `target_pdf_auto_denominator_count >= 1000`
- `target_pdf_auto_denominator_scope=target_missing_schools_before_run`
- `dry_run=false`, `status=success`, and matching `current_fy`

Current FY2025 bounded smokes remain below this line and should be treated as
threshold-calibration evidence, not as release proof.

Windows-side R7 proof, if using the promoted v465 root:

```powershell
Set-Location (Join-Path $env:USERPROFILE "EIDP-v465-be32eb2")
$env:EIDP_TARGET_FISCAL_YEAR = "2025"
$env:EIDP_WEEKLY_CURRENT_FY = "2025"
try {
  .\scripts\weekly_run.bat
} finally {
  Remove-Item Env:\EIDP_TARGET_FISCAL_YEAR -ErrorAction SilentlyContinue
  Remove-Item Env:\EIDP_WEEKLY_CURRENT_FY -ErrorAction SilentlyContinue
}
```

Do not persist `EIDP_TARGET_FISCAL_YEAR=2025` in `.env`.

## Owner Cycle After Promotion

After v465 is active:

1. Double-click `EIDP-start.bat` from `%USERPROFILE%\EIDP-v465-be32eb2`.
2. Confirm the browser opens `http://127.0.0.1:8501`.
3. Confirm the UI shows `2026年度（令和8年度）`.
4. Run one owner/operator workflow through task review, PDF/manual review,
   fiscal-year correction, Excel preview/download, audit log, and outbox flush.
5. Run `EIDP-stage6-evidence.bat` and `EIDP-stage6-verify-evidence.bat`.
6. Complete `docs/runbooks/eidp-operator-e2e-template.md`.

For FY2026/R8 publication-lag misses, record measured KPI values and use the
explicit verifier exception only after owner acknowledges the exception:

```bash
uv run python scripts/verify_stage6_return.py \
  --e2e-template docs/runbooks/eidp-operator-e2e-template.md \
  --last-run logs/win-v465-real-cycle/last_run.json \
  --evidence-verify-json logs/win-v465-real-cycle/stage6-evidence-verify.json \
  --target-fy 2026 \
  --release-exception-reason publication_lag \
  --mature-year-proof-json logs/mature-year-acquisition-proof.json \
  --json
```

The exception does not allow null KPI values, `ship_gate_status=not_measured`,
missing mature-year proof, missing evidence labels, missing audit/outbox
evidence, or missing sign-off.

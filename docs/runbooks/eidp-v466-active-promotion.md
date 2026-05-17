# EIDP v466 Active-Promotion Runbook

Updated: 2026-05-17

This runbook prepares the clean v466 successor package for Windows
side-by-side validation and, only after explicit approval, active Scheduled
Task promotion. It is not approval to switch `EIDP Weekly Run` by itself.

## Why v466

The current active owner-cycle lane is still v460. The v460 URL-rich FY2026
weekly probe ran about 9h41m, wrote no fresh `data\output\last_run.json`, and
showed repeated shared-corporation HTTP crawling. v465 contains the cache/perf
source fix but was built before the current publication-lag, mature-year proof,
weekly progress, target-FY override, and local bug-report contracts were added.

v466 is the first clean successor package after those contracts were committed.

| Item | Value |
| --- | --- |
| Package | `dist/eidp-windows-v466.zip` |
| Package/source commit | `9a5d50b556484d89b30a2c349d5ee5b01ff0f195` |
| SHA256 | `8712c5b2687fa34de35c35a52b7df8bf8fe8f2ad82f153c30d24d551ac503db5` |
| BUILD_INFO | `git_dirty=false` |
| Target Windows root | `%USERPROFILE%\EIDP-v466-9a5d50b` |
| Active fallback | `%USERPROFILE%\EIDP-v460-01e4427` |

Keep v460 as fallback. Do not delete v460 data, logs, SQLite, audit JSONL, or
evidence bundles during v466 validation.

## Mac Evidence

Already completed on 2026-05-17:

```bash
uv run python scripts/download_windows_runtime.py
uv run python scripts/build_windows_zip.py --out-zip dist/eidp-windows-v466.zip
uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v466.zip --json
uv run python scripts/run_non_windows_release_gates.py \
  dist/eidp-windows-v466.zip \
  --skip-full-unit \
  --json \
  --output logs/release-gate-v466.json
```

Expected evidence:

- ZIP SHA256 matches the table above.
- `BUILD_INFO.json` records commit `9a5d50b...` and `git_dirty=false`.
- Distribution verifier returns `ok=true`.
- Non-Windows release gate returns `ok=true`.
- GitHub CI is green for the package source commit: push run `25990716165`
  and pull-request run `25990716814`.

## Windows Side-By-Side Preflight

Run from PowerShell on the operator PC after copying the ZIP and sidecar to
`C:\EIDP-staging`. This preflight may run `EIDP-setup.bat`, which rewrites the
scheduled task, so it backs up and restores the current task immediately.

```powershell
$zip = "C:\EIDP-staging\eidp-windows-v466.zip"
$expected = "8712c5b2687fa34de35c35a52b7df8bf8fe8f2ad82f153c30d24d551ac503db5"
$deployParent = $env:USERPROFILE
$root = Join-Path $deployParent "EIDP-v466-9a5d50b"
$fallbackRoot = Join-Path $deployParent "EIDP-v460-01e4427"
$fallbackAction = Join-Path $fallbackRoot "scripts\weekly_run.bat"
$taskName = "EIDP Weekly Run"
$backupXml = "C:\EIDP-staging\EIDP-Weekly-Run-before-v466-preflight.xml"

$actual = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $expected) { throw "SHA256 mismatch: $actual" }

schtasks /Query /TN "\EIDP Weekly Run" /XML |
  Set-Content -Path $backupXml -Encoding UTF8

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
    -Xml (Get-Content $backupXml | Out-String) `
    -Force

  Set-Location $fallbackRoot
  .\scripts\stage6_recovery_check.bat $fallbackAction
}
```

Expected restore evidence: `stage6_recovery_check.bat` returns `ok=true` and
`action_matches_expected=true` for the v460 fallback action.

Completed preflight evidence from 2026-05-17:

- Windows root: `%USERPROFILE%\EIDP-v466-9a5d50b`
- Setup rc: `0`
- `scripts\validate_install.bat --after-setup --json`: `ok=true`,
  `warnings=[]`, `errors=[]`
- `scripts\diagnose.bat`: rc `0`
- Restored task action:
  `%USERPROFILE%\EIDP-v460-01e4427\scripts\weekly_run.bat`
- Recovery JSON:
  `%USERPROFILE%\EIDP-v460-01e4427\logs\stage6-recovery-20260517-215355.json`
- Mac evidence copies:
  `logs/win-v466-stage6/v466-preflight-result-20260517-215028.json`,
  `logs/win-v466-stage6/v466-validate-install-after-setup-20260517-215028.json`,
  `logs/win-v466-stage6/stage6-recovery-20260517-215355.json`

## Active Task Switch

Approval boundary: this section changes external Windows state. Run it only
after explicit instruction to promote v466 to active.

```powershell
$taskName = "EIDP Weekly Run"
$backupXml = "C:\EIDP-staging\EIDP-Weekly-Run-before-v466-active.xml"
$root = Join-Path $env:USERPROFILE "EIDP-v466-9a5d50b"
$expectedAction = Join-Path $root "scripts\weekly_run.bat"

schtasks /Query /TN "\EIDP Weekly Run" /XML |
  Set-Content -Path $backupXml -Encoding UTF8

$action = New-ScheduledTaskAction `
  -Execute $expectedAction `
  -WorkingDirectory $root
Set-ScheduledTask -TaskName $taskName -Action $action

Set-Location $root
.\scripts\stage6_recovery_check.bat $expectedAction
```

Rollback:

```powershell
Register-ScheduledTask -TaskName "EIDP Weekly Run" `
  -Xml (Get-Content "C:\EIDP-staging\EIDP-Weekly-Run-before-v466-active.xml" | Out-String) `
  -Force
```

## Owner Cycle Gate

After v466 is active:

1. Double-click `%USERPROFILE%\EIDP-v466-9a5d50b\EIDP-start.bat`.
2. Confirm the browser UI opens and shows `2026年度（令和8年度）`.
3. Run the operator workflow through task review, PDF/manual review,
   fiscal-year correction, Excel preview/download, audit log, and outbox flush.
4. Run `EIDP-stage6-evidence.bat` and `EIDP-stage6-verify-evidence.bat`.
5. Fill `docs/runbooks/eidp-operator-e2e-template.md`.
6. Verify the return with `scripts/verify_stage6_return.py`.

For FY2026/R8 publication-lag misses, use
`--release-exception-reason publication_lag` only with measured KPI values and
a mature-year acquisition proof generated by
`scripts/build_mature_year_acquisition_proof.py`. The exception does not allow
null KPI values, `ship_gate_status=not_measured`, missing evidence labels,
missing audit/outbox evidence, or missing owner/operator sign-off.

# EIDP v494 Side-by-Side Validation Runbook

Updated: 2026-05-19

This runbook validates v494 on the Windows operator PC without promoting the
active `EIDP Weekly Run` scheduled task. It is not approval to tag v1.0 or to
switch the active lane.

## Package

| Item | Value |
| --- | --- |
| Package | `dist/eidp-windows-v494.zip` |
| SHA256 | `ea6d6884be27b5ff3408439bffc82eef7763158fa941f886afec94677da7724c` |
| Package/source commit | `0d693c6b9e36cda7bb61ba9750f9b8b2b90b1e32` |
| Target Windows root | `%USERPROFILE%\EIDP-v494-0d693c6` |
| Active lane to preserve | `%USERPROFILE%\EIDP-v485-70e3db4` |
| Retained fallback lane | `%USERPROFILE%\EIDP-v460-01e4427` |

Mac-side evidence already completed:

- `logs/win-v494-stage6-v494-verify-windows-distribution-20260519.json`
  returned `ok=true`.
- `logs/win-v494-stage6-v494-non-windows-release-gates-20260519.json`
  returned `ok=true` with package/source freshness.
- `logs/mature-year-acquisition-proof-fy2025-release-exception-v494-20260519.json`
  returned `ok=true`.

## Transfer

Copy these files to `C:\EIDP-staging\`:

- `dist/eidp-windows-v494.zip`
- `dist/eidp-windows-v494.zip.sha256`

Do not delete existing `EIDP-v485-70e3db4` or `EIDP-v460-01e4427` directories.

## Side-by-Side Setup

Run in Windows PowerShell:

```powershell
$zip = "C:\EIDP-staging\eidp-windows-v494.zip"
$expected = "ea6d6884be27b5ff3408439bffc82eef7763158fa941f886afec94677da7724c"
$root = Join-Path $env:USERPROFILE "EIDP-v494-0d693c6"
$activeRoot = Join-Path $env:USERPROFILE "EIDP-v485-70e3db4"
$activeAction = Join-Path $activeRoot "scripts\weekly_run.bat"

$actual = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $expected) { throw "SHA256 mismatch: $actual" }

if (-not (Test-Path $root)) {
  New-Item -ItemType Directory -Path $root | Out-Null
  Expand-Archive -Path $zip -DestinationPath $root
}

Set-Location $root
$env:EIDP_REGISTER_WEEKLY_TASK = "0"
.\EIDP-setup.bat
Remove-Item Env:\EIDP_REGISTER_WEEKLY_TASK -ErrorAction SilentlyContinue

.\scripts\validate_install.bat --after-setup --json |
  Tee-Object -FilePath "logs\win-v494-stage6-v494-validate-after-setup-20260519.json"

.\scripts\stage6_recovery_check.bat $activeAction --json |
  Tee-Object -FilePath "logs\win-v494-stage6-v494-recovery-expected-v485-20260519.json"
```

Expected:

- setup exits `0`;
- `validate_install.bat --after-setup --json` returns `ok=true`;
- recovery check returns `ok=true` and `action_matches_expected=true`;
- active scheduled task still points to v485.

## UI Smoke

Run Streamlit side-by-side on a temporary port, not the active UI port:

```powershell
Set-Location $root
$env:EIDP_APP_ROOT = $root
$env:PYTHONPATH = "$root\src;$env:PYTHONPATH"
.\.venv\Scripts\python.exe -m streamlit run `
  "$root\src\eidp\review\app.py" `
  --server.address 127.0.0.1 `
  --server.port 8517 `
  --server.headless true `
  --browser.gatherUsageStats false
```

In another PowerShell window:

```powershell
Invoke-WebRequest http://127.0.0.1:8517/_stcore/health -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:8517/ -UseBasicParsing
```

Expected:

- health endpoint returns `200` / `ok`;
- root page returns `200`;
- no traceback is printed in the Streamlit console;
- the temporary listener is stopped after the smoke.

## Promotion Boundary

Stop after the side-by-side setup and UI smoke. Do not switch `EIDP Weekly Run`
to v494 unless release scope is explicitly decided and owner E2E is scheduled.

Current release blockers:

- FY2026/R8 strict current-FY yield remains below gate.
- v494 Windows side-by-side evidence is not complete until this runbook passes.
- Owner real cycle and sign-off are still required.
- If the `publication_lag` exception path is chosen, the completed owner return
  must be verified with `scripts/verify_stage6_return.py` and
  `logs/mature-year-acquisition-proof-fy2025-release-exception-v494-20260519.json`.

# EIDP v420 Windows Transfer Checklist

Updated: 2026-05-15
Status: ready for SSH-Win recovery / not executed on Windows

Use this checklist when SSH-Win is available again. It is intentionally scoped
to v420 and should not be used as evidence by itself; evidence starts only after
the Windows SHA check, setup, UI health check, retroactive dry-run, and Stage 6
bundle verification have actually run.

## Package

| Field | Value |
| --- | --- |
| ZIP | `dist/eidp-windows-v420.zip` |
| SHA256 sidecar | `dist/eidp-windows-v420.zip.sha256` |
| Expected SHA256 | `5585d303b97de1f29af3737a7c1fcd614eb5c23b51307fb2af57988612740de8` |
| Package commit | `99efba8a798d76611896be22e36abbb125a5eb71` |
| Optional local manifest | `dist/eidp-windows-v420-transfer-manifest.json` |
| Suggested staging path | `C:\EIDP-staging\` |
| Suggested extract path | `C:\Users\cyo20\EIDP-v420-99efba8a` |

## Mac Preflight

Run this before transfer:

```bash
shasum -a 256 -c dist/eidp-windows-v420.zip.sha256
if [ -f dist/eidp-windows-v420-transfer-manifest.json ]; then
  python -m json.tool dist/eidp-windows-v420-transfer-manifest.json >/dev/null
fi
uv run python scripts/run_non_windows_release_gates.py \
  dist/eidp-windows-v420.zip \
  --skip-full-unit \
  --allow-docs-only-stale-package \
  --json \
  --output logs/release-gate-v420-docs-only-stale-before-windows-transfer.json
```

Expected:

- `shasum` reports `dist/eidp-windows-v420.zip: OK`.
- release gate reports `ok=true`.
- `package_source_check.docs_only_stale=true` is acceptable only when changed
  paths are docs/runbooks/status files.
- Any tracked non-doc source change means rebuild a new ZIP instead of
  transferring v420.

## Transfer

Create staging directory and copy the ZIP plus sidecar:

```bash
ssh win 'powershell -NoProfile -Command "New-Item -ItemType Directory -Force C:\EIDP-staging | Out-Null"'
scp dist/eidp-windows-v420.zip dist/eidp-windows-v420.zip.sha256 win:C:/EIDP-staging/
```

If `scp` path handling fails on Windows OpenSSH, use `sftp win` and upload both
files to `C:\EIDP-staging\`.

## Windows SHA Check

Run in Windows PowerShell:

```powershell
$Expected = "5585d303b97de1f29af3737a7c1fcd614eb5c23b51307fb2af57988612740de8"
$Zip = "C:\EIDP-staging\eidp-windows-v420.zip"
$Actual = (Get-FileHash -Algorithm SHA256 $Zip).Hash.ToLowerInvariant()
if ($Actual -ne $Expected) {
    throw "SHA256 mismatch: expected=$Expected actual=$Actual"
}
"SHA256 OK: $Actual"
```

Optional `certutil` cross-check:

```powershell
certutil -hashfile C:\EIDP-staging\eidp-windows-v420.zip SHA256
```

Do not extract if the digest differs.

## Extract

Use a fresh directory unless the owner explicitly chooses a different staging
path:

```powershell
$Zip = "C:\EIDP-staging\eidp-windows-v420.zip"
$Dest = "C:\Users\cyo20\EIDP-v420-99efba8a"
if (Test-Path $Dest) {
    throw "Destination already exists: $Dest"
}
Expand-Archive -LiteralPath $Zip -DestinationPath $Dest
Get-ChildItem $Dest | Select-Object Name
```

Expected root files include:

- `EIDP-setup.bat`
- `EIDP-start.bat`
- `EIDP-diagnose.bat`
- `EIDP-stage6-evidence.bat`
- `EIDP-stage6-verify-evidence.bat`
- `scripts\first_setup.bat`
- `scripts\launch.bat`
- `scripts\weekly_run.bat`

## Setup

Prefer the root launcher:

```powershell
Set-Location "C:\Users\cyo20\EIDP-v420-99efba8a"
.\EIDP-setup.bat
```

After setup, validate:

```powershell
.\.venv\Scripts\python.exe scripts\validate_windows_install.py --after-setup --json
```

Expected:

- setup exits `0`
- SQLite integrity check is `ok`
- `school_count` and `school_fiscal_year_status_count` are populated
- scheduled task points to this v420 extraction unless intentionally skipped

## UI Health

Start the default launcher on Windows:

```powershell
Set-Location "C:\Users\cyo20\EIDP-v420-99efba8a"
.\EIDP-start.bat
```

For Mac-side tunnel verification:

```bash
ssh -N -o ClearAllForwardings=no -o ExitOnForwardFailure=yes \
  -L 127.0.0.1:18501:127.0.0.1:8501 win
curl http://127.0.0.1:18501/_stcore/health
```

Expected health response: `ok`.

## Retroactive Stage 6 Dry-Run

Use process-local `EIDP_TARGET_FISCAL_YEAR=2025` only. Do not write it to
`.env`.

```powershell
Set-Location "C:\Users\cyo20\EIDP-v420-99efba8a"
$env:EIDP_TARGET_FISCAL_YEAR = "2025"
.\scripts\weekly_run.bat
Remove-Item Env:\EIDP_TARGET_FISCAL_YEAR
```

Then collect:

- `logs\run-*.log`
- `data\output\last_run.json`
- generated Excel output path, if any
- audit outbox status
- screenshots or notes for the operator click-through

## Evidence Bundle

Build and verify the bundle on Windows:

```powershell
Set-Location "C:\Users\cyo20\EIDP-v420-99efba8a"
.\EIDP-stage6-evidence.bat
.\EIDP-stage6-verify-evidence.bat
```

Pull the bundle back to Mac and verify again:

```bash
scp win:C:/Users/cyo20/EIDP-v420-99efba8a/logs/stage6-evidence-*.zip logs/
uv run python scripts/verify_stage6_evidence.py logs/stage6-evidence-*.zip --json
```

Record the verified bundle path and verifier JSON in
`docs/runbooks/eidp-operator-e2e-template.md` and
`docs/reports/eidp-v420-stage6-evidence-draft.md`.

## Red Lines

- Do not edit code on Windows. Fixes must be Mac TDD -> new ZIP -> Windows
  verification.
- Do not delete `data\eidp.sqlite3`, `data\audit\manual-actions.jsonl`, or
  `data\master.xlsx`.
- Do not skip SHA256 verification.
- Do not overwrite v408 or any existing runtime without backing up data, audit,
  and DB files.
- Do not run `uninstall.bat` for this validation lane.
- Do not count Mac gates, retroactive Excel gates, or copied-DB smokes as real
  operator-PC Stage 6 completion.

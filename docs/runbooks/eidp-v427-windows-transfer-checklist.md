# EIDP v427 Windows Transfer Checklist

Updated: 2026-05-15
Status: ready for SSH-Win recovery or manual transfer / not executed on Windows

Use this checklist when SSH-Win is available again, or when the operator can
manually move the package through a USB drive or trusted internal file share. It
is intentionally scoped to v427 and should not be used as evidence by itself;
evidence starts only after the Windows SHA check, setup, UI health check,
retroactive dry-run, and Stage 6 bundle verification have actually run.

## Package

| Field | Value |
| --- | --- |
| ZIP | `dist/eidp-windows-v427.zip` |
| SHA256 sidecar | `dist/eidp-windows-v427.zip.sha256` |
| Expected SHA256 | `33d4f44e0f0027ba32598344484d89cd6100ec472b2d9d8bf4b04bd66e3a8aeb` |
| Package commit | `2154aeecf04769c6bd1ee38b590468919ce5043b` |
| Optional local manifest | `dist/eidp-windows-v427-transfer-manifest.json` |
| Suggested staging path | `C:\EIDP-staging\` |
| Suggested extract path | `C:\Users\cyo20\EIDP-v427-2154aeec` |

## Companion Docs

The v427 ZIP contains the packaged Windows app and the reusable operator E2E
template. This version-specific transfer checklist and the evidence draft are
companion documents outside the ZIP. Carry or print these current repo documents
alongside the ZIP and SHA sidecar:

- `docs/runbooks/eidp-v427-windows-transfer-checklist.md`
- `docs/runbooks/eidp-operator-e2e-template.md`
- `docs/reports/eidp-v427-stage6-evidence-draft.md`

Use the ZIP-embedded `docs/runbooks/eidp-operator-e2e-template.md` as the blank
recording form. Copy v427 package, SHA256, gate, and Windows execution values
from this checklist or `docs/reports/current-release-status.md` only when
filling the template after execution. Do not prefill the packaged reusable
template before building a ZIP.

## Mac Preflight

Run this before transfer:

```bash
shasum -a 256 -c dist/eidp-windows-v427.zip.sha256
if [ -f dist/eidp-windows-v427-transfer-manifest.json ]; then
  python -m json.tool dist/eidp-windows-v427-transfer-manifest.json >/dev/null
fi
uv run python scripts/run_non_windows_release_gates.py \
  dist/eidp-windows-v427.zip \
  --skip-full-unit \
  --allow-docs-only-stale-package \
  --json \
  --output logs/release-gate-v427-docs-only-stale-before-windows-transfer.json
```

Expected:

- `shasum` reports `dist/eidp-windows-v427.zip: OK`.
- release gate reports `ok=true`.
- `package_source_check.docs_only_stale=true` is acceptable only when changed
  paths are docs/runbooks/status files.
- Any tracked non-doc source change means rebuild a new ZIP instead of
  transferring v427.

## Transfer

### Option A: SSH / SCP

Create staging directory and copy the ZIP plus sidecar:

```bash
ssh win 'powershell -NoProfile -Command "New-Item -ItemType Directory -Force C:\EIDP-staging | Out-Null"'
scp dist/eidp-windows-v427.zip dist/eidp-windows-v427.zip.sha256 win:C:/EIDP-staging/
```

If `scp` path handling fails on Windows OpenSSH, use `sftp win` and upload both
files to `C:\EIDP-staging\`.

### Option B: No-SSH Manual Transfer

Use this path when SSH-Win is disconnected. Copy exactly these two files from
Mac to a USB drive or trusted internal file share:

- `dist/eidp-windows-v427.zip`
- `dist/eidp-windows-v427.zip.sha256`

On Windows, copy both files into the staging directory before running the SHA
check:

```powershell
New-Item -ItemType Directory -Force C:\EIDP-staging | Out-Null
$Source = "<USB_OR_SHARE_PATH>"
Copy-Item -LiteralPath (Join-Path $Source "eidp-windows-v427.zip") -Destination "C:\EIDP-staging\eidp-windows-v427.zip"
Copy-Item -LiteralPath (Join-Path $Source "eidp-windows-v427.zip.sha256") -Destination "C:\EIDP-staging\eidp-windows-v427.zip.sha256"
Get-ChildItem C:\EIDP-staging\eidp-windows-v427.zip*
```

Manual transfer is acceptable only if the next Windows SHA check matches the
expected digest below. Do not extract from the USB/share path directly; extract
from `C:\EIDP-staging\` after the digest check passes.

## Windows SHA Check

Run in Windows PowerShell:

```powershell
$Expected = "33d4f44e0f0027ba32598344484d89cd6100ec472b2d9d8bf4b04bd66e3a8aeb"
$Zip = "C:\EIDP-staging\eidp-windows-v427.zip"
$Actual = (Get-FileHash -Algorithm SHA256 $Zip).Hash.ToLowerInvariant()
if ($Actual -ne $Expected) {
    throw "SHA256 mismatch: expected=$Expected actual=$Actual"
}
"SHA256 OK: $Actual"
```

Optional `certutil` cross-check:

```powershell
certutil -hashfile C:\EIDP-staging\eidp-windows-v427.zip SHA256
```

Do not extract if the digest differs.

## Extract

Use a fresh directory unless the owner explicitly chooses a different staging
path:

```powershell
$Zip = "C:\EIDP-staging\eidp-windows-v427.zip"
$Dest = "C:\Users\cyo20\EIDP-v427-2154aeec"
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
Set-Location "C:\Users\cyo20\EIDP-v427-2154aeec"
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
- scheduled task points to this v427 extraction unless intentionally skipped

## UI Health

Start the default launcher on Windows:

```powershell
Set-Location "C:\Users\cyo20\EIDP-v427-2154aeec"
.\EIDP-start.bat
```

For Mac-side tunnel verification:

```bash
ssh -N -o ClearAllForwardings=no -o ExitOnForwardFailure=yes \
  -L 127.0.0.1:18501:127.0.0.1:8501 win
curl http://127.0.0.1:18501/_stcore/health
```

Expected health response: `ok`.

The packaged launchers are expected to bind Streamlit to `127.0.0.1` only. Do
not expose the unauthenticated operator UI on `0.0.0.0` or a LAN interface.

## Retroactive Stage 6 Dry-Run

Use process-local `EIDP_TARGET_FISCAL_YEAR=2025` only. Do not write it to
`.env`.

```powershell
Set-Location "C:\Users\cyo20\EIDP-v427-2154aeec"
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
Set-Location "C:\Users\cyo20\EIDP-v427-2154aeec"
.\EIDP-stage6-evidence.bat
.\EIDP-stage6-verify-evidence.bat
```

Pull the bundle back to Mac and verify again:

```bash
scp win:C:/Users/cyo20/EIDP-v427-2154aeec/logs/stage6-evidence-*.zip logs/
latest_bundle="$(ls -t logs/stage6-evidence-*.zip | head -n 1)"
test -n "$latest_bundle" || { echo "No logs/stage6-evidence-*.zip found"; exit 1; }
verify_json="logs/stage6-evidence-verify-mac-v427-$(date +%Y%m%d-%H%M%S).json"
uv run python scripts/verify_stage6_evidence.py "$latest_bundle" --json --require-label last_run > "$verify_json"
printf 'verified %s -> %s\n' "$latest_bundle" "$verify_json"
```

If SSH-Win is still disconnected, copy the newest Windows files below to USB or
a trusted internal file share, then place them under the Mac repo's `logs/`
directory before running the same Mac verifier snippet above:

- `C:\Users\cyo20\EIDP-v427-2154aeec\logs\stage6-evidence-*.zip`
- `C:\Users\cyo20\EIDP-v427-2154aeec\logs\stage6-evidence-verify-*.json`
- `C:\Users\cyo20\EIDP-v427-2154aeec\logs\run-*.log`
- `C:\Users\cyo20\EIDP-v427-2154aeec\data\output\last_run.json`

Record the verified bundle path and verifier JSON in
`docs/runbooks/eidp-operator-e2e-template.md` and
`docs/reports/eidp-v427-stage6-evidence-draft.md`.

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

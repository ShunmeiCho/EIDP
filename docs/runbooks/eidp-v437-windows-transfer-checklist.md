# EIDP v437 Windows Transfer Checklist

Updated: 2026-05-15
Status: ready for SSH-Win recovery or manual transfer / not executed on Windows

Use this checklist when SSH-Win is available again, or when the operator can
manually move the package through a USB drive or trusted internal file share. It
is scoped to v437 and is not evidence by itself; evidence starts only after the
Windows SHA check, setup, UI health check, retroactive dry-run, and Stage 6
bundle verification have actually run.

## Package

| Field | Value |
| --- | --- |
| ZIP | `dist/eidp-windows-v437.zip` |
| SHA256 sidecar | `dist/eidp-windows-v437.zip.sha256` |
| Expected SHA256 | `ed0d677fd2d36f7bd9f884185412180a6764beef9632543e5e36eb3c766ed33c` |
| Package commit | `7553c7480a001a1ebec687dcb743c8bd9529d6d4` |
| Suggested staging path | `C:\EIDP-staging\` |
| Suggested extract path | `C:\Users\cyo20\EIDP-v437-7553c748` |

## Companion Docs

Carry or print these current repo documents alongside the ZIP and SHA sidecar:

- `docs/runbooks/eidp-v437-windows-transfer-checklist.md`
- `docs/runbooks/eidp-operator-e2e-template.md`
- `docs/reports/eidp-v437-stage6-evidence-draft.md`

Use the ZIP-embedded `docs/runbooks/eidp-operator-e2e-template.md` as the blank
recording form. Copy v437 package, SHA256, gate, and Windows execution values
from this checklist or `docs/reports/current-release-status.md` only when
filling the template after execution.

## Mac Preflight

Run this before transfer:

```bash
shasum -a 256 -c dist/eidp-windows-v437.zip.sha256
uv run python scripts/run_non_windows_release_gates.py \
  dist/eidp-windows-v437.zip \
  --skip-full-unit \
  --allow-docs-only-stale-package \
  --json \
  --output logs/release-gate-v437-docs-only-stale-before-windows-transfer.json
```

Expected:

- `shasum` reports `dist/eidp-windows-v437.zip: OK`.
- release gate reports `ok=true`.
- `package_source_check.docs_only_stale=true` is acceptable only when changed
  paths are docs/runbooks/status files.
- Any tracked non-doc source change means rebuild a new ZIP instead of
  transferring v437.

## Transfer

### Option A: SSH / SCP

```bash
ssh win 'powershell -NoProfile -Command "New-Item -ItemType Directory -Force C:\EIDP-staging | Out-Null"'
scp dist/eidp-windows-v437.zip dist/eidp-windows-v437.zip.sha256 win:C:/EIDP-staging/
```

If `scp` path handling fails on Windows OpenSSH, use `sftp win` and upload both
files to `C:\EIDP-staging\`.

### Option B: No-SSH Manual Transfer

Use this path while SSH-Win is disconnected. Copy exactly these two files from
Mac to a USB drive or trusted internal file share:

- `dist/eidp-windows-v437.zip`
- `dist/eidp-windows-v437.zip.sha256`

On Windows, copy both files into the staging directory before running the SHA
check:

```powershell
New-Item -ItemType Directory -Force C:\EIDP-staging | Out-Null
$Source = "<USB_OR_SHARE_PATH>"
Copy-Item -LiteralPath (Join-Path $Source "eidp-windows-v437.zip") -Destination "C:\EIDP-staging\eidp-windows-v437.zip"
Copy-Item -LiteralPath (Join-Path $Source "eidp-windows-v437.zip.sha256") -Destination "C:\EIDP-staging\eidp-windows-v437.zip.sha256"
Get-ChildItem C:\EIDP-staging\eidp-windows-v437.zip*
```

Manual transfer is acceptable only if the next Windows SHA check matches the
expected digest. Do not extract from the USB/share path directly; extract from
`C:\EIDP-staging\` after the digest check passes.

## Windows SHA Check

Run in Windows PowerShell:

```powershell
$Expected = "ed0d677fd2d36f7bd9f884185412180a6764beef9632543e5e36eb3c766ed33c"
$Zip = "C:\EIDP-staging\eidp-windows-v437.zip"
$Actual = (Get-FileHash -Algorithm SHA256 $Zip).Hash.ToLowerInvariant()
if ($Actual -ne $Expected) {
    throw "SHA256 mismatch: expected=$Expected actual=$Actual"
}
"SHA256 OK: $Actual"
```

Optional `certutil` cross-check:

```powershell
certutil -hashfile C:\EIDP-staging\eidp-windows-v437.zip SHA256
```

## Extract And Setup

```powershell
$Zip = "C:\EIDP-staging\eidp-windows-v437.zip"
$Dest = "C:\Users\cyo20\EIDP-v437-7553c748"
New-Item -ItemType Directory -Force $Dest | Out-Null
Expand-Archive -LiteralPath $Zip -DestinationPath $Dest -Force
Set-Location $Dest
.\EIDP-setup.bat
```

Do not delete existing `data\`, `logs\`, `output\`, `master.xlsx`, or
`manual-actions.jsonl` from any prior lane. Back them up before replacing an
active operator path.

## Launch And Stage 6

```powershell
Set-Location "C:\Users\cyo20\EIDP-v437-7553c748"
.\EIDP-start.bat
```

Confirm Streamlit opens on `127.0.0.1:8501`, then run the operator E2E template
checks. For the retroactive dry-run, set `EIDP_TARGET_FISCAL_YEAR=2025` only in
the process environment; do not persist it into `.env`.

After the dry-run:

```powershell
Set-Location "C:\Users\cyo20\EIDP-v437-7553c748"
.\EIDP-stage6-evidence.bat
.\EIDP-stage6-verify-evidence.bat
```

Expected evidence to copy back to Mac:

- `logs\stage6-evidence-*.zip`
- `logs\stage6-evidence-verify-*.json`
- `logs\run-*.log`
- `logs\eidp.jsonl`
- `data\output\last_run.json`

Fill `docs/runbooks/eidp-operator-e2e-template.md` and
`docs/reports/eidp-v437-stage6-evidence-draft.md` only after the Windows run
has produced real values.

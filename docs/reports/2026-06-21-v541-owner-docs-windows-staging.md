# v541 Owner Docs Windows Staging

Date: 2026-06-21

## Scope

This follow-up stages the v541 owner/operator handoff docs on the Windows
operator host. It refreshes the owner-facing handoff from v540 to v541 package
identity:

- `docs/runbooks/00-READ-ME-FIRST-v541.txt`
- `docs/runbooks/eidp-v541-release-summary.md`
- `docs/runbooks/eidp-v541-owner-signoff.md`
- `docs/runbooks/eidp-v541-owner-request-20260621.txt`
- `docs/runbooks/eidp-v541-owner-return-fill-sheet.md`

This is a docs-only handoff update. It did not modify the active runtime,
SQLite DB, PDFs, audit JSONL, Excel files, or Task Scheduler registration.

## Transfer Evidence

| Check | Evidence |
| --- | --- |
| Docs ZIP | `C:\EIDP-staging\eidp-v541-owner-docs-20260621.zip` |
| ZIP SHA256 | `4ab692e47c0077eaedac91f340a561507ebaac79277bdce9db17d28ceea6c731` |
| ZIP SHA256 sidecar | `C:\EIDP-staging\eidp-v541-owner-docs-20260621.zip.sha256` present and contains the expected ZIP hash |
| Extracted destination | `C:\EIDP-staging\v541-owner-docs-20260621` |
| First-read handoff | `docs\runbooks\00-READ-ME-FIRST-v541.txt` present |
| One-page release summary | `docs\runbooks\eidp-v541-release-summary.md` present |
| Short owner sign-off | `docs\runbooks\eidp-v541-owner-signoff.md` present |
| Owner request | `docs\runbooks\eidp-v541-owner-request-20260621.txt` present |
| Owner return fill sheet | `docs\runbooks\eidp-v541-owner-return-fill-sheet.md` present |
| Current release status | `docs\reports\current-release-status.md` present and contains `NOT_READY` |
| Publication-lag exception record | `docs\reports\2026-05-19-publication-lag-release-exception-record.md` present and contains `NOT_APPROVED` |

## Remote Verification Output

```text
expected sha: 4AB692E47C0077EAEDAC91F340A561507EBAAC79277BDCE9DB17D28CEEA6C731
actual sha:   4AB692E47C0077EAEDAC91F340A561507EBAAC79277BDCE9DB17D28CEEA6C731
docs\runbooks\00-READ-ME-FIRST-v541.txt present: True
docs\runbooks\eidp-v541-release-summary.md present: True
docs\runbooks\eidp-v541-owner-signoff.md present: True
docs\runbooks\eidp-v541-owner-request-20260621.txt present: True
docs\runbooks\eidp-v541-owner-return-fill-sheet.md present: True
docs\reports\current-release-status.md present: True
docs\reports\2026-05-19-publication-lag-release-exception-record.md present: True
current-release-status NOT_READY: True
owner-signoff short-form marker: True
publication-lag NOT_APPROVED: True
scheduled task execute: ""C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat""
old v540 zip exists: False
old v540 dir exists: False
sidecar exists: True
sidecar content: 4ab692e47c0077eaedac91f340a561507ebaac79277bdce9db17d28ceea6c731  dist/eidp-v541-owner-docs-20260621.zip
sidecar has expected sha: True
```

## Local Cleanup

The generated v541 owner-docs ZIP and sidecar are retained in the
external-SSD-backed `dist/` directory as the current handoff transfer artifact:

```text
dist/eidp-v541-owner-docs-20260621.zip
dist/eidp-v541-owner-docs-20260621.zip.sha256
```

No superseded v540 owner-docs ZIP/sidecar or macOS AppleDouble `._*` sidecars
were present in `dist/` after staging. Current external SSD artifact usage:

```text
/Volumes/M1nG-ssd/EIDP-artifacts/dist  1.3G
/Volumes/M1nG-ssd/EIDP-artifacts/logs  1.2G
```

## Safety Recheck

The Windows `EIDP Weekly Run` Scheduled Task still executes:

```text
C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat
```

This confirms the staging step was a docs-only handoff update. It does not
approve v1.0, does not switch the active production lane, and does not replace
the missing owner real Windows cycle, returned KPI/sign-off evidence, approved
`publication_lag` decision, or OCR scope decision.

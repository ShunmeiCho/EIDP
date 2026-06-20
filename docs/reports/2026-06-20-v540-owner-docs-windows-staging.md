# v540 Owner Docs Windows Staging

Date: 2026-06-20

## Scope

The v540 owner/operator handoff docs were packaged on macOS and staged on the
Windows operator host under `C:\EIDP-staging`. This copied documentation only.
It did not modify the active runtime, SQLite DB, PDFs, audit JSONL, Excel
files, or Task Scheduler registration.

## Transfer Evidence

| Check | Evidence |
| --- | --- |
| Docs ZIP | `C:\EIDP-staging\eidp-v540-owner-docs-20260620.zip` |
| ZIP SHA256 | `219f0c4fe0e26073236e74a83fb92126898f885324666bea96a69fcb167afa5a` |
| ZIP SHA256 sidecar | `C:\EIDP-staging\eidp-v540-owner-docs-20260620.zip.sha256` present and matches the ZIP hash |
| Extracted destination | `C:\EIDP-staging\v540-owner-docs-20260620` |
| First-read handoff | `docs\runbooks\00-READ-ME-FIRST-v540.txt` present |
| Owner request | `docs\runbooks\eidp-v540-owner-request-20260620.txt` present |
| Owner return fill sheet | `docs\runbooks\eidp-v540-owner-return-fill-sheet.md` present |
| v540 Windows canary report | `docs\reports\2026-06-20-v540-owner-briefs-windows-canary.md` present |
| Current release status | `docs\reports\current-release-status.md` present and contains `NOT_READY` |
| Publication-lag exception record | `docs\reports\2026-05-19-publication-lag-release-exception-record.md` present and contains `NOT_APPROVED` |

## Safety Recheck

After staging, the Windows `EIDP Weekly Run` Scheduled Task still executes:

```text
C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat
```

The active v527 root and side-by-side v540 root were both present:

- `C:\Users\cyo20\EIDP-v527-69fe81f-env0`
- `C:\Users\cyo20\EIDP-v540-fbdd0bd-env0`

The staging checks returned:

```text
docs/runbooks/00-READ-ME-FIRST-v540.txt present: True
docs/runbooks/eidp-v540-owner-request-20260620.txt present: True
docs/runbooks/eidp-v540-owner-return-fill-sheet.md present: True
current-release-status.md contains NOT_READY: True
publication-lag exception record contains NOT_APPROVED: True
v540 docs ZIP SHA256: 219f0c4fe0e26073236e74a83fb92126898f885324666bea96a69fcb167afa5a
v540 root exists: True
v527 root exists: True
scheduled task execute: "C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat"
```

This confirms the staging step was a docs-only handoff update. It does not
approve v1.0 and does not replace the missing owner real Windows cycle,
returned KPI/sign-off evidence, approved `publication_lag` decision, or OCR
scope decision.

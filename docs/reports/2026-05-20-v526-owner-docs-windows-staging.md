# v526 Owner Docs Windows Staging

Date: 2026-05-20

## Scope

The v526 owner/operator handoff docs were packaged on macOS and staged on the
Windows operator host under `C:\EIDP-staging`. This copied documentation only.
It did not modify the active runtime, SQLite DB, PDFs, audit JSONL, Excel
files, or Task Scheduler registration.

## Transfer Evidence

| Check | Evidence |
| --- | --- |
| Docs ZIP | `C:\EIDP-staging\eidp-v526-owner-docs-20260520.zip` |
| ZIP SHA256 | `ee7d26f76de17291904f2f27ba899737b7117cd4916010cb512a43ba61910573` |
| ZIP SHA256 sidecar | `C:\EIDP-staging\eidp-v526-owner-docs-20260520.zip.sha256` present and matches the ZIP hash |
| Extracted destination | `C:\EIDP-staging\v526-owner-docs-20260520` |
| First-read handoff | `docs\runbooks\00-READ-ME-FIRST-v526.txt` present |
| Owner request | `docs\runbooks\eidp-v526-owner-request-20260520.txt` present |
| Package report | `docs\reports\2026-05-20-v526-extracted-confirmation-package.md` present |
| Post-reboot active-task preflight | `docs\reports\2026-05-20-v526-post-reboot-active-task-preflight.md` present |

## Safety Recheck

After staging, the Windows `EIDP Weekly Run` Scheduled Task still executes:

```text
C:\Users\cyo20\EIDP-v485-70e3db4\scripts\weekly_run.bat
```

The active v485 root and side-by-side v526 root were both present:

- `C:\Users\cyo20\EIDP-v485-70e3db4`
- `C:\Users\cyo20\EIDP-v526-5b30eb7-env0`

This confirms the staging step was a docs-only handoff update.

## Refresh Note

The owner docs ZIP was refreshed after the post-reboot active-task preflight so
the Windows-staged owner request and objective checklist include the finding
that active v485 is only a no-accidental-promotion boundary and is not healthy
v1.0 release evidence. The exact ZIP SHA256 is recorded in this external
staging report rather than inside the owner docs ZIP to avoid a
self-referential hash.

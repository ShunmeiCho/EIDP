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
| ZIP SHA256 | `a730947fe77029991463336b4376648f1c1c9900995e8adebac3a189322506f4` |
| Extracted destination | `C:\EIDP-staging\v526-owner-docs-20260520` |
| First-read handoff | `docs\runbooks\00-READ-ME-FIRST-v526.txt` present |
| Owner request | `docs\runbooks\eidp-v526-owner-request-20260520.txt` present |
| Package report | `docs\reports\2026-05-20-v526-extracted-confirmation-package.md` present |

## Safety Recheck

After staging, the Windows `EIDP Weekly Run` Scheduled Task still executes:

```text
C:\Users\cyo20\EIDP-v485-70e3db4\scripts\weekly_run.bat
```

The active v485 root and side-by-side v526 root were both present:

- `C:\Users\cyo20\EIDP-v485-70e3db4`
- `C:\Users\cyo20\EIDP-v526-5b30eb7-env0`

This confirms the staging step was a docs-only handoff update.

# v535 Owner Docs Windows Staging

Date: 2026-06-20

## Scope

The v535 owner/operator handoff docs were packaged on macOS and staged on the
Windows operator host under `C:\EIDP-staging`. This copied documentation only.
It did not modify the active runtime, SQLite DB, PDFs, audit JSONL, Excel
files, or Task Scheduler registration.

## Transfer Evidence

| Check | Evidence |
| --- | --- |
| Docs ZIP | `C:\EIDP-staging\eidp-v535-owner-docs-20260620.zip` |
| ZIP SHA256 | `75d4d4f12ca5a10abc6d1ac1d6c7287f6cc51e47a210c73ee68b7f252f79f5ca` |
| ZIP SHA256 sidecar | `C:\EIDP-staging\eidp-v535-owner-docs-20260620.zip.sha256` present and matches the ZIP hash |
| Extracted destination | `C:\EIDP-staging\v535-owner-docs-20260620` |
| First-read handoff | `docs\runbooks\00-READ-ME-FIRST-v535.txt` present and references the v535 owner return fill sheet |
| Owner request | `docs\runbooks\eidp-v535-owner-request-20260620.txt` present |
| Owner return fill sheet | `docs\runbooks\eidp-v535-owner-return-fill-sheet.md` present |
| v535 Windows smoke report | `docs\reports\2026-06-20-v535-full-windows-side-by-side-smoke.md` present |
| Current release status | `docs\reports\current-release-status.md` present and contains `NOT_READY` |
| Publication-lag exception record | `docs\reports\2026-05-19-publication-lag-release-exception-record.md` present and contains `NOT_APPROVED` |
| Remote check JSON | `C:\EIDP-staging\v535-owner-docs-20260620-staging-check.json` returned `ok=true` |

## Safety Recheck

After staging, the Windows `EIDP Weekly Run` Scheduled Task still executes:

```text
C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat
```

The active v527 root and side-by-side v535 root were both present:

- `C:\Users\cyo20\EIDP-v527-69fe81f-env0`
- `C:\Users\cyo20\EIDP-v535-d742327-env0`

The staging verification returned:

```text
ok=true
sidecar_matches=true
first_read_mentions_return_sheet=true
current_status_mentions_not_ready=true
publication_exception_mentions_not_approved=true
scheduled_task_still_v527=true
v527_root_exists=true
v535_root_exists=true
```

This confirms the staging step was a docs-only handoff update. It does not
approve v1.0 and does not replace the missing owner real Windows cycle,
returned KPI/sign-off evidence, approved `publication_lag` decision, or OCR
scope decision.

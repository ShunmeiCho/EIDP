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
| ZIP SHA256 | `f8bd3933a2a5a690befe172237a1027954e73fa604006dec5784f368460ca8f9` |
| ZIP SHA256 sidecar | `C:\EIDP-staging\eidp-v526-owner-docs-20260520.zip.sha256` present and matches the ZIP hash |
| Extracted destination | `C:\EIDP-staging\v526-owner-docs-20260520` |
| First-read handoff | `docs\runbooks\00-READ-ME-FIRST-v526.txt` present |
| Owner request | `docs\runbooks\eidp-v526-owner-request-20260520.txt` present |
| Windows runbook | `docs\runbooks\eidp-windows.md` present, including `10.209.*` and standard proxy environment-variable guidance |
| Owner-return remote check | `docs\reports\2026-05-20-v526-owner-return-remote-check.md` present |
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

It was refreshed again after the campus-network guidance update so the
Windows-staged owner docs include `10.x` private campus subnet guidance,
including `10.209.*`, and the standard `HTTP_PROXY` / `HTTPS_PROXY` /
`NO_PROXY` path for outbound PDF discovery behind a campus proxy. The refresh
copied documentation only; the active weekly task still points to v485.

It was refreshed a third time after the owner-return remote check so the
Windows-staged handoff now includes
`docs\reports\2026-05-20-v526-owner-return-remote-check.md`. Remote staging
verification returned `ok=true`, `owner_return_remote_check=true`,
`has_10209=true`, `has_proxy_guidance=true`, and the active weekly task still
points to v485.

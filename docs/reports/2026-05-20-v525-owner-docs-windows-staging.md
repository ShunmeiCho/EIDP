# v525 Owner Docs Windows Staging

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
Scope: owner/operator handoff docs only

## Purpose

Place the v525 owner/operator handoff documents on the Windows machine under
`C:\EIDP-staging` without touching the active v485 runtime, the v525
side-by-side app root, database files, or Task Scheduler.

## Mac Artifact

```text
_temp/v525-owner-docs-20260520.zip
```

SHA256:

```text
5b66839c24dd73a68092f823a584475a44779be1f1ae59947284f81af6dab4bb
```

Contents:

```text
docs/runbooks/00-READ-ME-FIRST-v525.txt
docs/runbooks/eidp-v525-owner-request-20260520.txt
docs/runbooks/eidp-operator-e2e-template.md
docs/runbooks/eidp-v1-release-admin-checklist.md
docs/reports/2026-05-20-v525-rc-metadata-package.md
docs/reports/2026-05-19-publication-lag-release-exception-record.md
docs/reports/eidp-current-objective-evidence-checklist.md
docs/reports/current-release-status.md
```

## Windows Destination

ZIP:

```text
C:\EIDP-staging\v525-owner-docs-20260520.zip
```

Extracted docs:

```text
C:\EIDP-staging\v525-owner-docs-20260520
```

Windows-side SHA256:

```text
5b66839c24dd73a68092f823a584475a44779be1f1ae59947284f81af6dab4bb
```

Extracted file proof:

```text
C:\EIDP-staging\v525-owner-docs-20260520\docs\runbooks\00-READ-ME-FIRST-v525.txt
C:\EIDP-staging\v525-owner-docs-20260520\docs\runbooks\eidp-v525-owner-request-20260520.txt
C:\EIDP-staging\v525-owner-docs-20260520\docs\reports\2026-05-20-v525-rc-metadata-package.md
```

## Boundary

This staging action copies only documentation. It does not approve v1.0, does
not promote the active weekly task, and does not modify:

- `data\eidp.sqlite3`
- `data\audit\manual-actions.jsonl`
- `data\master.xlsx`
- `data\pdfs`
- `%USERPROFILE%\EIDP-v485-70e3db4`
- `%USERPROFILE%\EIDP-v525-73392f7-env0`
- `EIDP Weekly Run`

## Post-Staging Boundary Recheck

Read-only checks after staging confirmed that the active scheduled task still
points to v485 and both v485/v525 roots remain present:

```text
active_weekly_action = C:\Users\cyo20\EIDP-v485-70e3db4\scripts\weekly_run.bat
v485_exists = true
v525_exists = true
first_read = true
owner_request = true
package_report = true
```

Current status remains **NOT COMPLETE**.

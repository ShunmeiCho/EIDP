# v523 Owner Docs Windows Staging

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
Scope: owner/operator handoff docs only

## Purpose

Place the v523 owner/operator handoff documents on the Windows machine under
`C:\EIDP-staging` without touching the active v485 runtime, the v523
side-by-side app root, database files, or Task Scheduler.

## Mac Artifact

```text
_temp/v523-owner-docs-20260520.zip
```

SHA256:

```text
11faa8be238c6ae6ff91652af8de7734f1465e135b53358c65365ca42fba6989
```

Contents:

```text
docs/runbooks/00-READ-ME-FIRST-v523.txt
docs/runbooks/eidp-v523-owner-request-20260520.txt
docs/runbooks/eidp-v523-owner-return-manual-review-checklist.md
docs/runbooks/eidp-operator-e2e-template.md
docs/reports/2026-05-20-v523-current-head-package.md
docs/reports/2026-05-20-v523-full-windows-side-by-side-smoke.md
docs/reports/2026-05-19-publication-lag-release-exception-record.md
docs/reports/eidp-current-objective-evidence-checklist.md
docs/reports/current-release-status.md
```

## Windows Destination

ZIP:

```text
C:\EIDP-staging\v523-owner-docs-20260520.zip
```

Extracted docs:

```text
C:\EIDP-staging\v523-owner-docs-20260520
```

Windows-side SHA256:

```text
11faa8be238c6ae6ff91652af8de7734f1465e135b53358c65365ca42fba6989
```

Extracted file proof:

```text
C:\EIDP-staging\v523-owner-docs-20260520\docs\reports\2026-05-19-publication-lag-release-exception-record.md
C:\EIDP-staging\v523-owner-docs-20260520\docs\reports\2026-05-20-v523-current-head-package.md
C:\EIDP-staging\v523-owner-docs-20260520\docs\reports\2026-05-20-v523-full-windows-side-by-side-smoke.md
C:\EIDP-staging\v523-owner-docs-20260520\docs\reports\current-release-status.md
C:\EIDP-staging\v523-owner-docs-20260520\docs\reports\eidp-current-objective-evidence-checklist.md
C:\EIDP-staging\v523-owner-docs-20260520\docs\runbooks\00-READ-ME-FIRST-v523.txt
C:\EIDP-staging\v523-owner-docs-20260520\docs\runbooks\eidp-operator-e2e-template.md
C:\EIDP-staging\v523-owner-docs-20260520\docs\runbooks\eidp-v523-owner-request-20260520.txt
C:\EIDP-staging\v523-owner-docs-20260520\docs\runbooks\eidp-v523-owner-return-manual-review-checklist.md
```

## Boundary

This staging action copies only documentation. It does not approve v1.0, does
not promote the active weekly task, and does not modify:

- `data\eidp.sqlite3`
- `data\audit\manual-actions.jsonl`
- `data\master.xlsx`
- `data\pdfs`
- `%USERPROFILE%\EIDP-v485-70e3db4`
- `%USERPROFILE%\EIDP-v523-9a5cefc-env0`
- `EIDP Weekly Run`

Current status remains **NOT COMPLETE**.

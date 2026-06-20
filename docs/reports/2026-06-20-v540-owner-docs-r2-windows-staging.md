# v540 Owner Docs r2 Windows Staging

Date: 2026-06-20

## Scope

This follow-up stages the v540 owner/operator handoff docs r2 on the Windows
operator host. It adds two owner-facing files:

- `docs/runbooks/eidp-v540-release-summary.md`
- `docs/runbooks/eidp-v540-owner-signoff.md`

This is a docs-only handoff update. It did not modify the active runtime,
SQLite DB, PDFs, audit JSONL, Excel files, or Task Scheduler registration.

## Transfer Evidence

| Check | Evidence |
| --- | --- |
| Docs ZIP | `C:\EIDP-staging\eidp-v540-owner-docs-20260620-r2.zip` |
| ZIP SHA256 | `e5ee3df87e962321ff8a4f37dd3ec9becc776078bcb93cdeed8bcd907751be8f` |
| ZIP SHA256 sidecar | `C:\EIDP-staging\eidp-v540-owner-docs-20260620-r2.zip.sha256` present and matches the ZIP hash |
| Extracted destination | `C:\EIDP-staging\v540-owner-docs-20260620-r2` |
| First-read handoff | `docs\runbooks\00-READ-ME-FIRST-v540.txt` present |
| One-page release summary | `docs\runbooks\eidp-v540-release-summary.md` present |
| Short owner sign-off | `docs\runbooks\eidp-v540-owner-signoff.md` present |
| Owner request | `docs\runbooks\eidp-v540-owner-request-20260620.txt` present |
| Owner return fill sheet | `docs\runbooks\eidp-v540-owner-return-fill-sheet.md` present |
| Current release status | `docs\reports\current-release-status.md` present and contains `NOT_READY` |
| Publication-lag exception record | `docs\reports\2026-05-19-publication-lag-release-exception-record.md` present and contains `NOT_APPROVED` |

## Remote Verification Output

```text
r2 expected sha: E5EE3DF87E962321FF8A4F37DD3EC9BECC776078BCB93CDEED8BCD907751BE8F
r2 actual sha:   E5EE3DF87E962321FF8A4F37DD3EC9BECC776078BCB93CDEED8BCD907751BE8F
docs\runbooks\00-READ-ME-FIRST-v540.txt present: True
docs\runbooks\eidp-v540-release-summary.md present: True
docs\runbooks\eidp-v540-owner-signoff.md present: True
docs\runbooks\eidp-v540-owner-request-20260620.txt present: True
docs\runbooks\eidp-v540-owner-return-fill-sheet.md present: True
docs\reports\current-release-status.md present: True
docs\reports\2026-05-19-publication-lag-release-exception-record.md present: True
current-release-status NOT_READY: True
owner-signoff short-form marker: True
publication-lag NOT_APPROVED: True
scheduled task execute: "C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat"
old r1 zip exists: False
old r1 dir exists: False
```

After the verifier ran, the temporary Windows staging script was removed. The
cleanup recheck returned `False` for
`C:\EIDP-staging\eidp_stage_v540_owner_docs_r2.ps1` existence.

## Local Cleanup

The external-SSD-backed `dist` directory was cleaned after r2 generation:

```text
dist/eidp-v540-owner-docs-20260620-r2.zip
dist/eidp-v540-owner-docs-20260620-r2.zip.sha256
```

The superseded r1 docs ZIP/sidecar and r2 AppleDouble sidecars were removed.

## Safety Recheck

The Windows `EIDP Weekly Run` Scheduled Task still executes:

```text
C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat
```

This confirms the staging step was a docs-only handoff update. It does not
approve v1.0, does not switch the active production lane, and does not replace
the missing owner real Windows cycle, returned KPI/sign-off evidence, approved
`publication_lag` decision, or OCR scope decision.

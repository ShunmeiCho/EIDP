# v547 Owner Docs Windows Staging

Date: 2026-06-21
Release Forecast: `NOT_READY`

## Classification

| Priority | Finding | Evidence | Action |
| --- | --- | --- | --- |
| P0 release blocker | This docs-only staging is not release approval. | v547 still has strict/Excel-ready `12/50 (24.0%)`, `53` blank false-reject worksheet decisions, missing owner real-cycle sign-off, and unapproved `publication_lag` / OCR scope decisions. | Keep release blocked. |
| P1 release hardening | The owner/operator handoff now targets the current v547 canary and worksheet lane. | `C:\EIDP-staging\v547-owner-docs-20260621` was extracted on Windows with SHA256 verification and required v547 files present. | Use this as the current owner/operator docs entry point. |
| P2 storage hygiene | The docs ZIP is small and stored under the external-SSD-backed `dist/`. | Local ZIP size is about `1.0M`; no runtime ZIPs or PDFs were added to git. | Keep generated ZIPs out of git. |
| P3 roadmap/research | University production workflow, cloud, multi-user, and complex frontend remain outside v1. | No v547 owner-docs staging evidence changes v1 scope. | Leave in roadmap. |

## Staged Artifacts

| Field | Value |
| --- | --- |
| Docs ZIP | `C:\EIDP-staging\eidp-v547-owner-docs-20260621.zip` |
| ZIP SHA256 | `1acdf8fb0a2db3b61a24d49ecf2eae9eae9211fa4b0d9f36c91729b3eed2ee54` |
| SHA256 sidecar | `C:\EIDP-staging\eidp-v547-owner-docs-20260621.zip.sha256` |
| Extracted destination | `C:\EIDP-staging\v547-owner-docs-20260621` |
| Active Scheduled Task after staging | `"C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat"` |

Windows verification returned:

```json
{
  "ok": true,
  "expected_sha": "1acdf8fb0a2db3b61a24d49ecf2eae9eae9211fa4b0d9f36c91729b3eed2ee54",
  "actual_sha": "1acdf8fb0a2db3b61a24d49ecf2eae9eae9211fa4b0d9f36c91729b3eed2ee54",
  "dest": "C:\\EIDP-staging\\v547-owner-docs-20260621",
  "missing": [],
  "active_task": "\"C:\\Users\\cyo20\\EIDP-v527-69fe81f-env0\\scripts\\weekly_run.bat\" "
}
```

## Included Current Files

- `docs\runbooks\00-READ-ME-FIRST-v547.txt`
- `docs\runbooks\eidp-v547-release-summary.md`
- `docs\runbooks\eidp-v547-owner-signoff.md`
- `docs\runbooks\eidp-v547-owner-request-20260621.txt`
- `docs\runbooks\eidp-v547-owner-return-fill-sheet.md`
- `docs\runbooks\eidp-operator-e2e-template.md`
- `docs\runbooks\eidp-v1-release-admin-checklist.md`
- `docs\reports\current-release-status.md`
- `docs\reports\eidp-current-objective-evidence-checklist.md`
- `docs\reports\2026-06-21-v547-package-gates.md`
- `docs\reports\2026-06-21-v547-windows-canary.md`
- `docs\reports\2026-06-21-v547-false-reject-review-summary.md`
- `docs\reports\2026-06-21-v547-false-reject-review-sheet.csv`
- `docs\reports\2026-06-21-v547-false-reject-review-validation.json`
- `docs\reports\2026-06-21-v547-false-reject-review-validation-summary.md`
- `docs\reports\2026-05-19-publication-lag-release-exception-record.md`
- `docs\release\owner-decisions\publication-lag.md`
- `docs\release\owner-decisions\ocr-scope.md`
- `docs\release\v1-known-limitations.md`

## Boundary

This copied documentation only. It did not modify the active runtime, SQLite
database, PDFs, Excel output, audit log, or Task Scheduler. It replaces v545 as
the current owner/operator handoff entry point, but it does not approve v1.0 and
does not complete the owner real Windows cycle.

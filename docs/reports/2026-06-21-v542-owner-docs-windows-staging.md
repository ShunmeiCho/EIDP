# v542 Owner Docs Windows Staging

Date: 2026-06-21

## Scope

This follow-up refreshes the docs-only owner/operator handoff from v541 r3 to
the current v542 package identity. It stages the v542 owner handoff docs plus
the v542 false-reject RCA packet and worksheet:

- `docs/runbooks/00-READ-ME-FIRST-v542.txt`
- `docs/runbooks/eidp-v542-release-summary.md`
- `docs/runbooks/eidp-v542-owner-signoff.md`
- `docs/runbooks/eidp-v542-owner-request-20260621.txt`
- `docs/runbooks/eidp-v542-owner-return-fill-sheet.md`
- `docs/runbooks/eidp-operator-e2e-template.md`
- `docs/runbooks/eidp-v1-release-admin-checklist.md`
- `docs/reports/current-release-status.md`
- `docs/reports/eidp-current-objective-evidence-checklist.md`
- `docs/reports/2026-05-19-publication-lag-release-exception-record.md`
- `docs/reports/2026-05-20-owner-v1.0-decision-brief.md`
- `docs/reports/2026-06-21-v542-false-reject-verifier-windows-canary.md`
- `docs/reports/2026-06-21-v542-false-reject-audit-packet.md`
- `docs/reports/2026-06-21-v542-false-reject-review-sheet.csv`
- `docs/release/owner-decisions/publication-lag.md`
- `docs/release/owner-decisions/ocr-scope.md`
- `docs/release/v1-known-limitations.md`

This is a docs-only handoff update. It did not modify the active runtime,
SQLite DB, PDFs, audit JSONL, Excel files, or Task Scheduler registration.

## Transfer Evidence

| Check | Evidence |
| --- | --- |
| Docs ZIP | `C:\EIDP-staging\eidp-v542-owner-docs-20260621.zip` |
| ZIP SHA256 | `553a40a18a43d4a9c5a32f5fb1a5c9abc75a5e0304a6cf25fd4f560be7740e64` |
| ZIP SHA256 sidecar | `C:\EIDP-staging\eidp-v542-owner-docs-20260621.zip.sha256` present and contains the expected ZIP hash |
| Extracted destination | `C:\EIDP-staging\v542-owner-docs-20260621` |
| First-read handoff | `docs\runbooks\00-READ-ME-FIRST-v542.txt` present |
| Owner request | `docs\runbooks\eidp-v542-owner-request-20260621.txt` present and contains `False-reject worksheet rules` plus the return-verifier false-reject arguments |
| Owner return fill sheet | `docs\runbooks\eidp-v542-owner-return-fill-sheet.md` present and contains `False-Reject RCA Worksheet` plus the return-verifier false-reject arguments |
| Current release status | `docs\reports\current-release-status.md` present and contains `NOT_READY` plus the v542 handoff paths |
| Objective checklist | `docs\reports\eidp-current-objective-evidence-checklist.md` present and contains the v542 handoff paths |
| False-reject worksheet | `docs\reports\2026-06-21-v542-false-reject-review-sheet.csv` present |
| False-reject packet | `docs\reports\2026-06-21-v542-false-reject-audit-packet.md` present |

## Remote Verification Output

```text
expected sha: 553a40a18a43d4a9c5a32f5fb1a5c9abc75a5e0304a6cf25fd4f560be7740e64
actual sha:   553a40a18a43d4a9c5a32f5fb1a5c9abc75a5e0304a6cf25fd4f560be7740e64
sidecar exists: True
sidecar content: 553a40a18a43d4a9c5a32f5fb1a5c9abc75a5e0304a6cf25fd4f560be7740e64  dist/eidp-v542-owner-docs-20260621.zip
docs\runbooks\00-READ-ME-FIRST-v542.txt present: True
docs\runbooks\eidp-v542-release-summary.md present: True
docs\runbooks\eidp-v542-owner-signoff.md present: True
docs\runbooks\eidp-v542-owner-request-20260621.txt present: True
docs\runbooks\eidp-v542-owner-return-fill-sheet.md present: True
docs\runbooks\eidp-operator-e2e-template.md present: True
docs\runbooks\eidp-v1-release-admin-checklist.md present: True
docs\reports\current-release-status.md present: True
docs\reports\eidp-current-objective-evidence-checklist.md present: True
docs\reports\2026-05-19-publication-lag-release-exception-record.md present: True
docs\reports\2026-05-20-owner-v1.0-decision-brief.md present: True
docs\reports\2026-06-21-v542-false-reject-verifier-windows-canary.md present: True
docs\reports\2026-06-21-v542-false-reject-audit-packet.md present: True
docs\reports\2026-06-21-v542-false-reject-review-sheet.csv present: True
docs\release\owner-decisions\publication-lag.md present: True
docs\release\owner-decisions\ocr-scope.md present: True
docs\release\v1-known-limitations.md present: True
request worksheet rules: True
request verifier false-reject args: True
request v542 package verifier wording: True
return sheet false-reject section: True
return sheet verifier false-reject args: True
return sheet v542 package verifier wording: True
current-release-status NOT_READY: True
current-release-status v542 handoff: True
objective checklist v542 handoff: True
review worksheet header: audit_row_id,bucket,decision,reviewer,reviewed_at,school_id,reason,pdf_type,detected_fiscal_year,year_evidence,trusted_year_evidence,discovery_method,anchor_text,page_url,pdf_url,review_question,false_reject_signal,notes
scheduled task execute: "C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat"
C:\EIDP-staging\eidp-v541-owner-docs-20260621.zip present: False
C:\EIDP-staging\eidp-v541-owner-docs-20260621.zip.sha256 present: False
C:\EIDP-staging\v541-owner-docs-20260621 present: False
C:\EIDP-staging\eidp-v541-owner-docs-20260621-r2.zip present: False
C:\EIDP-staging\eidp-v541-owner-docs-20260621-r2.zip.sha256 present: False
C:\EIDP-staging\v541-owner-docs-20260621-r2 present: False
C:\EIDP-staging\eidp-v541-owner-docs-20260621-r3.zip present: False
C:\EIDP-staging\eidp-v541-owner-docs-20260621-r3.zip.sha256 present: False
C:\EIDP-staging\v541-owner-docs-20260621-r3 present: False
v542 extracted dir present: True
```

## Local Cleanup

The generated v542 docs ZIP and sidecar are retained on the external SSD as the
current handoff transfer artifact:

```text
dist/eidp-v542-owner-docs-20260621.zip
dist/eidp-v542-owner-docs-20260621.zip.sha256
```

Superseded owner-doc transfer ZIPs and sidecars for v540 r2, v541 base, and
v541 r3 were removed from the external-SSD-backed `dist/` directory after v542
verification. macOS AppleDouble `._*` sidecars were also removed. Current
retained top-level transfer/core artifacts are:

```text
dist/eidp-v542-owner-docs-20260621.zip
dist/eidp-v542-owner-docs-20260621.zip.sha256
dist/eidp-windows-v535.zip
dist/eidp-windows-v536.zip
dist/eidp-windows-v542.zip
dist/eidp-windows.zip
```

Current external SSD artifact usage after cleanup:

```text
/Volumes/M1nG-ssd/EIDP-artifacts/dist  1.1G
/Volumes/M1nG-ssd/EIDP-artifacts/logs  1.3G
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

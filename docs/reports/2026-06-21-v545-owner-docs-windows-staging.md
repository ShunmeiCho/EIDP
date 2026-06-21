# v545 Owner Docs Windows Staging

Date: 2026-06-21

## Scope

This follow-up refreshes the docs-only owner/operator handoff from v544 to the
current v545 package identity. It stages the v545 owner handoff docs plus the
v545 false-reject RCA packet, read-only review summary, worksheet, and
blank-worksheet validation:

- `docs/runbooks/00-READ-ME-FIRST-v545.txt`
- `docs/runbooks/eidp-v545-release-summary.md`
- `docs/runbooks/eidp-v545-owner-signoff.md`
- `docs/runbooks/eidp-v545-owner-request-20260621.txt`
- `docs/runbooks/eidp-v545-owner-return-fill-sheet.md`
- `docs/runbooks/eidp-operator-e2e-template.md`
- `docs/runbooks/eidp-v1-release-admin-checklist.md`
- `docs/reports/current-release-status.md`
- `docs/reports/eidp-current-objective-evidence-checklist.md`
- `docs/reports/2026-05-19-publication-lag-release-exception-record.md`
- `docs/reports/2026-05-20-owner-v1.0-decision-brief.md`
- `docs/reports/2026-06-21-v545-disclosure-priority-windows-canary.md`
- `docs/reports/2026-06-21-v545-false-reject-audit-packet.md`
- `docs/reports/2026-06-21-v545-false-reject-review-summary.md`
- `docs/reports/2026-06-21-v545-false-reject-review-sheet.csv`
- `docs/reports/2026-06-21-v545-false-reject-review-validation.json`
- `docs/release/owner-decisions/publication-lag.md`
- `docs/release/owner-decisions/ocr-scope.md`
- `docs/release/v1-known-limitations.md`

This is a docs-only handoff update. It did not modify the active runtime,
SQLite DB, PDFs, audit JSONL, Excel files, or Task Scheduler registration.

## Transfer Evidence

| Check | Evidence |
| --- | --- |
| Docs ZIP | `C:\EIDP-staging\eidp-v545-owner-docs-20260621.zip` |
| ZIP SHA256 | `1b7f5d21ece3da3defe1956111213d004a1c6ba32f33bcc88e87f7471052bc1d` |
| ZIP SHA256 sidecar | `C:\EIDP-staging\eidp-v545-owner-docs-20260621.zip.sha256` present and contains the expected ZIP hash |
| Extracted destination | `C:\EIDP-staging\v545-owner-docs-20260621` |
| First-read handoff | `docs\runbooks\00-READ-ME-FIRST-v545.txt` present and contains latest docs commit `294d329` plus CI `27890470359` |
| Release summary | `docs\runbooks\eidp-v545-release-summary.md` present and contains latest docs commit `294d329` plus CI `27890470359` |
| Owner request | `docs\runbooks\eidp-v545-owner-request-20260621.txt` present and contains `False-reject worksheet rules` plus the read-only review summary guidance |
| Owner return fill sheet | `docs\runbooks\eidp-v545-owner-return-fill-sheet.md` present and contains the return-verifier false-reject arguments plus the read-only summary warning |
| Current release status | `docs\reports\current-release-status.md` present and contains `NOT_READY`, the v545 handoff path, and the review summary path |
| Objective checklist | `docs\reports\eidp-current-objective-evidence-checklist.md` present and contains the v545 handoff path plus the read-only review summary |
| False-reject worksheet | `docs\reports\2026-06-21-v545-false-reject-review-sheet.csv` present |
| False-reject packet | `docs\reports\2026-06-21-v545-false-reject-audit-packet.md` present |
| False-reject review summary | `docs\reports\2026-06-21-v545-false-reject-review-summary.md` present and contains the read-only warning plus `12/50` strict-yield context |
| False-reject validation | `docs\reports\2026-06-21-v545-false-reject-review-validation.json` present |

## Remote Verification Output

```text
expected sha: 1b7f5d21ece3da3defe1956111213d004a1c6ba32f33bcc88e87f7471052bc1d
actual sha:   1b7f5d21ece3da3defe1956111213d004a1c6ba32f33bcc88e87f7471052bc1d
sidecar content: 1b7f5d21ece3da3defe1956111213d004a1c6ba32f33bcc88e87f7471052bc1d  dist/eidp-v545-owner-docs-20260621.zip
docs\runbooks\00-READ-ME-FIRST-v545.txt present: True
docs\runbooks\eidp-v545-release-summary.md present: True
docs\runbooks\eidp-v545-owner-signoff.md present: True
docs\runbooks\eidp-v545-owner-request-20260621.txt present: True
docs\runbooks\eidp-v545-owner-return-fill-sheet.md present: True
docs\reports\2026-06-21-v545-false-reject-review-sheet.csv present: True
docs\reports\2026-06-21-v545-false-reject-audit-packet.md present: True
docs\reports\2026-06-21-v545-false-reject-review-summary.md present: True
docs\reports\2026-06-21-v545-false-reject-review-validation.json present: True
latest docs commit in first-read: True
latest docs CI in first-read: True
latest docs commit in release summary: True
latest docs CI in release summary: True
latest docs commit in return sheet: True
latest docs CI in return sheet: True
request worksheet rules: True
request review summary guidance: True
return sheet verifier false-reject args: True
return sheet review summary warning: True
current-release-status NOT_READY: True
current-release-status v545 handoff: True
current-release-status review summary: True
objective checklist v545 handoff: True
objective checklist review summary: True
review summary present: True
review summary read-only warning: True
review summary strict yield: True
review worksheet header: audit_row_id,bucket,decision,reviewer,reviewed_at,school_id,reason,pdf_type,detected_fiscal_year,year_evidence,trusted_year_evidence,discovery_method,anchor_text,page_url,pdf_url,suggested_decision,suggested_decision_basis,review_question,false_reject_signal,notes
scheduled task execute: "C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat"
C:\EIDP-staging\v545-owner-docs-20260621 present: True
C:\EIDP-staging\v544-owner-docs-20260621 present: False
C:\EIDP-staging\eidp-windows-v544.zip present: True
C:\EIDP-staging\eidp-windows-v545.zip present: True
```

## Cleanup

The generated v545 docs ZIP and sidecar are retained on the external SSD as the
current handoff transfer artifact:

```text
dist/eidp-v545-owner-docs-20260621.zip
dist/eidp-v545-owner-docs-20260621.zip.sha256
```

Superseded v544 owner-doc transfer ZIPs and sidecars were removed from the
external-SSD-backed `dist/` directory after v545 verification:

```text
dist/eidp-v544-owner-docs-20260621.zip
dist/eidp-v544-owner-docs-20260621.zip.sha256
```

AppleDouble `._*` files were also removed from `dist/` after local package
creation. The superseded Windows docs-only staging artifacts were removed:

```text
C:\EIDP-staging\eidp-v544-owner-docs-20260621.zip
C:\EIDP-staging\eidp-v544-owner-docs-20260621.zip.sha256
C:\EIDP-staging\v544-owner-docs-20260621
```

This cleanup did not remove v544 core package artifacts or historical tracked
evidence reports. Current retained top-level transfer/core artifacts are:

```text
dist/eidp-v545-owner-docs-20260621.zip
dist/eidp-v545-owner-docs-20260621.zip.sha256
dist/eidp-windows-v544.zip
dist/eidp-windows-v544.zip.sha256
dist/eidp-windows-v545.zip
dist/eidp-windows-v545.zip.sha256
dist/eidp-windows.zip
dist/eidp-windows.zip.sha256
```

Current external SSD artifact usage after cleanup:

```text
/Volumes/M1nG-ssd/EIDP-artifacts/dist  901M
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

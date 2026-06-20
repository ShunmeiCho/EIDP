# v541 Owner Docs r2 Windows Staging

Date: 2026-06-21

## Scope

This follow-up refreshes the docs-only v541 owner/operator handoff on the
Windows operator host after the false-reject worksheet return rules were added
to the owner request and owner return fill sheet.

It stages the current owner handoff docs plus the v541 false-reject RCA packet
and worksheet:

- `docs/runbooks/00-READ-ME-FIRST-v541.txt`
- `docs/runbooks/eidp-v541-release-summary.md`
- `docs/runbooks/eidp-v541-owner-signoff.md`
- `docs/runbooks/eidp-v541-owner-request-20260621.txt`
- `docs/runbooks/eidp-v541-owner-return-fill-sheet.md`
- `docs/reports/current-release-status.md`
- `docs/reports/eidp-current-objective-evidence-checklist.md`
- `docs/reports/2026-05-19-publication-lag-release-exception-record.md`
- `docs/reports/2026-06-21-v541-owner-signoff-verifier-windows-canary.md`
- `docs/reports/2026-06-21-v541-false-reject-audit-packet.md`
- `docs/reports/2026-06-21-v541-false-reject-review-sheet.csv`
- `docs/release/owner-decisions/publication-lag.md`
- `docs/release/owner-decisions/ocr-scope.md`
- `docs/release/v1-known-limitations.md`

This is a docs-only handoff update. It did not modify the active runtime,
SQLite DB, PDFs, audit JSONL, Excel files, or Task Scheduler registration.

## Transfer Evidence

| Check | Evidence |
| --- | --- |
| Docs ZIP | `C:\EIDP-staging\eidp-v541-owner-docs-20260621-r2.zip` |
| ZIP SHA256 | `6575a28c74be7d977db8fd640a622f070f7027915e07dd04698a38d4bc12dd31` |
| ZIP SHA256 sidecar | `C:\EIDP-staging\eidp-v541-owner-docs-20260621-r2.zip.sha256` present and contains the expected ZIP hash |
| Extracted destination | `C:\EIDP-staging\v541-owner-docs-20260621-r2` |
| First-read handoff | `docs\runbooks\00-READ-ME-FIRST-v541.txt` present |
| Owner request | `docs\runbooks\eidp-v541-owner-request-20260621.txt` present and contains `False-reject worksheet rules` |
| Owner return fill sheet | `docs\runbooks\eidp-v541-owner-return-fill-sheet.md` present and contains `False-Reject RCA Worksheet` |
| Current release status | `docs\reports\current-release-status.md` present and contains `NOT_READY` |
| Objective checklist | `docs\reports\eidp-current-objective-evidence-checklist.md` present |
| False-reject worksheet | `docs\reports\2026-06-21-v541-false-reject-review-sheet.csv` present |
| False-reject packet | `docs\reports\2026-06-21-v541-false-reject-audit-packet.md` present |

## Remote Verification Output

```text
expected sha: 6575a28c74be7d977db8fd640a622f070f7027915e07dd04698a38d4bc12dd31
actual sha:   6575a28c74be7d977db8fd640a622f070f7027915e07dd04698a38d4bc12dd31
docs\runbooks\00-READ-ME-FIRST-v541.txt present: True
docs\runbooks\eidp-v541-owner-request-20260621.txt present: True
docs\runbooks\eidp-v541-owner-return-fill-sheet.md present: True
docs\reports\current-release-status.md present: True
docs\reports\eidp-current-objective-evidence-checklist.md present: True
docs\reports\2026-06-21-v541-false-reject-review-sheet.csv present: True
docs\reports\2026-06-21-v541-false-reject-audit-packet.md present: True
return sheet false-reject section: True
request worksheet rules: True
current-release-status NOT_READY: True
review worksheet header: audit_row_id,bucket,decision,reviewer,reviewed_at,school_id,reason,pdf_type,detected_fiscal_year,year_evidence,trusted_year_evidence,discovery_method,anchor_text,page_url,pdf_url,review_question,false_reject_signal,notes
scheduled task execute: "C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat"
sidecar exists: True
sidecar content: 6575a28c74be7d977db8fd640a622f070f7027915e07dd04698a38d4bc12dd31  /Volumes/M1nG-ssd/EIDP-artifacts/dist/eidp-v541-owner-docs-20260621-r2.zip
```

## Local Cleanup

The generated docs ZIP and sidecar are retained on the external SSD as the
current handoff transfer artifact:

```text
/Volumes/M1nG-ssd/EIDP-artifacts/dist/eidp-v541-owner-docs-20260621-r2.zip
/Volumes/M1nG-ssd/EIDP-artifacts/dist/eidp-v541-owner-docs-20260621-r2.zip.sha256
```

The temporary external-SSD staging directory was removed after transfer. The
temporary Windows verification script was also removed:

```text
C:\EIDP-staging\eidp-verify-v541-owner-docs-r2.ps1 present: False
/Volumes/M1nG-ssd/EIDP-artifacts/stage only contains the empty stage root
```

Current external SSD artifact usage after cleanup:

```text
/Volumes/M1nG-ssd/EIDP-artifacts/dist   1.3G
/Volumes/M1nG-ssd/EIDP-artifacts/stage  1.0M
```

The clean ZIP was created without macOS AppleDouble `._*` sidecars.

## Safety Recheck

The Windows `EIDP Weekly Run` Scheduled Task still executes:

```text
C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat
```

This confirms the staging step was a docs-only handoff update. It does not
approve v1.0, does not switch the active production lane, and does not replace
the missing owner real Windows cycle, returned KPI/sign-off evidence, approved
`publication_lag` decision, or OCR scope decision.

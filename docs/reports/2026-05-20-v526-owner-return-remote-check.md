# v526 Owner Return Remote Check

Date: 2026-05-20 20:37 JST
Scope: read-only Windows SSH probe after the `ssh win` service recovered.

## Summary

The Windows host is reachable over SSH, and the refreshed v526 owner handoff
docs are still staged on the Windows machine. No completed v526 owner real-cycle
return, sign-off, or `publication_lag` approval was found in the checked
handoff and v526 log locations.

This is negative evidence only. It confirms that the v526 handoff is present,
but it does not unblock v1.0.

## Probe Boundary

The probe was intentionally read-only and limited to:

- `C:\EIDP-staging`
- `C:\Users\junming\Desktop`
- `C:\Users\junming\Downloads`
- `C:\Users\cyo20\EIDP-v526-5b30eb7-env0\logs`

The initial broad recursive scan of `C:\Users` was stopped because it was too
wide for an interactive check. The final probe avoided that broad scan.

## Host And Handoff State

| Item | Result |
| --- | --- |
| SSH target | `win` |
| Host | `JUNMING` |
| SSH user | `junming` |
| `C:\EIDP-staging` | present |
| `C:\Users\junming\Desktop` | missing |
| `C:\Users\junming\Downloads` | missing |
| `C:\Users\cyo20\EIDP-v526-5b30eb7-env0\logs` | present |
| v526 owner docs | `C:\EIDP-staging\v526-owner-docs-20260520` present |

The staged v526 owner docs include:

- `docs\reports\2026-05-19-publication-lag-release-exception-record.md`
- `docs\reports\2026-05-20-v526-extracted-confirmation-package.md`
- `docs\reports\2026-05-20-v526-post-reboot-active-task-preflight.md`
- `docs\reports\current-release-status.md`
- `docs\reports\eidp-current-objective-evidence-checklist.md`
- `docs\runbooks\00-READ-ME-FIRST-v526.txt`
- `docs\runbooks\eidp-operator-e2e-template.md`
- `docs\runbooks\eidp-v1-release-admin-checklist.md`
- `docs\runbooks\eidp-v526-owner-request-20260520.txt`
- `docs\runbooks\eidp-windows.md`

## Approval State

Remote staged exception record:

| Field | Remote value |
| --- | --- |
| Status | `NOT_APPROVED` |
| Decision | `NOT_APPROVED` |
| Approver | blank |
| Approval date | blank |
| FY2026/R8 status acknowledged | blank |

Remote staged E2E template still has blank sign-off rows:

- `Owner sign-off: Name`
- `Owner sign-off: Date`
- `Owner sign-off: Decision`
- `業務員 sign-off: Name`
- `業務員 sign-off: Date`
- `業務員 sign-off: Decision`

## Candidate Files Seen

The candidate-owner-return search returned the refreshed v526 owner docs ZIP,
the staged v526 docs, known v526 smoke/evidence logs, historical v525/v523
handoff docs, and historical v485 owner evidence. It did not show a completed
v526 owner E2E return or signed approval artifact.

Known v526 smoke/evidence files seen include:

- `C:\Users\cyo20\EIDP-v526-5b30eb7-env0\logs\stage6-evidence-20260520-091540.zip`
- `C:\Users\cyo20\EIDP-v526-5b30eb7-env0\logs\stage6-evidence-verify-20260520-v526.json`
- `C:\Users\cyo20\EIDP-v526-5b30eb7-env0\logs\win-v526-stage6-v526-last-run-after-weekly-canary-limit50-20260520.json`
- `C:\Users\cyo20\EIDP-v526-5b30eb7-env0\logs\win-v526-stage6-v526-excel-summary-20260520.json`
- `C:\Users\cyo20\EIDP-v526-5b30eb7-env0\logs\stage6-recovery-20260520-v526.json`

Historical v485 owner-evidence files are still present under `C:\EIDP-staging`,
but they are not v526 owner real-cycle approval evidence.

## Verdict

P0 remains blocked:

1. `publication_lag` exception approval is still absent.
2. Owner real Windows cycle sign-off is still absent.
3. v1.0 tag remains disallowed.

# Windows Track Legacy Boundary

Date: 2026-07-05

This document defines what remains reusable from the Windows track during the
Linux/Web pivot, what becomes fallback, and what must not be deleted or
relabelled without owner/PI approval.

## Boundary Statement

The Linux/Web pivot does not archive the Windows track. The Windows work remains
the current packaged evidence baseline and rollback path until an approved
Linux/Web release replaces it.

Release Forecast remains `NOT_READY`. The pivot package does not change the
v548 Windows canary evidence and does not declare Linux/Web approved.

## Reusable Assets

The following Windows-track assets remain reusable:

- database schema, migrations, and import/export concepts;
- `data/master.xlsx` conventions and Excel workbook expectations;
- extraction confidence model and manual review principles;
- audit log and append-only decision patterns;
- Stage 6 vocabulary for evidence bundles and verifier outputs;
- owner/operator sign-off templates and return-intake discipline;
- package verification lessons around reproducibility and checksums;
- file-lock and SQLite lock handling lessons;
- no-regret table-aware extraction first cut completed on the extraction branch.

## Legacy Or Fallback Items

The following become legacy/fallback in the proposed Linux/Web v1 path:

- Windows ZIP as primary delivery;
- local single-PC operator setup;
- Windows scheduled weekly task as primary operation;
- Streamlit desktop-style flow as the final Web UX;
- broad automatic crawler/yield work as the first v1 release blocker;
- file-lock-heavy local Excel workflow as the only output model.

They are still valid fallback evidence. They must not be deleted, archived, or
renamed as obsolete until owner/PI approves a retirement plan.

## Explicit Non-Goals For This Slice

This docs slice must not:

- delete Windows code;
- modify Windows package scripts;
- edit Windows canary reports;
- change `docs/reports/current-release-status.md`;
- change deployment scripts;
- alter release forecast wording;
- implement Linux/Web UI;
- reuse HTML prototype/support files as production UI.

## Fallback Use

Windows fallback remains appropriate when:

- Linux server network access is unavailable;
- owner/PI has not approved the Web release direction;
- external extraction policy is unresolved;
- SQLite concurrency is not acceptable for the intended Web use;
- a package-style operator handoff is still required.

Fallback does not mean `READY`; it only preserves an operational route while
the release gates remain open.

## Retirement Criteria

Windows can be considered for archive only after:

- Linux/Web v1 is owner-approved;
- Linux/Web release gates pass with evidence;
- owner/operator sign-off exists;
- a rollback plan is documented;
- historical v547/v548 evidence is preserved read-only;
- Excel output and audit requirements are proven in the Web workflow.

Until then, Windows is a maintained fallback boundary, not dead code.

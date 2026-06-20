# v1 Exit Criteria

Updated: 2026-06-20

This file defines what "v1 complete" means for EIDP. It is a release decision
anchor, not a backlog. Detailed operational gates remain in
`docs/governance/release-gates.md`,
`docs/runbooks/eidp-v1-release-admin-checklist.md`, and
`docs/reports/current-release-status.md`.

## v1 Scope

v1 is complete only for the vocational-school-first, one-operator Windows
workflow:

- official index and official disclosure entry based PDF discovery;
- target-year judgment for the configured fiscal year;
- deterministic PDF extraction, OCR fallback when in scope, and manual review;
- program/metrics review sufficient for workbook output;
- audit trail for manual business decisions;
- Excel-ready gate and workbook export;
- Windows ZIP installation and operation.

v1 completion does not mean university production support, multi-operator
operation, PostgreSQL, cloud deployment, or a React production frontend.

## Exit Criteria

All criteria below must be true before v1 can be called complete:

| Gate | Required result |
| --- | --- |
| Source scope | v1 remains scoped to `専門学校` unless an owner-approved scope change exists |
| Official evidence | PDF discovery starts from MEXT/prefecture/authority indexes and official disclosure entries |
| Target year | current target-year evidence is explicit, or a formal `publication_lag` exception is approved |
| PDF identity | target-document kind and institution identity are confirmed before business ingestion |
| Extraction | parsed/OCR/manual values are accepted through confidence or operator review gates |
| Program changes | new, discontinued, renamed, merged, or split programs are reviewed before export |
| Excel-ready | unconfirmed, low-confidence, mismatched, non-target, and old-year rows cannot silently enter Excel |
| Audit | manual URL, PDF, fiscal-year, metrics, program-change, and export decisions are logged |
| Windows evidence | setup, start, weekly run, diagnose, SQLite lock behavior, and Excel output are validated on Windows |
| Owner return | owner/operator E2E template, KPI rows, sign-off, and evidence verification pass |
| Release conclusion | the only acceptable GA conclusion is `READY`; `RC_ONLY` and `NOT_READY` do not complete v1 |

## Current Decision

As of 2026-06-20, v1 is not complete. The current release status remains
`NOT_READY` until the release gates above have real evidence and the owner
decisions are returned.

Current blocking areas are tracked in `docs/reports/current-release-status.md`
and include FY2026/R8 strict-yield gating, owner/operator real-cycle sign-off,
the unapproved `publication_lag` path, and the selected OCR release scope.


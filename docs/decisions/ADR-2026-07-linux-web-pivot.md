# ADR-2026-07: Linux/Web pivot decision package

- Status: Proposed
- Date: 2026-07-05
- Branch: `docs/linux-web-pivot-decision`
- Scope: decision documentation only

## Decision Summary

Meeting direction changes the v1 product goal from a Windows single-operator
package optimized around automatic target-year PDF discovery to a
Linux-hosted Web workflow focused on correct-PDF intake, extraction, human
double-check, and Excel integration.

This ADR does not approve the pivot for release. It records the decision
package needed for owner/PI review. Release Forecast remains `NOT_READY` until
owner/PI approval and the Linux/Web release gates are satisfied with evidence.

## Current v1 Goal After The Meeting

v1 should prioritize:

- user-provided or user-confirmed correct `機関要件確認申請書` PDFs;
- deterministic local EIDP extraction from text PDFs;
- comparison against operator-supplied Copilot/NotebookLM extraction outputs;
- human reconciliation of mismatches before Excel;
- Excel output that can be joined with existing workbook workflows through
  XLOOKUP-compatible keys and columns;
- image PDFs as exception/manual/OCR flow, not the main release path.

Full automatic target-year PDF discovery and fiscal-year judgment are no
longer the main v1 release path. They remain useful support tooling, but they
must not be treated as the release blocker for the Linux/Web v1 proposal.

## What Stays Reusable From The Windows Track

The Windows track produced assets that remain useful in either deployment:

- PDF extraction tests, schemas, confidence logic, and manual review concepts;
- table-aware extraction first cut from `feature/table-aware-ohara-extraction`;
- read-only `data/master.xlsx` import and Excel export conventions;
- release evidence discipline, owner sign-off shape, and Stage 6 verifier
  vocabulary;
- SQLite data model and migration history;
- append-only audit principles for manual corrections and export decisions;
- packaging lessons about local-only secrets, file locks, and reproducibility.

The no-regret extraction first cut already completed for the pivot is:

- field aliases for `生徒` / `学生` capacity and enrollment labels;
- pdfplumber table-grid extraction for capacity, enrollment, and international
  student counts;
- page/table/row/column evidence on extracted table values;
- Ohara table regression coverage;
- a small `data/master.xlsx` ground-truth diff harness.

This ADR references that work as completed implementation evidence. It does
not modify extraction code in this docs-only branch.

## What Becomes Legacy Or Fallback

The following Windows-track behavior becomes legacy or fallback for Linux/Web
v1 unless owner/PI explicitly keeps it as a release requirement:

- Windows ZIP as the primary delivery artifact;
- one-PC Streamlit operation as the primary operator workflow;
- fully automatic target-year discovery as the main v1 success path;
- broad crawler improvement as the first response to low strict-yield numbers;
- image-PDF OCR as mandatory core behavior;
- local Excel file-lock behavior as the only workbook-output operational
  model.

These items are not deleted or archived by this decision package. They remain
available for fallback, audit comparison, and rollback until an owner-approved
retirement decision exists.

## Proposed Linux/Web Shape

The proposed v1 system is a Linux-hosted, browser-accessed internal tool:

- users upload or select the correct official PDF locally within the EIDP
  environment;
- EIDP runs local extraction and records evidence;
- users import or paste externally generated Copilot/NotebookLM extraction
  results when policy allows;
- the Web UI shows differences and requires human acceptance before export;
- output is staged for Excel/XLOOKUP workflows and never silently writes
  unverified values into final Excel.

The old HTML prototype, including `prototype/support.js` or equivalent
support files, is not production UI and must not be reused as the production
implementation.

## Open Owner/PI Decisions

Owner/PI must still decide:

- whether Linux/Web is approved as the v1 release direction;
- who may access the Linux server and from which network;
- whether external Copilot/NotebookLM handling is allowed, and for which data;
- whether user-provided correct PDFs are enough for v1 scope;
- whether automatic target-year judgment is support-only or still a partial
  release gate;
- whether image PDFs require OCR in core v1 or remain manual exceptions;
- whether SQLite single-writer limits are acceptable for the expected operator
  concurrency;
- what evidence proves Excel/XLOOKUP output is ready.

## Consequences

Positive:

- v1 can focus on extraction correctness and human-verifiable PDF intake;
- Windows work is preserved as fallback and evidence rather than thrown away;
- table-aware extraction work is directly reusable;
- risky automatic year judgment is no longer over-weighted in v1.

Tradeoffs:

- Linux/Web introduces network, authentication, and concurrency questions;
- Copilot/NotebookLM comparison introduces data-handling policy risk;
- SQLite can remain viable only if the Web workflow keeps a clear
  single-writer boundary;
- release evidence must be rebuilt for the new operation model.

## Release Position

This decision package does not declare `READY`, does not change
`docs/reports/current-release-status.md`, and does not change the v548 Windows
canary evidence. The release forecast remains `NOT_READY`.


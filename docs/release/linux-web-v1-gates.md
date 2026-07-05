# Linux/Web v1 Release Gates

Date: 2026-07-05

These gates define what evidence is required before EIDP can describe a
Linux-hosted Web workflow as v1-ready. They do not change the existing Windows
release forecast, and they do not declare the pivot approved.

## Release Conclusion Vocabulary

Allowed conclusions remain:

- `READY`
- `RC_ONLY`
- `NOT_READY`

Current Linux/Web status is `NOT_READY`. A green test suite or a complete
decision package is not enough to change that status.

## Scope Gate

Linux/Web v1 is scoped to:

- vocational-school (`専門学校`) PDF extraction and review;
- user-provided or user-confirmed correct PDFs;
- text PDFs as the main path;
- image PDFs as exception/manual/OCR flow;
- local EIDP extraction compared with operator-provided
  Copilot/NotebookLM-style extraction outputs;
- human-reviewed differences before Excel;
- Excel/XLOOKUP-compatible output.

Linux/Web v1 is not scoped to:

- university production support;
- automatic whole-country target-year PDF discovery as the main release path;
- external automatic PDF upload;
- replacing owner/PI sign-off with developer judgment;
- reusing the HTML prototype as production UI.

## Required Gates

| Gate | Required evidence before `READY` |
| --- | --- |
| Owner/PI approval | Explicit owner/PI decision approving Linux/Web as the v1 release direction |
| Correct-PDF intake | Workflow proves users provide or confirm the correct official PDF before extraction |
| PDF type boundary | Text PDFs pass the main path; image PDFs route to manual/OCR exception state |
| EIDP extraction | Local extractor produces metric rows with field evidence and confidence policy |
| External comparison | Copilot/NotebookLM outputs are imported only under approved data policy and compared without automatic acceptance |
| Human reconciliation | Mismatches require human decision and audit trail before Excel |
| Excel/XLOOKUP | Output includes stable join keys and columns suitable for XLOOKUP integration |
| No unverified Excel writes | Unconfirmed, low-confidence, mismatched, or non-target values cannot enter final Excel silently |
| Network access | Server access path, allowed network, authentication, and operator reachability are proven |
| SQLite concurrency | Single-writer boundary or alternate database decision is documented and tested |
| Audit | PDF selection, extraction comparison, reconciliation, and export decisions are logged |
| Rollback/fallback | Windows fallback boundary is documented and not deleted |

## Technical Gate Details

### Correct-PDF Intake

Users must either upload/select the official PDF or confirm a candidate PDF.
The UI must record:

- source URL or file provenance when available;
- school identity;
- fiscal year as user-confirmed or explicitly unknown;
- document type;
- operator identity and timestamp.

The system must not infer the target fiscal year from download time.

### Extraction And Comparison

The Linux/Web gate should use the no-regret extraction first cut as the local
baseline:

- canonical aliases for `生徒` / `学生` labels;
- table-grid extraction for capacity, enrollment, and international students;
- page/table/row/column evidence for extracted values;
- `data/master.xlsx` small-subset diff harness as ground-truth check.

External Copilot/NotebookLM output is comparison input only. It must not
overwrite EIDP extraction or final Excel without human approval.

### Excel/XLOOKUP

The Web workflow should produce reviewable rows with stable columns for:

- school identity;
- department key;
- fiscal year;
- metric name;
- EIDP extracted value;
- external extracted value when provided;
- accepted value;
- evidence and reviewer decision.

The final Excel handoff must remain blocked for rows without accepted values.

## Network Gate

Before `READY`, the team must prove:

- who can reach the Linux server;
- whether access is limited to education-net/STF or requires VPN/bastion;
- TLS/authentication/session policy;
- backup access for owner/PI review;
- no public exposure without owner-approved security review.

See `docs/decisions/linux-server-network-access.md`.

## SQLite Concurrency Gate

SQLite can be accepted only if Linux/Web v1 is operated with a clear
single-writer contract:

- one active write operation at a time;
- short transactions;
- explicit lock/retry behavior;
- visible "busy/retry" user state;
- backup/checkpoint procedure;
- documented maximum operator concurrency.

If concurrent multi-user writes are required, owner/PI must approve a database
change before release.

## Release Forecast

Release Forecast remains `NOT_READY` until every gate above has evidence and
owner/PI approval. This file is a proposed gate package, not release approval.


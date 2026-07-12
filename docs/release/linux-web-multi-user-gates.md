# Linux/Web Multi-User Release Gates

Date: 2026-07-05

Release Forecast: `NOT_READY`

This gate package defines what must be true before EIDP can be described as a
formal multi-user Linux/Web system. It does not change the current release
forecast and does not approve Linux/Web for release.

## Current Position

Current Streamlit pages remain valid as internal MVP and smoke UI. They are not
the final multi-user production UI.

The target multi-user architecture is:

- React/TypeScript UI;
- Python FastAPI backend;
- PostgreSQL persistence;
- background workers;
- server-side locking, audit, and Excel-ready gates.

## Required Gates

| Gate | Required evidence |
| --- | --- |
| Owner/PI approval | Explicit approval that Linux/Web multi-user operation is in scope |
| User identity | Every mutating action records stable `user_id` and display identity |
| Roles | Minimum role policy exists for viewer, operator, reviewer, and admin |
| Persistence | Business state is stored in PostgreSQL or an approved equivalent |
| SQLite boundary | If SQLite/local JSON remains, maximum concurrency and single-writer limits are documented |
| Locking | Review and mapping writes use optimistic locking or explicit row locks |
| Audit | Every accept/correct/exclude/mapping/export decision writes an audit event |
| Job queue | Extraction, external comparison, and workbook generation run outside frontend request handling |
| File storage | PDFs and generated artifacts are addressed by server-managed document IDs |
| Ambiguous key handling | `ambiguous_key` rows require `master_row_id` or `program_mapping_id` before comparison/export |
| Double-check boundary | External Copilot/NotebookLM files are imported only under approved data policy |
| Excel-ready gate | Server-side gate blocks unresolved, ambiguous, mismatched, or unreviewed rows |
| Network access | Allowed network, authentication, TLS/session policy, and operator reachability are proven |
| Backup/recovery | Database and file storage backup/restore procedure is tested |
| Observability | Job status, failure reason, and audit trail are visible to operators |

## Non-Comparable Rows

The system must treat these rows as not comparable:

- `ambiguous_key`;
- `needs_review`;
- `excluded`;
- unresolved image/manual/OCR tasks;
- rows with missing required metrics;
- rows with unresolved double-check mismatch;
- rows whose reviewed/master mapping is stale or version-conflicted.

Non-comparable rows must not become Excel-ready.

## Concurrency Requirements

Multi-user write paths must include:

- `version` or equivalent revision token;
- `updated_at`;
- `updated_by`;
- previous value and new value;
- conflict response when a stale update is submitted;
- audit event for both successful writes and rejected stale writes when useful.

Last-write-wins is not acceptable for review, mapping, or export decisions.

## External Data Handling

Copilot/NotebookLM outputs are second-opinion evidence. They are not automatic
truth and cannot overwrite reviewed EIDP values without human decision.

The system must not automatically upload PDFs or raw school documents to
external tools unless owner/PI approves a data policy for that operation.

## Goal 4 Gate

Goal 4 may start from the current integration baseline only if it follows this
temporary gate:

- compare only unique comparable rows;
- keep `ambiguous_key`, `needs_review`, and `excluded` as not comparable;
- generate TRUE/FALSE or match/mismatch reports without marking rows
  Excel-ready;
- keep final Excel and XLOOKUP output out of scope.

## Release Forecast

`NOT_READY`

These gates add multi-user requirements. They do not reduce the existing
Linux/Web v1 gates for owner/PI approval, deployment proof, network access
proof, data-policy approval, external comparison, and Excel/XLOOKUP evidence.

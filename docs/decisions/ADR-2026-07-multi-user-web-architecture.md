# ADR-2026-07: Multi-User Linux Web Architecture Boundary

- Status: Proposed
- Date: 2026-07-05
- Branch: `docs/linux-web-multi-user-architecture`
- Scope: architecture documentation only

## Decision Summary

The Linux/Web pivot now has a multi-user implication. Python remains the
source-of-truth implementation language for extraction, Excel handling, audit,
comparison, jobs, and backend services. Streamlit remains useful for internal
MVP, demo, and smoke flows, but it is no longer the default final UI shape for
formal multi-user operation.

For multi-user production, the target architecture is:

- React/TypeScript frontend;
- Python FastAPI backend API;
- PostgreSQL persistence;
- background job queue for extraction, comparison, and export work;
- server-managed file storage;
- server-side locking, audit, and Excel-ready gates.

This ADR does not implement React, FastAPI, PostgreSQL, a job queue, or auth.
It records the boundary so Goal 4 and later slices do not continue to assume a
single-user Streamlit/local-file model.

Release Forecast remains `NOT_READY`.

## Context

The meeting direction changed v1 from a Windows single-operator package toward
a Linux-hosted Web workflow:

- users operate through a browser;
- users provide or confirm correct PDFs;
- automatic fiscal-year PDF judgment is not the primary v1 release path;
- EIDP extraction is compared with Copilot/NotebookLM-style external extraction;
- Excel integration uses XLOOKUP-compatible output;
- image PDFs remain exception/manual/OCR flow.

The current Linux/Web integration line has implemented:

- PDF intake;
- extraction queue;
- table-aware extraction;
- extraction review;
- normalized review report;
- master expected subset diff;
- ambiguous-key reporting.

The 2026-07-05 key-collision audit found that string-only department keys are
not stable enough for full comparison coverage. Goal 3D now reports duplicate
review/master keys as `ambiguous_key` instead of silently matching them.

## Relationship To Existing Direction

`docs/governance/technical-direction.md` remains accurate for the older
single-operator Windows/SQLite/Streamlit posture. This ADR supersedes that
default only for the Linux/Web multi-user direction.

The change is not "rewrite EIDP in React." The change is:

- keep Python as the core pipeline and backend language;
- keep Streamlit as MVP/internal console while business rules are still moving;
- make React/FastAPI/PostgreSQL the target when formal multi-user operation is
  required.

## Layer Decisions

| Layer | Decision |
| --- | --- |
| Extraction core | Keep Python modules under `src/eidp/pdf/` and `src/eidp/pipeline/` |
| Excel and XLOOKUP output | Keep Python workbook/report generation |
| Audit and comparison logic | Keep Python services and database-backed audit events |
| MVP UI | Keep Streamlit for local/internal MVP, smoke, and operator walkthroughs |
| Production multi-user UI | Target React/TypeScript |
| Backend API | Target Python FastAPI |
| Persistence | Target PostgreSQL for multi-user state |
| Temporary storage | SQLite/local JSON only for low-concurrency development and MVP |
| Long-running work | Move extraction, double-check comparison, and export to jobs |
| File storage | Server-managed filesystem first, object-store-compatible boundary later |

## Required Multi-User Contracts

Formal multi-user operation requires these contracts before release:

- every review action has `user_id`, timestamp, before/after values, version,
  and audit event;
- concurrent edits use optimistic locking or explicit row locks;
- stale writes fail with a visible conflict state rather than last-write-wins;
- PDF, external extraction files, reports, and workbooks are referenced by
  server-issued IDs, not UI-provided filesystem paths;
- long-running extraction, comparison, and workbook generation run as jobs;
- Excel-ready state is computed server-side, not by frontend state;
- `ambiguous_key`, `needs_review`, `excluded`, unresolved image/OCR tasks, and
  unresolved double-check mismatches are not comparable and not Excel-ready;
- no PDF is uploaded automatically to external Copilot/NotebookLM unless an
  owner-approved data policy exists.

## Goal 4 Boundary

Goal 4 may proceed only under this boundary:

- import operator-supplied Copilot/NotebookLM CSV/XLSX outputs;
- normalize external rows into the reviewed-row schema;
- compare only unique comparable rows;
- report `ambiguous_key`, `needs_review`, and `excluded` rows as not
  comparable;
- never mark external matches or mismatches as Excel-ready by themselves;
- do not call Copilot/NotebookLM APIs;
- do not upload PDFs externally;
- do not write final Excel.

If Goal 4 needs higher coverage, a mapping slice must come first or run in
parallel:

- show ambiguous reviewed/master rows;
- let a reviewer select the intended `master_row_id`;
- persist `program_mapping_id` or equivalent;
- audit the mapping decision.

## Consequences

Positive:

- Python extraction and Excel assets stay reusable;
- Streamlit MVP work remains useful for workflow proof;
- React can be introduced after API and state boundaries are stable;
- multi-user risks are visible before external double-check import;
- ambiguous keys cannot silently flow into comparison or Excel.

Tradeoffs:

- PostgreSQL, FastAPI, React, auth, and job workers become future engineering
  work;
- SQLite/local JSON must not be over-claimed as production multi-user storage;
- Goal 4 coverage may be lower until ambiguous mapping exists;
- release evidence must prove network, locking, audit, and owner/PI data-policy
  gates.

## Non-Goals

This ADR does not:

- implement React;
- implement FastAPI;
- implement PostgreSQL;
- implement auth or roles;
- implement a job queue;
- implement final Excel or XLOOKUP output;
- change Streamlit MVP pages;
- change Windows canary evidence;
- change release forecast to `READY` or `RC_ONLY`.

## Release Position

Release Forecast remains `NOT_READY`. Multi-user architecture direction is not
release approval. The Linux/Web release remains blocked until owner/PI sign-off,
network access proof, data-policy approval, double-check import, Excel/XLOOKUP
output, and deployment evidence exist.

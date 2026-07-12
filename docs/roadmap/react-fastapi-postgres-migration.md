# React/FastAPI/PostgreSQL Migration Roadmap

Date: 2026-07-05

Release Forecast: `NOT_READY`

This roadmap describes how EIDP can move from the current Streamlit MVP to a
formal multi-user Linux/Web system without rewriting the Python extraction
core.

## Migration Principle

Do not rewrite stable Python pipeline logic in TypeScript.

Move boundaries in this order:

1. keep Python extraction, review, diff, Excel, and audit logic;
2. make state and artifacts addressable by stable IDs;
3. expose backend APIs around existing services;
4. move persistence to PostgreSQL when multi-user writes are real;
5. replace Streamlit pages with React screens after API contracts stabilize.

## Phase 0: Current MVP

Status: in progress on `integration/linux-web-v1`.

Current capabilities:

- PDF intake;
- extraction queue;
- table-aware extraction;
- extraction review;
- normalized review report;
- master diff;
- `ambiguous_key` reporting.

Storage remains local JSON/files for the Linux/Web MVP. This is acceptable only
for low-concurrency development and workflow proof.

## Phase 1: Goal 4 On Current MVP

Goal:

- import operator-provided Copilot/NotebookLM CSV/XLSX output;
- normalize external rows;
- compare against reviewed EIDP rows.

Required constraints:

- compare only unique comparable rows;
- keep `ambiguous_key`, `needs_review`, and `excluded` not comparable;
- do not upload PDFs externally;
- do not call Copilot/NotebookLM APIs;
- do not write final Excel;
- do not claim release readiness.

This phase may still use Streamlit for operator workflow proof.

## Phase 2: API Boundary

Goal:

- introduce Python FastAPI endpoints around already-stable pipeline services;
- keep Streamlit available as internal/admin smoke UI while React is built.

Candidate endpoint groups:

- `/api/intake`;
- `/api/documents`;
- `/api/extractions`;
- `/api/reviews`;
- `/api/master-diff`;
- `/api/double-check`;
- `/api/exports`;
- `/api/audit`;
- `/api/jobs`.

Do not move business rules into React. The API should own validation,
locking, audit, and Excel-ready decisions.

## Phase 3: Persistence Upgrade

Goal:

- move multi-user business state to PostgreSQL;
- preserve local file or object-store-compatible document storage.

Minimum tables:

- `users`;
- `documents`;
- `intake_items`;
- `extraction_jobs`;
- `extraction_rows`;
- `review_decisions`;
- `master_rows`;
- `program_mappings`;
- `double_check_rows`;
- `export_runs`;
- `audit_events`.

SQLite may remain only for local development, smoke tests, or single-user demo
flows. It must not be described as the formal multi-user persistence layer.

## Phase 4: Job Queue

Goal:

- move long-running operations out of UI requests.

Job types:

- `extract_pdf`;
- `import_external_result`;
- `compare_double_check`;
- `generate_review_report`;
- `generate_xlookup_workbook`;
- `resolve_mapping_batch` if needed later.

The UI should receive `job_id`, poll job status, and display failure reasons.

## Phase 5: React UI

Goal:

- replace Streamlit operator screens with React/TypeScript screens after API
  and persistence contracts are stable.

Target screens:

- PDF intake;
- extraction queue;
- extraction review;
- ambiguous-key mapping;
- double-check comparison;
- export runs;
- audit log;
- admin/users.

React should not directly read server file paths, mutate JSON files, or compute
Excel-ready state. It should call backend APIs and render server-owned state.

## Phase 6: Multi-User Release Proof

Goal:

- prove the system is safe for the intended number of operators.

Required evidence:

- network access proof;
- authentication and role proof;
- optimistic lock or row-lock conflict proof;
- job queue failure/retry proof;
- audit event proof;
- backup/restore proof;
- owner/PI data-policy approval;
- sample corpus comparison coverage;
- Excel/XLOOKUP output gate proof.

## Deferred Work

Do not do these before the underlying contracts exist:

- full React rewrite before Goal 4 business rules are stable;
- PostgreSQL migration without a multi-user write requirement;
- object storage before server filesystem boundaries are stable;
- real-time collaboration;
- external API calls to Copilot/NotebookLM;
- final Excel/XLOOKUP output before review and double-check gates are proven.

## Next Slice

Goal 4 may proceed after this ADR if it treats `ambiguous_key` rows as not
comparable. If higher comparison coverage is required first, open an ambiguous
mapping slice before Goal 4.

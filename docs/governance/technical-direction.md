# Technical Direction

EIDP's current best-fit stack is a Python data pipeline with a Streamlit
operator UI. The project should stay on this path for v1 and v1.5 unless a
specific product requirement triggers a larger split.

## Current Stack Decision

Python remains the primary implementation language because the core work is:

- official index parsing
- URL and PDF discovery
- deterministic PDF extraction
- OCR fallback
- data cleaning and reconciliation
- SQLite and SQLAlchemy persistence
- Excel workbook generation
- CLI, diagnostics, packaging, and Windows batch launchers

This is a data-operations pipeline, not a high-concurrency web product.

## Layer Responsibilities

| Layer | Current direction |
| --- | --- |
| Core pipeline | Python 3.12+, SQLAlchemy, Pydantic, Typer |
| PDF and OCR | Python PDF libraries, optional OCR add-on |
| Excel | Python workbook generation |
| Database | SQLite for v1/v1.5, designed with PostgreSQL-compatible contracts |
| Operator UI | Streamlit for v1/v1.5 |
| UI prototype | HTML design reference only |
| Future complex frontend | React/TypeScript only after product triggers |
| Browser automation | Optional Playwright add-on, not a default runtime dependency |

Python is the engine. It does not have to be the final dashboard technology
forever.

## Streamlit Policy

Streamlit is not mandatory forever, but it is the pragmatic v1/v1.5 choice while
the product is:

- single-operator
- Windows-local
- SQLite-backed
- weekly or periodic rather than high-concurrency
- centered on task queues, PDF review, fiscal-year confirmation, manual entry,
  and Excel export

Do not migrate to React, Next.js, Tauri, PySide, Go, Java, .NET, or Node
full-stack only because the current UI feels less modern.

## React/FastAPI Upgrade Triggers

Revisit a frontend/backend split only when several of these are real production
requirements:

- multiple operators reviewing concurrently
- remote deployment
- authentication, roles, or fine-grained permissions
- PDF region annotation and field-level highlighting
- spreadsheet-like inline editing
- saved complex filters and bulk actions
- Streamlit rerun state becomes unmaintainable
- PostgreSQL and background worker orchestration become required

The likely v2 shape is:

- Python FastAPI backend
- PostgreSQL
- React or Next.js frontend
- background workers
- object storage for PDFs
- field-level audit events

## HTML Prototype Boundary

The operations-console HTML prototype is a design reference and demo artifact.
It must remain under `docs/design/operations-console-demo/`.

Allowed uses:

- visual direction
- page naming
- operator-facing Japanese copy
- UI contract seed
- implementation reference for Streamlit pages
- stakeholder demos

Forbidden uses:

- iframe the standalone HTML into Streamlit
- import `support.js` into `src/eidp`
- copy generated JavaScript into production code
- connect the prototype directly to SQLite
- treat mock numbers as fixtures or business truth
- package the prototype as the Windows operator application

Production UI remains implemented under `src/eidp/review/` unless a planned
future migration creates `src/eidp/operator_ui/`.

## Near-Term Engineering Direction

The next production UI improvements should harden the Python application rather
than replace it:

- introduce stable enums or constants for workflow states
- centralize Japanese labels
- add ViewModel boundaries for dashboard, queue, review, and export pages
- use `current_lane`, `blocking_reason`, and `next_action` consistently
- strengthen Excel-ready gates
- keep OCR and Playwright optional add-ons
- maintain append-only revisions and audit logging

## Non-Goals

- No database table rename as part of v1 governance work.
- No broad module move from `scraper/`, `pdf/`, `excel/`, or `review/` solely
  for naming cleanup.
- No Agent-Reach or generic internet-agent entry point in the operator UI.
- No production dependency on generated prototype runtime files.

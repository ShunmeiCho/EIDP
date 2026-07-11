# ADR-2026-07: Linux/Web is the EIDP v1 product

- Status: **Accepted**
- Decision date: 2026-07-11
- Implementation branch: `main`
- Release forecast: `NOT_READY` until the served-app gates pass

## Decision

EIDP v1 is a browser-accessed Web application hosted on the laboratory Linux
server. The Windows single-machine runtime, ZIP distribution, batch launchers,
and Stage 6 release gate are retired from `main`.

The historical Windows v548 implementation remains available only through Git
history and the local audit tag `windows-v548-fallback` (`c1a9690`). It is not a
fallback release lane and receives no new development.

`main` is the sole development line. It contains the former
`integration/linux-web-v1` work and the Ohara table-aware extraction core.

## Product boundary

- A business user confirms the correct official PDF and fiscal year.
- EIDP accepts PDF/ZIP/URL metadata through Streamlit.
- The server classifies text versus image PDFs, runs deterministic extraction,
  retains cell evidence, and routes exceptions visibly.
- A reviewer accepts/corrects/excludes rows.
- Reviewed rows are compared with read-only `master.xlsx` data and an optional
  externally produced extraction.
- The output remains Excel-compatible.

Automatic discovery and fiscal-year judgment remain support-only tooling. The
historical 60% strict-yield and 30% manual-workload thresholds are health
metrics, not the Linux/Web release gate.

## Current architecture

- Python 3.12 domain core and extraction worker.
- Streamlit Web UI bound to `127.0.0.1`.
- SQLite/SQLAlchemy with a POSIX application-wide single-writer lock.
- All Venus runtime state below `/home/junming/EIDP` in a project-local virtual
  environment.
- Approved internal reverse proxy/port for business-PC access.

FastAPI, React, and PostgreSQL are future options. They are introduced only
when measured multi-operator concurrency, roles, or durable job orchestration
exceeds the current Streamlit/SQLite contract.

## Preserved assets

- deterministic PDF/table extraction and field aliases;
- cell evidence and confidence routing;
- read-only master loader/diff and Excel output;
- four-table append-only fiscal-year correction;
- SQLite schema/migrations and audit outbox;
- scraper/discovery safety and data-quality logic as support tooling;
- POSIX lock, backup, diagnostics, and regression tests.

## Release consequences

Accepting the product direction does not declare the service ready. Release
still requires fresh quality results, Venus venv/start/restart proof, real LAN
browser upload/review/download evidence, image/OCR-lane policy evidence, and
backup/restore proof defined in `docs/governance/release-gates.md`.

## Superseded documents

This ADR is canonical and supersedes the earlier multi-user architecture drafts.
They must not be used as a separate v1 product definition.

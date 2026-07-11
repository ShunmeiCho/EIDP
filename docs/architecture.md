# EIDP Architecture

## Runtime topology

```text
authorized business browser
        |
        | campus LAN / approved internal endpoint
        v
internal reverse proxy or SSH-forwarded validation path
        |
        v
Streamlit 127.0.0.1:8502
        |
        +-- confirmed PDF/ZIP/URL intake
        +-- TEXT vs image/manual/OCR routing
        +-- table-grid extraction with CellEvidence
        +-- human accept/correct/exclude review
        +-- read-only master.xlsx diff
        +-- external extraction double-check
        +-- Excel-compatible report/export
        |
        v
SQLite + files below EIDP_DATA_DIR
```

The production checkout and all service-owned artifacts on Venus remain below
`/home/junming/EIDP`. The process runs in the `uv`-managed project virtual
environment and never installs into the system Python.

## Module boundaries

- `src/eidp/db/`: SQLAlchemy models, sessions, migrations, append-only audit,
  and the POSIX application lock.
- `src/eidp/pipeline/`: intake, extraction queue, review state, reconciliation,
  double-check, and report orchestration.
- `src/eidp/pdf/`: deterministic PDF/table extraction and optional OCR.
- `src/eidp/scraper/`: support-only URL/PDF discovery and safety controls.
- `src/eidp/excel/`: read-only master loading, diffs, and workbook output.
- `src/eidp/web/`: Streamlit entry point, pages, components, and Web write-lock
  adapter.
- `src/eidp/review/`: retained legacy operator views that still provide shared
  review/report functionality; migrate deliberately rather than deleting
  business logic during deployment cleanup.

## Data integrity

SQLite is valid only under the application-wide single-writer contract:

- CLI/background writes acquire `data/.lock`.
- Web writes acquire the same lock through `eidp.web.locking`.
- lock contention is surfaced and does not proceed with a write.
- revisioned business tables use append-only `revision++` updates.
- `manual_action_log` is authoritative; JSONL is an idempotent outbox.
- `data/master.xlsx` is never modified by extraction or diff code.

## Intake and review contract

1. A business user confirms the official PDF and fiscal year.
2. Intake validates metadata, safe filenames, PDF magic, hash, and lane.
3. Text PDFs enter deterministic extraction; image PDFs enter the explicit
   manual/OCR exception lane.
4. Every extracted metric carries source evidence.
5. A reviewer accepts, corrects, excludes, or leaves the row unresolved.
6. Reviewed rows are compared with the read-only master and optional external
   extraction.
7. Only reviewed, policy-compliant values become export candidates.

## Security boundary

- Streamlit remains loopback-bound.
- LAN exposure is handled by approved network infrastructure, not `0.0.0.0`.
- Secrets live in a private `.env`, never Git.
- Upload limits, authentication/allowlist policy, and retention must be decided
  before multi-user production use.
- Source URLs and untrusted PDF/HTML content never bypass existing SSRF,
  throttling, or validation controls.

## Evolution

The current release is Streamlit + SQLite. FastAPI/React/PostgreSQL become
appropriate only after a measured multi-operator requirement exceeds the
single-writer design. The Python extraction/audit/Excel core remains reusable.

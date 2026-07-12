# EIDP repository guidance

## Product definition

EIDP v1 is a Linux-hosted internal Web application for Japanese vocational
school disclosure data. Users work through a browser; the server performs PDF
parsing, optional OCR routing, extraction, evidence review, comparison, audit,
and Excel-compatible output.

- Single mainline: `main`.
- Deployment root: `venus:/home/junming/EIDP`.
- Remote safety boundary: never edit, create, delete, or install outside
  `/home/junming/EIDP`.
- Runtime isolation: `uv` project environment at `/home/junming/EIDP/.venv`.
- Streamlit binds `127.0.0.1`; LAN users enter through an approved internal
  reverse proxy/port.
- SQLite remains the v1 store under a strict single-writer lock. PostgreSQL is
  reconsidered only after a real concurrent-operator requirement exists.
- Automatic PDF discovery and target-year judgment are support-only health
  indicators. Human-confirmed correct PDFs are the v1 intake boundary.

The Windows ZIP/runtime/Stage 6 product is retired from `main`. Historical
evidence is available at the `windows-v548-fallback` tag.

## Commands

```bash
uv sync --extra dev --extra scraper-basic --extra pdf
uv run streamlit run src/eidp/web/app.py --server.address 127.0.0.1 --server.port 8502
uv run ruff check .
uv run --with bandit bandit -q --severity-level high -r src/eidp scripts
uv run mypy src
EIDP_DATABASE_URL='sqlite:///./data/test_audit.sqlite3' uv run pytest
```

## Core contracts

### Append-only fiscal-year correction

`src/eidp/pipeline/fiscal_year_override.py` and `src/eidp/db/models.py` define
the four-table contract. `DepartmentYearly`, `SupportRecipient`, and
`SchoolYearStatus` corrections create a new `revision` and change `is_current`;
they are never silently updated in place. Collateral demotion emits a
`manual_action_log` event.

### Audit

`manual_action_log` is authoritative. `data/audit/manual-actions.jsonl` is an
idempotent after-commit outbox keyed by `action_id`. Never delete
`data/eidp.sqlite3`, `data/audit/manual-actions.jsonl`, or `data/master.xlsx`.

### Single writer

`src/eidp/db/locking.py` uses POSIX `fcntl.flock` on `data/.lock`. CLI writes
must call `_require_app_lock(...)`. Linux/Web mutation paths use
`src/eidp/web/locking.py::acquire_web_write_lock` and surface `LockBusyError`
without writing.

### App root

`EIDP_APP_ROOT` is the first-priority root. Installed wheels fail closed when
it is absent. `deploy/linux/run_web.sh` sets it from the repository root, while
the Venus environment sets it explicitly to `/home/junming/EIDP`.

`EIDP_TARGET_FISCAL_YEAR` is a red line: the settings UI never writes it to
`.env`; the default rolls over through `current_fiscal_year()`.

### Extraction and output

- Table-grid extraction keeps cell evidence (page/table/row/column).
- `data/master.xlsx` is read-only ground truth.
- Confidence thresholds remain 0.85/0.70/0.50 unless explicitly configured.
- Image-only PDFs enter the manual/OCR lane and are never silently accepted.
- Final output requires reviewed values and preserves Excel/XLOOKUP keys.

## Engineering goals

- G1 correctness: reviewed extraction/master diff is explicit and regression
  tested; the served-app workflow preserves exact expected row/cardinality
  invariants.
- G2 contract integrity: append-only revisions, file-hash uniqueness, and audit
  dedup remain intact.
- G3 data quality: extraction/reconciliation failures are visible queues, not
  implicit success.
- G4-G8 engineering: small typed modules, observable failures, deterministic
  tests, optional extractors, and all deployment paths under `EIDP_*` config.
- G9-G12 operations: backup/restore proof, idempotent writes, human review, and
  measured runtime/storage workload.
- G13 security: no secrets in Git, no public Streamlit bind, safe uploads, and
  no remote writes outside the authorized root.
- G14 release integrity: protected `main`, green quality checks, served-app
  gate, reproducible lockfile.
- G15 business: an authorized business PC completes an intranet browser cycle
  and produces a reviewed Excel-compatible result.

PRs include `Goals: G<x>, G<y>`.

## Validation order

1. Unit/integration tests, Ruff, Bandit, mypy.
2. Linux/Web chain E2E with exact extraction/review invariants.
3. Fresh Venus checkout/venv/dependency smoke inside `/home/junming/EIDP`.
4. Streamlit loopback health and restart proof.
5. Authorized LAN browser upload/review/download smoke.
6. Backup/restore and operator acceptance evidence.

## Key documents

- `docs/architecture.md`
- `docs/decisions/ADR-2026-07-linux-web-pivot.md`
- `docs/governance/release-gates.md`
- `docs/reports/current-release-status.md`
- `docs/runbooks/linux-web-dev-run.md`
- `deploy/linux/server-requirements.md`

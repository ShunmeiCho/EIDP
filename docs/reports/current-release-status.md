# EIDP Current Release Status

Updated: 2026-07-11
Branch: `main`
Product: Linux-hosted internal Web application
Release Forecast: `NOT_READY`

## Current state

- Local `main` contains the Linux/Web integration baseline originally assembled
  at `feb2839`, including the Ohara table-grid core and five-stage Streamlit
  workflow.
- Windows runtime/ZIP/batch launchers and Stage 6 release machinery are retired
  from `main`. The historical audit anchor is `windows-v548-fallback` at
  `c1a9690`.
- Extraction, Excel, SQLite, append-only revisions, audit, discovery support,
  data-quality reports, and POSIX locking remain active.
- The Web launcher now sets `EIDP_APP_ROOT`; Web mutation paths share the
  application lock and redirect runtime caches/temporary files below the app
  root.

## Fresh local verification

- `uv lock --check`: passed.
- `uv run ruff check .`: passed with the explicit legacy-research exclusions
  recorded in `pyproject.toml`.
- high-severity Bandit across `src/eidp` and all `scripts`: passed.
- `uv run mypy src`: passed for 129 source files.
- full pytest with coverage: 1730 passed, 8 skipped; 82.01% coverage.
- Streamlit PDF-intake AppTest covers traversal-safe filename storage and the
  operator-visible `LockBusyError` path.
- tracked real-PDF Linux/Web E2E: exact 28 departments, 84 metric rows, and 3
  independent parenthesized course siblings.
- local Streamlit loopback health: `127.0.0.1` returned `ok`.

## Evidence still required

- Fresh Venus install/start/restart proof using the repository-local virtual
  environment under `/home/junming/EIDP`.
- Real internal-network browser upload/review/download smoke from a business PC.
- LAN accessibility through the approved loopback proxy or tunnel boundary.
- Served-app image/OCR-lane browser evidence.
- Backup/restore and operator acceptance evidence.
- Web review decisions connected transactionally to `manual_action_log` and
  the idempotent audit outbox.

No GA/READY claim is permitted until the Linux/Web release gates are satisfied.

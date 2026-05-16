# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

EIDP (Education Institution Data Pipeline) — automated enrollment data collection for Japanese 専門学校 (vocational schools). Ships as a Windows ZIP for one non-technical operator. Streamlit UI local-only (`127.0.0.1`). SQLite backend with WAL.

- Final target: Windows PC, double-click `.bat` launchers, no SSH / SQL / terminal access by operator.
- Pipeline: PDF discovery → target-FY judgment → ingest (pdf_parse / OCR / manual) → weekly Excel export.
- Venus crontab path is archived (`deploy/legacy-venus/`), not live.

## Common commands

```bash
# Dev install
uv sync --extra dev --extra scraper-basic --extra pdf

# Test suite (use a temp SQLite to avoid clobbering data/)
EIDP_DATABASE_URL='sqlite:///./data/test_audit.sqlite3' uv run pytest -q

# Single test file / case
uv run pytest tests/unit/test_fiscal_year_override.py -q
uv run pytest tests/unit/test_fiscal_year_override.py::test_override_audits_collateral_target_current_demotes -q

# Static checks
uv run mypy src
uv run ruff check src scripts/build_windows_zip.py scripts/run_non_windows_release_gates.py

# Run the Streamlit UI locally
uv run streamlit run src/eidp/review/app.py

# Build the Windows ZIP from Mac/Linux
uv run python scripts/download_windows_runtime.py
uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-vXXX.zip --latest-alias

# Mac-side release gate (must pass green before SCP to Win VM)
uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-vXXX.zip --json

# Retroactive Excel algorithm proof (compare exported workbook vs sample/master.xlsx historical column)
uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-vXXX.zip \
  --retroactive-excel-reference sample/master.xlsx --retroactive-fiscal-year 2025

# Distribution verifier (use before SCP to Windows)
uv run python scripts/verify_windows_distribution.py dist/eidp-windows-vXXX.zip --json
```

CI (GitHub Actions, `.github/workflows/ci.yml`): ruff, bandit (high-severity), mypy, pytest. Run locally before pushing.

## Architecture — read these before changing pipeline / DB / UI code

`docs/architecture.md` is the source of truth. Critical contracts:

### Four-table append-only fiscal_year override contract
Files: `src/eidp/pipeline/fiscal_year_override.py`, `src/eidp/db/models.py:171-280` (SR / SYS / DepartmentYearly).
- `Document.fiscal_year` is physically rewritten; `Document.fiscal_year_override` records operator choice.
- `DepartmentYearly`, `SupportRecipient`, `SchoolYearStatus` rewrite via **revision++ append** with `is_current` partial index. **Never** in-place `.first()` update.
- `effective_fiscal_year()` is for override internals + UI display **only**. `coverage`, `excel/exporter`, normal `ingest` read the physical `fiscal_year`.
- Collateral demotion (target FY current row owned by different document) must emit `manual_action_log` audit row (`operation="collateral_demote"`).

### Confidence cascade
File: `src/eidp/extraction_confidence.py`. Composite = F1×0.4 + F2×0.4 + F3×0.2. Thresholds 0.85 / 0.70 / 0.50 with `EIDP_CONFIDENCE_AUTO/REVIEW/REJECT` env overrides read **per call** (`thresholds_from_env()`). DB column is `Numeric(4,3)` after `9497b2c7` to prevent boundary rounding drift. `ALLOWED_METHODS` = `{"pdf_parse", "ocr_tesseract", "ocr_paddleocr", "manual"}`.

### DB-authoritative audit + JSONL outbox
Files: `src/eidp/db/audit.py`, `src/eidp/db/audit_outbox.py`.
- `manual_action_log` is primary. `data/audit/manual-actions.jsonl` is an **after-commit outbox** keyed by `action_id` (UUID4).
- Flush is idempotent across DB-restore replay. Archive symlinks are skipped to avoid double-flush.

### Cross-process lock contract
File: `src/eidp/db/locking.py`. Shared `data/.lock` via `msvcrt.locking` (Win) / `fcntl.flock` (POSIX).
- Every CLI write command must call `_require_app_lock(owner=...)` (see `cli.py`).
- Every UI write must `acquire_lock(...)` and surface `LockBusyError` as a "週次処理中" banner.
- `tests/unit/test_cli_write_lock_contract.py` is the AST gate — extending write helpers requires adding to `WRITE_HELPER_CALLS` (or use decorator registry once introduced).

### App root resolution
File: `src/eidp/config.py:46-63`. Order: `EIDP_APP_ROOT` env → cwd heuristic → `Path(__file__).parents[2]`. If running from a wheel under `site-packages` without `EIDP_APP_ROOT`, **raise** rather than silently writing under `.venv`. All `.bat` launchers set `cd /d "%~dp0\.." && set EIDP_APP_ROOT=%CD%`.

`EIDP_TARGET_FISCAL_YEAR` is a **red line**: never written to `.env` from the settings UI. Default rolls over by calendar via `current_fiscal_year()`.

### Streamlit pages
Sidebar mounts 12 pages from `src/eidp/review/app.py` + `_pages/*`. `unsafe_allow_html=True` sites all pre-escape with `html.escape(..., quote=True)`. The server must bind `127.0.0.1` (see `scripts/launch.bat`, `src/eidp/cli_tools.py`).

### Untrusted-content boundaries
- School HTML / PDF text → UNTRUSTED. RCA prompt builder (`src/eidp/scraper/discovery_rca_packet.py`) wraps in nonce-fenced `UNTRUSTED_EVIDENCE_JSON_*` markers using `secrets.token_hex(8)`.
- All outbound URLs pass `_is_safe_url` (`src/eidp/scraper/url_discovery.py`) with DNS-resolved private/loopback/link-local rejection.
- `discovery_gold_set` payloads validated via `jsonschema.Draft202012Validator` at load.

## Working rules

- **Mac fix only**: every Windows bug fix must be Mac-side TDD red → green → refactor → rebuild ZIP → re-deploy. Never edit code on the Windows operator PC.
- **Red-line files**: never delete `data/eidp.sqlite3`, `data/audit/manual-actions.jsonl`, `data/master.xlsx`. `uninstall.bat` and `stage6_residual_cleanup.py` honor this.
- **Append-only**: no `.commit()` with in-place mutation on revisioned tables. Use `with_for_update()` + revision++ insert.
- **No raw SQL with user input**: SQLAlchemy ORM only. Vetted module constants (`IS_CURRENT_TRUE_SQL`, `FISCAL_YEARS`) may interpolate via f-string in `text()`.
- **No `--no-verify` / `--no-gpg-sign` / `--allow-dirty` for release builds.** `BUILD_INFO.json` `git_commit="unknown"` is rejected by both build and verifier.
- **Test-first**: new write helper → write `test_*_returns_lock_busy_without_writing` mirroring `tests/unit/test_operator_proposals.py`.
- **Logging**: `from eidp.logging_config import configure_logging`; entry points call once. Use `log.exception` (not `log.warning(error=str(e))`) for non-expected errors.
- **No timeline output** in plans / runbooks unless user explicitly requests time estimates.

## CLI surface

`pyproject.toml` `project.scripts.eidp = "eidp.cli:main"`. Subcommand modules:
- `cli.py`: ingest, discover, weekly-update, db-bootstrap, db-backup, prefecture-aggregate, audit-flush, seed-discovery-gold-sites, fiscal_year_override, populate-reviews.
- `cli_discovery.py`: discovery-gold-set, discovery-gold-run-plan, eval-discovery-gold, RCA packet.
- `cli_reports.py`: report-coverage, report-extraction, report-gaps, report-ship-readiness.
- `cli_tools.py`: db-info, export-excel, export-competition-excel, diff-excel (with `--business-values --fail-on-diff`), eval-pdf, launch UI.

## Validation layers (Sprint 8 v6 plan)

| # | Layer | Gate |
|---|---|---|
| 1 | Mac `pytest` + `mypy` + `ruff` + `bandit` | Business-logic only |
| 2 | Windows VM offline `first_setup.bat` + `launch.bat` | Setup completes |
| 3 | Win VM `weekly_run.bat` + lock + `last_run.json` | Weekly succeeds |
| 4 | Win VM Excel + occupancy error (Japanese banner) | Excel ships |
| 5 | Win VM OCR add-on + R8 override + 4-table audit | OCR pipeline |
| 6 | Operator PC E2E (real R8 cycle, R7 retroactive dry-run first) | **v1.0 ship gate** |

Mac side has retroactive proof tooling (`scripts/run_retroactive_excel_matrix.py`) that diffs FY 2023/2024/2025 exports against `sample/master.xlsx` historical columns — provides algorithm correctness independent of R8 release timing.

## Key docs

- `docs/architecture.md` — full architecture (Windows layout, 4-step pipeline, contracts)
- `docs/plans/2026-05-04-sprint8-win-deployment.md` — Sprint 8 v6 plan
- `docs/runbooks/eidp-windows.md` — operator-facing
- `docs/runbooks/eidp-non-windows-release-gates.md` — Mac release gate
- `docs/runbooks/eidp-retroactive-fy-validation.md` — algorithm proof via retroactive Excel diff
- `docs/runbooks/eidp-operator-e2e-template.md` — Stage 6 KPI template
- `docs/reports/current-release-status.md` — latest ZIP / SHA256 / verifier state

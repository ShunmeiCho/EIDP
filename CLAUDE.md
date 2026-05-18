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

## Engineering Goals (G1–G15)

5 categories, 15 goals. Each has a measurable target and current phase. Plans, PRs, and sprint reviews track progress against these. "高性能・稳定・轻量化" alone is shallow — these 15 axes are what make EIDP production-grade.

### Results

- **G1 Correctness** — retroactive matrix FY2023/2024/2025 diff vs `sample/master.xlsx` = `0`; strict target PDF auto-yield (Excel-producing) ≥ `60%` at mature year; alembic head consistency check passes. [v1.0]
- **G2 Contract integrity** — 4-table append-only `revision++` violations = `0`; `file_hash` UNIQUE violations = `0`; audit JSONL ↔ `manual_action_log` dedup = `100%`. [v1.0]
- **G3 Data quality** — `school` unmatched < `5%`; no single `discovery_rejections` bucket dominates (each < `30%`); `parse_failed` / `image_only` / `review_pending` routed to operator queue (never silently accepted). [v1.0–v1.1]

### Engineering

- **G4 Maintainability** — each `src/eidp/*.py` < `800` lines (current debt: `pdf_discovery.py` 3494, `operator_pages.py` 2994 — split in v1.2); new discovery method onboarding < 1 dev-day; operator-UI test coverage ≥ `70%`. [v1.1–v1.2]
- **G5 Observability** — `/health/full` aggregator endpoint (DB + lock + disk + last_run + audit); `log.exception` enforced for non-expected errors (no `log.warning(error=str(e))`); `silent_failure_hunter` runs in CI nightly. [v1.1]
- **G6 Testability** — `tests/integration/` carries real on-disk SQLite + WAL contract tests; chaos tests for `kill -9 mid-run` / network partition / disk full / lock starvation; every CLI write has `--dry-run`. [v1.1–v1.3]
- **G7 Extensibility** — `DEFAULT_METHODS` becomes a plugin registry; ingest stages are an insertable chain; LLM addon is optional with `--no-llm` deterministic flag. [v1.2]
- **G8 Configurability** — every hard-coded threshold (60 / 30 / 0.85 / 0.70 / 0.50) moves to `ship_gate_contract.py` or `extraction_confidence.py` config; every path / timeout / batch_size / rate_limit reachable via `EIDP_*` env. **Red line**: `EIDP_TARGET_FISCAL_YEAR` never written to `.env` from settings UI. [v1.1]

### Operations

- **G9 Recoverability** — nightly `db-backup → fake-corrupt → restore → integrity_check` drill; crash-dump auto-collect → bug bundle → GitHub Issue (Phase 2 from `bug_signals/`); recovery time objective ≤ `30 min` for documented failure modes; `v(N-1)` lane retained side-by-side for fallback. [v1.1–v1.2]
- **G10 Idempotency + fault tolerance** — every write helper has a `test_*_returns_lock_busy_without_writing` (enforced by `WRITE_HELPER_CALLS` AST gate); same `file_hash` re-insert → UNIQUE conflict → graceful retry; same `action_id` re-flush → dedup; weekly mid-batch crash → resume from last WAL-committed txn. [v1.0–v1.1]
- **G11 Scheduling + human-in-loop** — Windows Task Scheduler retry-on-failure explicit (default Win = no retry); confidence < `0.70` → `review_pending` queue; `image_only` without OCR add-on → `image_pending` queue + UI banner; high-risk operator actions require two-stage confirm dialog. [v1.0–v1.1]
- **G12 Cost / SLO** — weekly run wall-clock < `30 min`; operator manual workload ≤ `30%` of `target_missing` schools; Streamlit cold-start < `2 s`; single-weekly bandwidth < `2 GB` (≈ `2418` schools × < `1 MB`); audit/log monthly growth < `100 MB`. [v1.1]

### Security

- **G13 Credentials / secrets / PII** — bandit high-severity = `0`; no secrets in logs (`silent_failure_hunter` + nightly secret-scan); no hard-coded `/Users/` or `C:\Users\<name>` paths in tracked code; Streamlit binds `127.0.0.1` only. [v1.0]
- **G14 Release integrity** — `BUILD_INFO.json` rejected if `git_commit="unknown"` or `git_dirty=true`; SHA256 sidecar required; cosign / sigstore signing (v1.2); branch protection on `main` + `sprint8-handoff-finalize` requires `Python quality gates` + `Ship gate contract` checks (already enabled). [v1.0–v1.2]

### Business

- **G15 Business KPI** — operator real-cycle ≥ `1` per quarter (production validation); owner sign-off required before any `v1.x` tag (no auto-tag); manual workload ≤ `30%` of `target_missing` measured monthly; Excel-producing yield ≥ `60%` at mature FY. [v1.0]

### Phase mapping

| Phase | Primary goals landing |
|---|---|
| **v1.0** (current ship) | G1 / G2 / G3 (partial) / G10 (partial) / G11 (partial) / G13 / G14 (branch protection) / G15 (initial owner cycle) |
| **v1.1** (stability foundation) | G5 / G6 (integration tests) / G8 / G9 (backup drill) / G11 / G12 |
| **v1.2** (operational maturity) | G4 (file split) / G7 (plugin registry) / G9 (auto-recovery) / G14 (cosign) |
| **v1.3** (chaos hardening) | G6 (kill -9 / disk-full / partition) / G9 (drill expansion) |
| **v2.0** (algorithm + UX) | G3 (LLM-assist) / G6 (full chaos) / G7 (multi-agent) |

PRs add a single line: `Goals: G<x>, G<y>` (e.g. `Goals: G1, G10`) so sprint reviews can roll up. Plans place each task under the relevant G.

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

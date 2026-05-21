# Sprint 8 Windows Deployment Implementation Log

Status: In progress; local implementation through 8.9 docs is complete, external
Windows gates remain.
Last updated: 2026-05-05

## Objective

Move EIDP's operational target from Venus to a one-operator Windows PC:

- unzip the distribution;
- double-click setup / launch / weekly scripts;
- complete the four business steps in Streamlit;
- keep SQLite, audit, confidence, OCR, and Excel behavior consistent.

## Completed Local Phases

### 8.1 SQLite schema contract

Delivered before this log:

- SQLite bootstrap
- partial index support
- null-safe department expression index
- SQLite PRAGMAs
- Alembic stamp-head path

### 8.2 fiscal_year 4-table contract

Delivered before this log:

- `Document.fiscal_year_override`
- append-only revisions for `DepartmentYearly`, `SupportRecipient`, and
  `SchoolYearStatus`
- current-read helpers
- DB-authoritative `manual_action_log`
- JSONL audit outbox with dedup
- `confidence_breakdown` columns

### 8.3 prefecture aggregator

Delivered before this log:

- production module under `src/eidp/scraper/prefecture_aggregator.py`
- dry-run/apply CLI safety
- Saitama hyperlink annotation path

### 8.4 operator UI

Delivered before this log:

- manual entry contract
- shared lock
- PDF manual-entry page
- R8 override page
- Excel preview page
- audit log page

### 8.5.a Mac-side Windows packaging

Delivered before this log:

- app-root resolution
- Python runtime download script
- Windows wheelhouse checks
- `.bat` launchers
- runtime pin correction

### 8.6 OCR + confidence

Delivered before this log:

- `src/eidp/extraction_confidence.py`
- confidence gating in ingest
- Tesseract wrapper and runtime detection
- UI confidence display
- OCR availability banner
- queue-depth dashboard

### 8.7.a weekly runner Windows hardening

Current worktree adds:

- app-root anchored weekly paths;
- shared `data/.lock` acquisition;
- compact `data/output/last_run.json`;
- failure `last_run.json` write;
- `logs/run-*.log` ringbuffer pruning;
- `weekly_run.bat` locale-safe datestamp via PowerShell;
- `.bat` exit-code preservation across `endlocal`;
- UTF-8 environment variables for `first_setup.bat`, `launch.bat`, and
  `weekly_run.bat`;
- default fiscal year from `settings.target_fiscal_year`;
- tests in `tests/unit/test_r8_rediscovery_weekly.py` and
  `tests/unit/test_windows_packaging_spike.py`.

### 8.7.b existing-docs migration

Current worktree adds:

- `scripts/migrate_pg_to_sqlite.py`
- idempotent SQLAlchemy table copy from source DB to target SQLite
- primary key preservation
- revision/is_current preservation
- target dialect guard requiring SQLite
- tests in `tests/unit/test_pg_to_sqlite_migration.py`

The operator PC may still start with empty documents. This migration is a dev
tool for preserving the existing 116-doc corpus when needed.

### 8.7.c OCR add-on packaging

Current worktree adds:

- `scripts/build_ocr_addon_zip.py`
- required layout:
  - `ocr-addon/tesseract/tesseract.exe`
  - `ocr-addon/tessdata/jpn.traineddata`
- add-on manifest with file size and SHA-256
- tests in `tests/unit/test_ocr_addon_packaging.py`

### 8.7.d Playwright add-on packaging

Current worktree adds:

- `scripts/build_playwright_addon_zip.py`
- required layout:
  - `playwright-addon/wheelhouse/`
  - `playwright-addon/ms-playwright/`
- add-on manifest with file size and SHA-256
- tests in `tests/unit/test_playwright_addon_packaging.py`

The core ZIP remains HTTP-first. Playwright is optional.

### 8.7.e distribution verifier

Current worktree adds:

- `scripts/_packaging_lib.py`
- `scripts/windows_path_safety.py`
- `scripts/check_windows_paths.py`
- `scripts/verify_windows_distribution.py`
- `scripts/validate_windows_install.py`
- `scripts/validate_install.bat`
- core ZIP verification for runtime, project wheel, wheel ABI/platform,
  `.bat` launchers, migrations, runbook, and source layout
- core ZIP includes `scripts/validate_install.bat` and `scripts/validate_windows_install.py` so VM checks can run from the extracted ZIP
- Windows path safety verification for case-insensitive collisions,
  reserved device names, and parent-directory entries
- OCR add-on verification for Tesseract, `jpn.traineddata`, and manifest
- Playwright add-on verification for browser files, Playwright wheel, and
  manifest
- JSON output containing each ZIP's `sha256` and `size_bytes` for internal
  file-server distribution records
- extracted install validation for post-setup and post-weekly evidence
- `after-weekly` validation requires `last_run.status=success`
- repository/worktree path safety validation for Windows case collisions and
  reserved names
- tests in `tests/unit/test_windows_distribution_verifier.py`
- tests in `tests/unit/test_windows_install_validator.py`
- tests in `tests/unit/test_windows_path_safety.py`

Simplify pass follow-up:

- `scripts/_packaging_lib.py` is the shared SHA-256 / payload-walk helper for
  add-on builders and the distribution verifier;
- `scripts/migrate_pg_to_sqlite.py` streams source rows with `yield_per`,
  batches inserts, preloads target primary keys once, and routes dry-run
  through `bootstrap_sqlite`;
- `scripts/run_r8_rediscovery_weekly.py` reports log-prune failures instead
  of swallowing `OSError`, and the public `run_weekly` wrapper no longer uses
  self-recursion to take the lock.

### 8.8 runbooks

Current worktree adds:

- `docs/runbooks/eidp-windows.md`
- `docs/runbooks/eidp-windows-vm-validation.md`
- `docs/runbooks/eidp-operator-e2e-template.md`

### 8.9 Venus archive and architecture docs

Current worktree adds/updates:

- `deploy/legacy-venus/`
- archived notice in `docs/runbooks/eidp-r8-rediscovery.md`
- `docs/architecture.md`
- `docs/plans/future-v2-roadmap.md`
- `docs/plans/future-natural-language-query.md`
- `docs/plans/2026-05-05-sprint8-release-gate-audit.md`
- `docs/plans/2026-05-05-sprint8-handoff.md`
- `docs/runbooks/eidp-operator-e2e-template.md`
- superseded notice in `docs/plans/2026-04-11-eidp-design.md`
- `README.md`
- Windows SQLite defaults in `.env.example`

Archive integrity check:

- `deploy/legacy-venus/systemd/*` matches the deleted HEAD systemd files
  byte-for-byte;
- `deploy/legacy-venus/run_r8_rediscovery_cron.sh` matches the deleted HEAD
  cron wrapper byte-for-byte;
- `deploy/legacy-venus/cron/*` intentionally rewrites only self-reference
  paths from `deploy/cron/...` and `scripts/run_r8_rediscovery_cron.sh` to the
  archived `deploy/legacy-venus/...` locations.

## Current Verification Evidence

Latest local verification:

```text
UV_CACHE_DIR=/private/tmp/eidp-uv-cache uv run pytest tests/unit -q
=> 593 passed, 5 warnings

git diff --check
=> clean
```

Focused verification:

```text
tests/unit/test_r8_rediscovery_weekly.py
tests/unit/test_windows_packaging_spike.py
tests/unit/test_pg_to_sqlite_migration.py
tests/unit/test_ocr_addon_packaging.py
tests/unit/test_playwright_addon_packaging.py
tests/unit/test_windows_distribution_verifier.py
tests/unit/test_windows_install_validator.py
tests/unit/test_config.py
```

Release-gate audit:

```text
docs/plans/2026-05-05-sprint8-release-gate-audit.md
=> maps Sprint 8 objective to local artifacts, verification evidence,
   and remaining external gates

docs/plans/2026-05-05-sprint8-handoff.md
=> recovery patch path, verification commands, suggested Lore commit split,
   and remaining external gates
```

Distribution verifier:

```text
UV_CACHE_DIR=/private/tmp/eidp-uv-cache uv run pytest tests/unit/test_windows_distribution_verifier.py -q
=> 22 passed

UV_CACHE_DIR=/private/tmp/eidp-uv-cache uv run pytest tests/unit/test_windows_path_safety.py -q
=> 6 passed

UV_CACHE_DIR=/private/tmp/eidp-uv-cache uv run python scripts/check_windows_paths.py
=> OK: all paths are Windows-safe
=> checked_paths: 246

UV_CACHE_DIR=/private/tmp/eidp-uv-cache uv run ruff check scripts/verify_windows_distribution.py tests/unit/test_windows_distribution_verifier.py
=> All checks passed

UV_CACHE_DIR=/private/tmp/eidp-uv-cache uv run mypy scripts/verify_windows_distribution.py
=> Success: no issues found in 1 source file

UV_CACHE_DIR=/private/tmp/eidp-uv-cache uv run pytest tests/unit/test_windows_install_validator.py -q
=> 12 passed

UV_CACHE_DIR=/private/tmp/eidp-uv-cache uv run mypy scripts/validate_windows_install.py
=> Success: no issues found in 1 source file
```

Artifact smoke verification:

```text
scripts/build_windows_zip.py --skip-download --skip-runtime
=> /private/tmp/eidp-zip-smoke/eidp-windows-smoke.zip
=> required_missing: []
=> required paths present: README.md, docs/runbooks/eidp-windows.md,
   scripts/weekly_run.bat, scripts/run_r8_rediscovery_weekly.py,
   alembic.ini, requirements-windows.txt, wheelhouse/*.whl

scripts/build_windows_zip.py assemble_zip fixture + scripts/verify_windows_distribution.py
=> /private/tmp/eidp-zip-wrapper-smoke/eidp-windows.zip
=> OK core, entry_count=81, wheel_count=2
=> includes scripts/validate_install.bat, scripts/validate_windows_install.py,
   and scripts/launch.bat for VM-side evidence checks

scripts/build_ocr_addon_zip.py
=> /private/tmp/eidp-ocr-addon-smoke/eidp-ocr-addon-smoke.zip
=> required_missing: []
=> manifest_files: 3
=> required paths present: ocr-addon/tesseract/tesseract.exe,
   ocr-addon/tessdata/jpn.traineddata, ocr-addon/MANIFEST.json

scripts/build_playwright_addon_zip.py
=> /private/tmp/eidp-playwright-addon-smoke/eidp-playwright-addon-smoke.zip
=> required_missing: []
=> manifest_files: 4
=> required paths present: playwright-addon/wheelhouse/playwright-*.whl,
   playwright-addon/ms-playwright/**/chrome.exe,
   playwright-addon/MANIFEST.json

scripts/build_*_addon_zip.py + scripts/verify_windows_distribution.py integrity smoke
=> /private/tmp/eidp-addon-integrity-smoke/eidp-ocr-addon-windows.zip
=> OK ocr-addon, entry_count=4, manifest_files=3
=> /private/tmp/eidp-addon-integrity-smoke/eidp-playwright-addon-windows.zip
=> OK playwright-addon, entry_count=3, manifest_files=2
=> verifier checks manifest path, size, sha256, duplicate manifest paths,
   unlisted ZIP payloads, and duplicate ZIP entries

scripts/verify_windows_distribution.py .bat contract checks
=> rejects stale launch.bat without exit-code capture
=> rejects weekly_run.bat if locale-dependent %DATE:~ parsing reappears
=> rejects uninstall.bat if it tries to delete data with rmdir/del/erase/rd
=> verifies packaged first_setup/launch/weekly/validate_install UTF-8 and app-root anchors

scripts/verify_windows_distribution.py Python entrypoint checks
=> rejects stale validate_windows_install.py missing --require-playwright-addon
=> rejects run_r8_rediscovery_weekly.py if export_excel reappears
=> verifies packaged validator + weekly runner expose VM gate contracts
```

These tests prove local business logic, packaging shape, and static Windows
contracts. They do not prove actual Windows execution.

## Known Blockers

### Git write lock

The current execution environment cannot write under `.git/`:

```text
touch .git/codex-write-test
=> Operation not permitted
```

Therefore the current worktree is verified but not committed.

### Windows VM gate

The following remain unverified until a Windows VM is available:

- `first_setup.bat`
- `launch.bat`
- `weekly_run.bat`
- Task Scheduler registration
- offline wheel install
- PyMuPDF/pdfplumber Windows imports
- Excel file-lock behavior
- OCR add-on subprocess execution
- Defender / SmartScreen behavior

Use `docs/runbooks/eidp-windows-vm-validation.md` as the execution checklist.

### Real operator PC gate

v1.0 cannot be declared until one real operator PC completes one R8 cycle with
owner sign-off.

## Next Actions

1. Commit the current worktree from an environment that can write `.git/`.
2. Build the final Windows ZIP with real runtime and wheelhouse.
3. Run Windows VM validation Stage 2 through Stage 5c.
4. Fold VM findings into runbook and code.
5. Run operator PC E2E.

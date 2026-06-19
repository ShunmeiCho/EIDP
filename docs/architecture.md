# EIDP Architecture

Status: Sprint 8 Windows deployment architecture
Updated: 2026-05-05

## 1. v1.0 Goal

EIDP v1.0 is a Windows-PC application for one nontechnical operator. The
operator receives a ZIP, extracts it, runs `.bat` files by double-clicking, and
uses the Streamlit UI to complete the four business steps:

1. PDF collection
2. Target fiscal-year judgment
3. Database transcription from PDF / OCR / manual input
4. Weekly Excel aggregation

The final v1.0 environment is not Venus. Sprint 7 Venus crontab/systemd assets
are archived under `deploy/legacy-venus/` and are not the live deployment path.

## 2. Windows Deployment Layout

```text
C:\EIDP\
├─ runtime\
│  ├─ python\
│  └─ uv.exe
├─ wheelhouse\
├─ ocr-addon\
│  ├─ tesseract\tesseract.exe
│  └─ tessdata\jpn.traineddata
├─ src\eidp\
├─ scripts\
│  ├─ first_setup.bat
│  ├─ launch.bat
│  ├─ weekly_run.bat
│  └─ uninstall.bat
├─ data\
│  ├─ eidp.sqlite3
│  ├─ master.xlsx
│  ├─ pdfs\
│  ├─ output\
│  ├─ audit\manual-actions.jsonl
│  └─ .lock
└─ logs\
```

All runtime paths are rooted at `EIDP_APP_ROOT`. The `.bat` launchers set
`EIDP_APP_ROOT=%CD%` after `cd /d "%~dp0\.."`, so Explorer, Task Scheduler, and
terminal launches all resolve the same app root.

## 3. Four-Step Pipeline

### Step 1: PDF Collection

Primary sources:

- Prefecture aggregators, via `src/eidp/scraper/prefecture_aggregator.py`
- Existing school-site PDF discovery
- Manual URL/PDF intervention through the UI

The prefecture aggregator uses parse -> match -> writer-plan -> apply. Writes
to `school_site` use `discovery_method='prefecture_aggregator'` so this source
stays distinct from historical discovery methods.

### Step 2: Target-Year Judgment

Automatic extraction records a physical `Document.fiscal_year`. Operator
correction uses `pipeline/fiscal_year_override.py`.

Override rule:

- `Document.fiscal_year` is physically rewritten to the target fiscal year.
- `Document.fiscal_year_override` records the operator-selected year.
- Related rows in `DepartmentYearly`, `SupportRecipient`, and
  `SchoolYearStatus` are rewritten through append-only revision rows.
- `coverage` and `excel/exporter` continue to read the physical
  `fiscal_year`. They do not call `effective_fiscal_year()`.

`effective_fiscal_year()` is only for override internals and UI display.

### Step 3: Transcription

Input paths:

- `pdf_parse` for text PDFs
- `ocr_tesseract` for image PDFs when OCR add-on is installed
- `manual` for operator-entered values

Manual input goes through `src/eidp/pipeline/manual_entry.py`, not direct UI
INSERTs. Department changes are written only when the operator explicitly marks
the event as one of:

- new department
- discontinued department
- rename
- merge

Ordinary number corrections update `DepartmentYearly` and audit only.

### Step 4: Weekly Excel Aggregation

`weekly_run.bat` launches `scripts/run_weekly_target_year_discovery.py`.
`scripts/run_r8_rediscovery_weekly.py` remains as a compatibility wrapper for
older Task Scheduler entries and archived validation notes.

The weekly runner does:

- rediscovery
- ingest of documents created during the run
- JSON summary writing
- `data/output/last_run.json`
- shared lock acquisition

The weekly runner does not generate Excel. Operators generate Excel from the
Streamlit `Excel出力` page after reviewing queued items.

## 4. Database Backend

v1.0 uses SQLite:

- `data/eidp.sqlite3`
- WAL mode
- `foreign_keys=ON`
- `busy_timeout=5000`
- shared application lock at `data/.lock`

`eidp db-bootstrap --sqlite` creates tables from ORM metadata, adds the
null-safe department expression index, applies PRAGMAs, and stamps Alembic head.
SQLite bootstrap does not run the historical PostgreSQL-only migration chain.

## 5. Append-Only Data Contract

The following tables are append-only revision tables:

- `DepartmentYearly`
- `SupportRecipient`
- `SchoolYearStatus`

Current-row contract:

- Historical rows remain in place.
- New business changes insert `revision=max+1`.
- Only trusted current rows have `is_current=true`.
- Partial unique indexes enforce one current row per business key.

Business keys:

- `DepartmentYearly`: `(department_id, fiscal_year, revision)`
- `SupportRecipient`: `(school_id, fiscal_year, revision)`
- `SchoolYearStatus`: `(school_id, fiscal_year, revision)`

Read paths use current helpers for `SupportRecipient` and `SchoolYearStatus`.
Low-confidence rows are preserved with `is_current=false` and do not flow into
Excel until confirmed.

## 6. Audit Contract

`manual_action_log` is the authoritative audit table.

`data/audit/manual-actions.jsonl` is an after-commit outbox projection:

- each JSONL row includes `action_id`;
- `jsonl_exported_at` records successful export;
- `jsonl_export_error` records failures;
- `eidp audit-flush` retries pending exports;
- duplicate flushes deduplicate by `action_id`.

JSONL is not treated as the source of truth because file append cannot roll back
with a DB transaction.

## 7. Confidence Architecture

Every extracted row receives a composite confidence:

```text
confidence = 0.4 * F1 + 0.4 * F2 + 0.2 * F3
```

Factors:

- F1 extraction confidence
  - `pdf_parse`: v1 structural approximation
  - `ocr_tesseract`: Tesseract TSV word confidence average
  - `manual`: 1.0
- F2 parser completeness
  - required fields: `name`, `capacity`, `enrollment`, `graduates`
- F3 year-over-year sanity
  - stable enrollment ratio band gets 1.0
  - missing prior data gets neutral 0.7

Default thresholds:

- `>= 0.85`: auto accepted
- `>= 0.70 and < 0.85`: accepted with review flag
- `>= 0.50 and < 0.70`: not current, goes to manual queue
- `< 0.50`: extraction failed / held for manual queue

Environment overrides:

- `EIDP_CONFIDENCE_AUTO`
- `EIDP_CONFIDENCE_REVIEW`
- `EIDP_CONFIDENCE_REJECT`

The composite value is stored in `extraction_confidence`; detailed factor JSON
is stored in `confidence_breakdown`.

## 8. OCR Add-On

The OCR add-on is optional and uses this layout:

```text
ocr-addon\tesseract\tesseract.exe
ocr-addon\tessdata\jpn.traineddata
```

Runtime detection checks:

- binary location
- Japanese traineddata
- CPU and memory threshold

Automatic OCR is enabled when CPU is at least 2 cores and available memory is
at least 4GB. Lower-spec PCs can still trigger OCR for a single PDF manually.

## 9. Windows Constraints

Mac unit tests prove business logic. They do not prove Windows deployability.
The Windows VM offline gate remains mandatory.

Key constraints:

- use `pathlib` for application paths;
- do not rely on cwd;
- use `EIDP_APP_ROOT`;
- use Windows `win_amd64` / CPython 3.12 / `cp312` wheels;
- install offline from `wheelhouse`;
- force UTF-8 for long-running Python launchers;
- keep SQLite WAL / FK / busy timeout on every connection;
- display lock-busy state in UI instead of silently blocking;
- detect Excel file locks and show a Japanese operator message;
- detect missing OCR/Chromium add-ons at runtime;
- keep Playwright/Chromium outside the core ZIP.

## 10. Verification Gates

Stage 1: Mac unit tests

- proves business logic and packaging shape only
- not sufficient for release

Stage 2: Windows VM offline setup

- ZIP extraction
- `first_setup.bat`
- offline wheel install
- SQLite bootstrap
- master import
- Task Scheduler registration

Stage 3: Windows VM weekly run

- `weekly_run.bat`
- shared lock
- `last_run.json`
- run log

Stage 4: Windows VM Excel generation

- preview page
- output workbook
- Excel-open file lock error

Stage 5: Windows VM OCR add-on

- add-on extraction
- image PDF OCR
- confidence breakdown
- manual queue routing

Stage 6: operator PC E2E

- one real target-year cycle
- KPI collection
- owner and operator sign-off

Until Stage 2-5 pass, the package is alpha. Until Stage 6 passes, it is beta.

## 11. Future Direction

v2 is tracked separately. The near-term v1.0 scope is vocational schools on one
operator Windows PC. Universities, multi-operator concurrency, cloud
distribution, and PostgreSQL return are future roadmap items.

## 12. Optional Add-On Packages

The core ZIP should stay small and predictable. Optional heavy runtimes are
packaged separately:

- OCR add-on: `scripts/build_ocr_addon_zip.py`
  - packages a prepared Tesseract directory and tessdata
  - runtime layout: `ocr-addon/tesseract/` and `ocr-addon/tessdata/`
- Playwright add-on: `scripts/build_playwright_addon_zip.py`
  - packages a prepared Playwright wheelhouse and `ms-playwright` browser cache
  - runtime layout: `playwright-addon/wheelhouse/` and
    `playwright-addon/ms-playwright/`

The core Windows ZIP remains HTTP-first. Missing add-ons must be detected at
runtime and shown as operator-facing warnings, not hard failures during normal
startup.

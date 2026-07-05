# Linux/Web v1 Integration Status

Date: 2026-07-05

Branch: `integration/linux-web-v1`

Status: Linux/Web v1 engineering baseline is forming correctly.

Release Forecast: `NOT_READY`

## Included Goals

- Goal 1: table-aware extraction first cut, with legacy extractor behavior kept outside the Linux/Web queue path.
- Goal 2A: Linux/Web pivot decision package and release-gate documents.
- Goal 2B: Linux Web PDF intake MVP for PDF, ZIP, and URL CSV registration.
- Goal 3A: intake-to-extraction queue bridge with `text_pdf_main` and `exception_manual_ocr` lanes.
- Goal 3B: extraction review UI MVP with evidence display, review actions, correction log, and review report generation.
- Goal 3C: normalized review report, read-only master expected subset loading, reviewed-row diff, mismatch CSV, and lightweight Web diff page.
- Goal 3D: reviewed-row key hardening, `field_category` / `course_name` preservation, master row identity, and `ambiguous_key` reporting.
- Goal 3E: multi-user architecture boundary for React/FastAPI/PostgreSQL migration planning.
- Goal 4: external Copilot/NotebookLM/manual CSV/XLSX import, canonical metric normalization, and TRUE/FALSE double-check comparison for unique comparable rows.

## Current Chain

PDF intake
-> extraction queue
-> table-aware extraction
-> extraction review
-> normalized review report
-> master expected subset diff
-> ambiguous-key gated mismatch report
-> multi-user architecture boundary
-> external extraction import
-> TRUE/FALSE double-check report

## Verification

- `uv run pytest tests/unit/test_review_report.py tests/unit/test_review_master_diff.py tests/unit/test_extraction_review.py tests/unit/test_extraction_queue.py tests/unit/test_pdf_intake.py -q`
  - Result: 29 passed.
- `uv run pytest tests/unit/test_table_grid_extractor.py tests/unit/test_pdf_parser_regression.py tests/unit/test_actual_row_converter.py -q`
  - Result: 28 passed, 1 skipped.
- `uv run ruff check src/eidp/pipeline/pdf_intake.py src/eidp/pipeline/extraction_queue.py src/eidp/pipeline/extraction_review.py src/eidp/pipeline/review_report.py src/eidp/pipeline/review_master_diff.py src/eidp/web tests/unit/test_pdf_intake.py tests/unit/test_extraction_queue.py tests/unit/test_extraction_review.py tests/unit/test_review_report.py tests/unit/test_review_master_diff.py`
  - Result: all checks passed.
- `uv run mypy src/eidp/pipeline/pdf_intake.py src/eidp/pipeline/extraction_queue.py src/eidp/pipeline/extraction_review.py src/eidp/pipeline/review_report.py src/eidp/pipeline/review_master_diff.py src/eidp/web`
  - Result: success, no issues found in 20 source files.
- `uv run python -c "import eidp.web.app; import eidp.web.pages.review_diff"`
  - Result: passed.
- `uv run --extra dev pytest tests/unit/test_external_extraction_import.py tests/unit/test_double_check_compare.py -q`
  - Result: 11 passed.
- `uv run --extra dev ruff check src/eidp/pipeline/pdf_intake.py src/eidp/pipeline/extraction_queue.py src/eidp/pipeline/extraction_review.py src/eidp/pipeline/review_report.py src/eidp/pipeline/review_master_diff.py src/eidp/pipeline/external_extraction_import.py src/eidp/pipeline/double_check_compare.py src/eidp/web tests/unit/test_pdf_intake.py tests/unit/test_extraction_queue.py tests/unit/test_extraction_review.py tests/unit/test_review_report.py tests/unit/test_review_master_diff.py tests/unit/test_external_extraction_import.py tests/unit/test_double_check_compare.py`
  - Result: all checks passed.
- `uv run --extra dev mypy src/eidp/pipeline/pdf_intake.py src/eidp/pipeline/extraction_queue.py src/eidp/pipeline/extraction_review.py src/eidp/pipeline/review_report.py src/eidp/pipeline/review_master_diff.py src/eidp/pipeline/external_extraction_import.py src/eidp/pipeline/double_check_compare.py src/eidp/web`
  - Result: success, no issues found in 24 source files.
- `uv run --extra dev python -c "import eidp.web.app; import eidp.web.pages.double_check"`
  - Result: passed.
- `uv run pytest -q`
  - Result: 2203 passed, 3 skipped, 5 warnings.
- Real master ambiguity smoke:
  - Command: `load_master_expected_subset('/Users/shunmei/workspace/EIDP/data/master.xlsx', corporation_name='山口学園', school_name='ECCコンピュータ専門学校', fiscal_year=2019)` followed by `diff_reviewed_against_master([], expected)`.
  - Result: 30 expected rows, 30 diff rows, 6 `ambiguous_key` rows.

## Known Not Included

- Automatic Copilot/NotebookLM API integration or external PDF upload.
- Excel/XLOOKUP export.
- Final Excel write.
- Linux server deployment proof.
- Intended network browser access validation.
- Authentication, PostgreSQL, or React/Next.js.
- Automatic PDF discovery.
- Automatic fiscal-year judgment.
- Windows canary evidence changes.
- Owner/PI final sign-off for data handling and network access boundaries.
- Operator mapping UI or workflow for resolving remaining `ambiguous_key` rows.
- React/FastAPI/PostgreSQL implementation.
- Authentication, roles, locking implementation, and job queue implementation.

## Key-Collision Audit

`docs/reports/linux-web-v1-key-collision-audit.md` scanned the real master workbook at
`/Users/shunmei/workspace/EIDP/data/master.xlsx` in read-only mode.

Result:

- K1 `school_name | department_name | fiscal_year | metric`: not stable.
- K2 `school_name | course_name | department_name | fiscal_year | metric`: not stable.
- K3 `school_name | field_category | course_name | department_name | day_or_evening | duration_years | fiscal_year | metric`: still has collisions.
- Goal 3D now reports ambiguous keys instead of silently matching them.
- Goal 4 compares only rows that resolve to a unique reviewed/external key; `ambiguous_key`, `needs_review`, and `excluded` rows remain not comparable and do not become Excel-ready.

## Multi-User Architecture Boundary

- `docs/decisions/ADR-2026-07-multi-user-web-architecture.md`
- `docs/release/linux-web-multi-user-gates.md`
- `docs/roadmap/react-fastapi-postgres-migration.md`

Decision summary:

- Python remains the backend, extraction, Excel, audit, and job-processing core.
- Streamlit remains MVP/internal prototype UI.
- React is the target formal multi-user UI.
- FastAPI is the target backend API layer.
- PostgreSQL is the target multi-user persistence layer.
- Goal 4 proceeds only on unique comparable rows; `ambiguous_key`, `needs_review`, and `excluded` remain not comparable.

## Release Forecast

`NOT_READY`

This integration line is suitable as the base for Goal 5 only if the next slice keeps double-check mismatches,
`ambiguous_key`, `needs_review`, and `excluded` rows out of the Excel/XLOOKUP output. It is not suitable for release
or RC designation.

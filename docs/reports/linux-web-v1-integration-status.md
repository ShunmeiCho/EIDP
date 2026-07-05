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

## Current Chain

PDF intake
-> extraction queue
-> table-aware extraction
-> extraction review
-> normalized review report
-> master expected subset diff

## Verification

- `uv run pytest tests/unit/test_extraction_review.py tests/unit/test_extraction_queue.py tests/unit/test_pdf_intake.py -q`
  - Result: 17 passed.
- `uv run pytest tests/unit/test_review_report.py tests/unit/test_review_master_diff.py -q`
  - Result: 10 passed.
- `uv run pytest tests/unit/test_table_grid_extractor.py tests/unit/test_pdf_parser_regression.py tests/unit/test_actual_row_converter.py -q`
  - Result: 28 passed, 1 skipped.
- `uv run ruff check src/eidp/pipeline/pdf_intake.py src/eidp/pipeline/extraction_queue.py src/eidp/pipeline/extraction_review.py src/eidp/pipeline/review_report.py src/eidp/pipeline/review_master_diff.py src/eidp/web tests/unit/test_pdf_intake.py tests/unit/test_extraction_queue.py tests/unit/test_extraction_review.py tests/unit/test_review_report.py tests/unit/test_review_master_diff.py`
  - Result: all checks passed.
- `uv run mypy src/eidp/pipeline/pdf_intake.py src/eidp/pipeline/extraction_queue.py src/eidp/pipeline/extraction_review.py src/eidp/pipeline/review_report.py src/eidp/pipeline/review_master_diff.py src/eidp/web`
  - Result: success, no issues found in 20 source files.
- `uv run python -c "import eidp.web.app; import eidp.web.pages.review_diff"`
  - Result: passed.
- `uv run pytest -q`
  - Result: 2201 passed, 3 skipped, 5 warnings.

## Known Not Included

- Copilot/NotebookLM import.
- TRUE/FALSE double-check comparison.
- Excel/XLOOKUP export.
- Final Excel write.
- Linux server deployment proof.
- Intended network browser access validation.
- Authentication, PostgreSQL, or React/Next.js.
- Automatic PDF discovery.
- Automatic fiscal-year judgment.
- Windows canary evidence changes.
- Owner/PI final sign-off for data handling and network access boundaries.
- Stable reviewed-row key hardening after the 2026-07-05 key-collision audit.

## Key-Collision Audit

`docs/reports/linux-web-v1-key-collision-audit.md` scanned the real master workbook at
`/Users/shunmei/workspace/EIDP/data/master.xlsx` in read-only mode.

Result:

- K1 `school_name | department_name | fiscal_year | metric`: not stable.
- K2 `school_name | course_name | department_name | fiscal_year | metric`: not stable.
- K3 `school_name | field_category | course_name | department_name | day_or_evening | duration_years | fiscal_year | metric`: still has collisions.
- Goal 4 is blocked until Goal 3D hardens reviewed/master keys and reports ambiguous keys instead of silently matching them.

## Release Forecast

`NOT_READY`

This integration line is suitable as the base for Goal 3D stable reviewed-row key hardening. It is not suitable for Goal 4, release, or RC designation.

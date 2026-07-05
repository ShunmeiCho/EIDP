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

## Verification

- `uv run pytest tests/unit/test_extraction_review.py tests/unit/test_extraction_queue.py tests/unit/test_pdf_intake.py -q`
  - Result: 17 passed.
- `uv run pytest tests/unit/test_table_grid_extractor.py tests/unit/test_pdf_parser_regression.py tests/unit/test_actual_row_converter.py -q`
  - Result: 28 passed, 1 skipped.
- `uv run ruff check src/eidp/pipeline/pdf_intake.py src/eidp/pipeline/extraction_queue.py src/eidp/pipeline/extraction_review.py src/eidp/web tests/unit/test_pdf_intake.py tests/unit/test_extraction_queue.py tests/unit/test_extraction_review.py`
  - Result: all checks passed.
- `uv run mypy src/eidp/pipeline/pdf_intake.py src/eidp/pipeline/extraction_queue.py src/eidp/pipeline/extraction_review.py src/eidp/web`
  - Result: success, no issues found in 16 source files.
- `uv run python -c "import eidp.web.app"`
  - Result: passed.

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

## Release Forecast

`NOT_READY`

This integration line is suitable as the base for Goal 3C: reviewed rows to master diff and mismatch report hardening. It is not suitable for release or RC designation.

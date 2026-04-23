# Repository Guidelines

## Project Structure & Module Organization

EIDP is a Python 3.12 data pipeline packaged from `src/eidp`. Major modules are `db/` for SQLAlchemy models and sessions, `pipeline/` for ingestion, `scraper/` for URL/PDF discovery, `pdf/` for extraction and evaluation, `matcher/` for MEXT reconciliation, `excel/` for import/export, and `review/` for the Streamlit review UI. Alembic files live in `migrations/`, with revisions in `migrations/versions/`. Tests live in `tests/`; keep unit tests in `tests/unit/` and use `tests/integration/` or `tests/e2e/` for broader flows. Tracked reference data is in `data/`; generated PDFs and exports should stay out of git.

## Build, Test, and Development Commands

- `uv sync --extra dev`: install the package with pytest, Ruff, and mypy.
- `uv sync --extra scraper --extra pdf --extra dev`: install common extras; add `--extra ocr` only for OCR work.
- `docker compose -f deploy/compose.yaml up -d`: start the local Postgres 17 database.
- `uv run alembic upgrade head`: apply database migrations.
- `uv run eidp --help`: inspect CLI commands.
- `uv run pytest`: run the test suite.
- `uv run ruff check .` and `uv run mypy src`: run linting and type checks.

## Coding Style & Naming Conventions

Use 4-space indentation, explicit type hints, and focused modules. Ruff uses a 120-character line length and lint families `E`, `F`, `I`, `N`, `W`, and `UP`; keep imports sorted by Ruff. Mypy is strict, so avoid untyped public functions. Use `snake_case` for modules, functions, variables, and Typer callbacks; use `PascalCase` for classes and Pydantic/SQLAlchemy models.

## Testing Guidelines

Tests use pytest. Name files `test_*.py`, functions `test_*`, and related classes `Test*`. Prefer deterministic fixtures in `tests/fixtures/` or the existing gold-set/sample-PDF data. For behavior changes, add or update tests first and aim for at least 80% coverage on touched code. Use `uv run pytest --cov=eidp` to check coverage.

## Commit & Pull Request Guidelines

Follow the existing conventional style: `feat:`, `fix:`, `chore:`, `security:`, `test:`, `docs:`, or `refactor:`. Keep commits focused and mention migrations, data format changes, or new environment variables in the body. Pull requests should summarize the change, list verification commands, link relevant issues, and include screenshots for UI changes.

## Security & Configuration Tips

Copy `.env.example` to `.env` for local configuration; never commit real secrets. Install hooks with `git config core.hooksPath .githooks` to enable staged Gitleaks scans. Keep large/generated artifacts in ignored paths such as `data/pdfs/`, `output/`, or local-only storage.

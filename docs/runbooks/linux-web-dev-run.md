# Linux Web Dev Runbook

Status: MVP development runbook. This is not a Linux production deployment guide and does not change the
release forecast.

## Scope

This web entry point supports only browser-based PDF intake:

- single PDF upload;
- ZIP upload containing PDFs;
- URL CSV registration;
- required metadata capture: `school_name`, optional `school_id`, `fiscal_year`, `source_page_url`, and either
  `pdf_url` or an uploaded filename;
- SHA256 and local file storage for uploaded PDFs;
- text-PDF versus image-PDF classification;
- intake queue display;
- image PDFs routed to `exception_manual_ocr`.

It does not implement automatic PDF discovery, automatic target-year judgment, Copilot/NotebookLM upload,
extraction review, double-check import, final Excel write, user auth/roles, or Linux production deployment.

## Local Runtime Lifecycle

From the repository root:

```bash
uv sync --extra pdf --extra dev
# Set the allowlisted port in the project-root .env, for example:
# EIDP_WEB_PORT=8510
deploy/linux/eidpctl.sh start
deploy/linux/eidpctl.sh status
deploy/linux/eidpctl.sh health
deploy/linux/eidpctl.sh stop
deploy/linux/eidpctl.sh restart
```

The controller validates `EIDP_WEB_PORT` from `.env`, defaults it to `8502`,
and keeps Streamlit bound to `127.0.0.1`. Operators use only the five
`eidpctl.sh` lifecycle commands above. `deploy/linux/run_web.sh` is reserved for
the internal CI smoke and is not an operator entrypoint.

For a remote research-lab Linux server, expose the UI through an SSH tunnel or an approved reverse proxy.
Do not bind this MVP directly to `0.0.0.0`; this slice does not include authentication or role controls.

## Storage

The app stores intake artifacts under:

```text
data/web-intake/
  files/<fiscal_year>/<sha-prefix>-<filename>.pdf
  records/<record_id>.json
```

Uploaded PDFs get a SHA256 hash before classification. URL CSV rows register metadata only and do not download the
remote PDF in this slice.

Metadata records are one JSON file per intake record. This avoids introducing PostgreSQL or a new SQLite write path in
the MVP. If a later slice moves intake metadata into SQLite, keep the existing EIDP single-writer/WAL boundary explicit
before enabling multiple concurrent operators.

## CSV Format

Required columns:

```csv
school_name,school_id,fiscal_year,source_page_url,pdf_url
```

`school_id` may be blank. `fiscal_year` must be a western-year integer in the supported EIDP range.

## Verification

Targeted checks for this slice:

```bash
uv run pytest tests/unit/test_pdf_intake.py
uv run python -c "import eidp.web.app"
uv run ruff check src/eidp/pipeline/pdf_intake.py src/eidp/web tests/unit/test_pdf_intake.py
uv run mypy src/eidp/pipeline/pdf_intake.py src/eidp/web/app.py src/eidp/web/components/intake_table.py src/eidp/web/pages/pdf_intake.py
```

No command in this runbook writes final Excel output.

# Linux Web Dev Runbook

Status: MVP development runbook. This is not a Linux production deployment guide and does not change the
release forecast.

## Scope

This web entry point supports local development of the browser workflow through
reasoned double-check resolution:

- single PDF upload;
- ZIP upload containing PDFs;
- URL CSV registration;
- required metadata capture: `school_name`, optional `school_id`, `fiscal_year`, `source_page_url`, and either
  `pdf_url` or an uploaded filename;
- SHA256 and local file storage for uploaded PDFs;
- text-PDF versus image-PDF classification;
- intake queue display;
- served TEXT extraction with persisted cell evidence;
- accept, correct, needs-review and exclude decisions stored in SQLite with
  DB-authoritative audit and after-commit JSONL projection;
- read-only comparison against the managed `data/master.xlsx`;
- persisted external CSV/XLSX comparison and audited human resolution;
- image PDFs routed to `exception_manual_ocr`.

It does not implement automatic PDF discovery, automatic target-year judgment, Copilot/NotebookLM upload,
canonical source-PDF CAS/retention, automatic image OCR, final/partial Excel export, application-managed user
accounts/roles, or Linux production deployment.

## Local Runtime Lifecycle

From the repository root:

```bash
uv sync --extra pdf --extra dev
# Set the allowlisted port in the project-root .env, for example:
# EIDP_WEB_PORT=8510
# Local development uses an explicit, auditable fallback identity:
# EIDP_IDENTITY_MODE=configured_fallback
# EIDP_FALLBACK_ACTOR=local-dev
deploy/linux/eidpctl.sh start
deploy/linux/eidpctl.sh status
deploy/linux/eidpctl.sh health
deploy/linux/eidpctl.sh stop
deploy/linux/eidpctl.sh restart
```

The controller validates `EIDP_WEB_PORT` from `.env`, defaults it to `8502`,
and keeps Streamlit bound to `127.0.0.1`. Operators use only the five
`eidpctl.sh` lifecycle commands above. `deploy/linux/run_web.sh` is reserved for
the internal CI smoke and is not an operator entrypoint. Before starting
Streamlit, the launcher validates the selected identity mode. Trusted-proxy
mode requires a non-empty `EIDP_PROXY_SHARED_SECRET`; a real secret must never
be committed.

For developer-only remote diagnostics, an SSH tunnel may reach the loopback
listener. Business users must use an ICT-approved reverse proxy; they do not use
SSH. Never bind the app directly to `0.0.0.0`; this slice does not include
application-managed login or role controls. It resolves request identity through
either a trusted proxy plus shared secret or the explicit configured fallback.

## Storage

The app stores intake artifacts under:

```text
data/web-intake/
  files/<fiscal_year>/<sha-prefix>-<filename>.pdf
  records/<record_id>.json
  extraction/jobs/<record_id>.json
  extraction/results/<record_id>.json
  extraction/reviews/<review_id>.json
```

Uploaded PDFs get a SHA256 hash before classification. URL CSV rows register metadata only and do not download the
remote PDF in this slice.

Intake and mechanical extraction JSON files are projections/base evidence, not
the authority for human decisions. Review decisions, comparison runs/results,
resolutions and manual audit rows are stored in the project-local SQLite DB
under the existing global single-writer/WAL boundary. The JSONL audit file is an
idempotent after-commit projection keyed by `action_id`. PostgreSQL and multiple
concurrent writers remain out of scope for v1.

## CSV Format

Required columns:

```csv
school_name,school_id,fiscal_year,source_page_url,pdf_url
```

`school_id` may be blank. `fiscal_year` must be a western-year integer in the supported EIDP range.

## Verification

Targeted checks for this slice:

```bash
uv run pytest tests/integration/test_served_linux_web_chain.py tests/integration/test_linux_web_e2e_chain.py
uv run python -c "import eidp.web.app"
uv run ruff check src/eidp/web tests/integration/test_served_linux_web_chain.py
uv run mypy src/eidp/web
```

No command in this runbook writes final Excel output.

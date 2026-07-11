# EIDP

Education Institution Data Pipeline (EIDP) is an internal Linux/Web workflow
for extracting Japanese vocational-school disclosure data, reviewing evidence,
cross-checking an external extraction, and producing Excel-compatible results.

## Active product

- Deployment: Linux server, with the application process isolated in the
  repository-local `.venv` managed by `uv`.
- UI: Streamlit in a browser; the Streamlit process binds `127.0.0.1` and LAN
  access is provided by an approved internal reverse proxy.
- Storage: SQLite plus files under the configured `EIDP_DATA_DIR`.
- Workflow: confirmed PDF intake -> text/image routing -> deterministic
  extraction -> human review -> master diff -> external double-check -> export.
- Scope: vocational schools (`専門学校`). Automatic website discovery remains
  support tooling, not the v1 release gate.

The retired Windows runtime, ZIP packaging, batch launchers, and Stage 6 gate
are not part of `main`. Their last audit anchor is the Git tag
`windows-v548-fallback`.

## Local development

```bash
uv sync --extra dev --extra scraper-basic --extra pdf
uv run streamlit run src/eidp/web/app.py --server.address 127.0.0.1 --server.port 8502
```

Quality checks:

```bash
uv run ruff check .
uv run --with bandit bandit -q --severity-level high -r src/eidp scripts
uv run mypy src
EIDP_DATABASE_URL='sqlite:///./data/test_audit.sqlite3' uv run pytest
```

## Venus deployment boundary

The authorized target is `venus:/home/junming/EIDP`. Deployment edits,
virtual environments, data, logs, and generated files must remain under that
directory. Do not modify any path outside it.

Typical flow:

1. Develop and test locally on `main`.
2. Transfer through Git/GitHub.
3. On Venus, update `/home/junming/EIDP` and run `uv sync --frozen` to create or
   update `/home/junming/EIDP/.venv`.
4. Copy `deploy/linux/env.example` to a private `.env` under the project root.
5. Start with `deploy/linux/run_web.sh` and verify the loopback health endpoint.
6. Validate access from an authorized business PC through the internal network
   endpoint/reverse proxy.

See [Linux development runbook](docs/runbooks/linux-web-dev-run.md),
[server requirements](deploy/linux/server-requirements.md), and
[release gates](docs/governance/release-gates.md).

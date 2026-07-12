# EIDP v1 Exit Criteria

EIDP v1 is a Linux-hosted internal Web workflow for vocational-school data.

Mandatory exit criteria:

- full Ruff, high-severity Bandit, mypy, and pytest are green;
- confirmed-PDF intake through double-check passes exact E2E assertions;
- Web writes share the SQLite application lock and contention never writes;
- append-only revision, audit/outbox, master.xlsx read-only, and Excel-output
  contracts pass;
- a frozen dependency install, start, stop, and restart succeed under
  `/home/junming/EIDP/.venv`;
- Streamlit remains loopback-bound and a real authorized business PC completes
  upload, review, and download through the internal endpoint;
- image/OCR exceptions have an accepted policy and visible manual path;
- authentication/allowlist, retention, and backup/restore evidence are recorded;
- operator acceptance is recorded without unresolved high-risk mismatches.

Automatic target-year discovery yield is monitored but is not an exit gate.
University production support remains out of v1 scope.

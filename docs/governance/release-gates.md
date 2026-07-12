# Linux/Web Release Gates

EIDP is releasable only when all mandatory gates below have fresh evidence.
Green unit tests alone are insufficient.

## G0 — source and quality

- `main` is the only development line.
- `uv.lock` is current and dependency installation succeeds with `--frozen`.
- Ruff, high-severity Bandit, mypy, and full pytest pass.
- CI keeps the required check names `Python quality gates` and
  `Ship gate contract`; the latter now enforces the Linux/Web served-app
  contract.

## G1 — served application

- `deploy/linux/run_web.sh` sets `EIDP_APP_ROOT`, uses the project `.venv`, and
  binds Streamlit to `127.0.0.1`.
- The Web entry point imports and starts on Venus from
  `/home/junming/EIDP` without writing outside that directory.
- Intake -> queue -> review -> master diff -> double-check E2E passes with exact
  expected record counts and `excel_ready` invariants.
- Every Web mutation participates in the shared `data/.lock` contract.

## G2 — data integrity

- Four-table append-only fiscal-year revision tests pass.
- Audit DB/outbox dedup and master.xlsx read-only tests pass.
- Duplicate PDFs are detected through hashes/keys.
- Image/OCR exceptions and reconciliation mismatches remain visible and cannot
  enter final output silently.

## G3 — deployment and network

- Venus resources, Python 3.12/uv, storage permissions, and restart mechanism
  are verified.
- The service and all runtime artifacts stay under `/home/junming/EIDP`.
- Streamlit is loopback-only; the approved internal endpoint is reachable from
  an authorized business PC and is not publicly exposed.
- Upload, review, and download are tested from the real business network.

## G4 — security and operations

- No secrets are committed or logged.
- Authentication/allowlist policy matches the approved LAN risk decision.
- Backup and restore of SQLite, audit data, uploads, and exports are proven.
- Operator identity and review actions are auditable.

## support-only metrics

Automatic target-year discovery yield and the historical 60%/30% thresholds
remain health/workload indicators in `scripts/ship_gate_contract.py`. They do not determine Linux/Web v1 release readiness.

## Current conclusion

Until the Venus served-app, LAN browser, and backup/restore evidence exists,
the release forecast is `NOT_READY`.

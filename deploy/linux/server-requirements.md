# Venus Linux Server Requirements

Date: 2026-07-11
Target: `venus:/home/junming/EIDP`

## Hard filesystem boundary

Deployment automation may read and write only below `/home/junming/EIDP`.
Do not install packages into system Python, edit `/etc`, create system-wide
services, or touch any other user/project directory without a separate explicit
authorization.

## Isolated runtime

```bash
cd /home/junming/EIDP
deploy/linux/sync_venv.sh
```

The sync wrapper and project-local controller both use
`deploy/linux/project_env.sh`, so dependency builds, extraction, and serving
share the same filesystem boundary. This creates/updates
`/home/junming/EIDP/.venv`. Runtime startup uses `uv run --frozen --no-sync`, so
serving the app neither resolves dependencies nor changes the host environment.
The boundary also redirects `HOME`, `TMPDIR`, XDG/uv caches, browser binaries,
SQLite, and application data below the project root so libraries cannot
silently create runtime state elsewhere.

Required server capabilities:

- Python 3.12 available to `uv`; if `uv` must download it, the configured
  install directory keeps it below the authorized root;
- enough CPU/RAM/storage for PDF parsing and the selected OCR lane;
- write permission for `/home/junming/EIDP/data`;
- an approved restart/supervision method that does not require edits outside
  the project boundary;
- backup storage/path approved within the same boundary.

## Network shape

```text
business PC on the internal network
  -> approved internal IP/DNS and port
  -> reverse proxy or controlled forward
  -> 127.0.0.1:8502 on Venus
```

Streamlit does not bind `0.0.0.0`. Before release, verify the actual business PC
can upload, review, and download through the approved internal endpoint.

Set the allowlisted `EIDP_WEB_PORT` in the private project-root `.env`. Runtime
operators use only:

```bash
deploy/linux/eidpctl.sh start
deploy/linux/eidpctl.sh status
deploy/linux/eidpctl.sh health
deploy/linux/eidpctl.sh stop
deploy/linux/eidpctl.sh restart
```

`deploy/linux/run_web.sh` is reserved for the internal CI smoke and is not an
operator entrypoint.

## Minimum deployment proof

- `uv sync --frozen` succeeds inside the project root;
- `deploy/linux/eidpctl.sh start`, `status`, and `health` prove the loopback
  runtime, and `stop`/`restart` prove controlled lifecycle recovery;
- stop/start/restart does not corrupt SQLite or leave a stale writer lock;
- a business-PC LAN smoke completes;
- SQLite, audit, upload, and export backup/restore succeeds;
- `git status` shows no generated runtime data tracked by Git.

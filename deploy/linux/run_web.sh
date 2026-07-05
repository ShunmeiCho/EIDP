#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PORT="${EIDP_WEB_PORT:-8502}"

cd "${APP_ROOT}"
exec uv run streamlit run src/eidp/web/app.py \
  --server.address 127.0.0.1 \
  --server.port "${PORT}"

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=project_env.sh
source "${SCRIPT_DIR}/project_env.sh"
: "${STREAMLIT_SERVER_PORT:?STREAMLIT_SERVER_PORT must be supplied by the runtime controller or CI smoke}"
export STREAMLIT_SERVER_PORT

cd "${APP_ROOT}"
exec uv run --frozen --no-sync streamlit run src/eidp/web/app.py \
  --server.address 127.0.0.1

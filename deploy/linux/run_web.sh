#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=project_env.sh
source "${SCRIPT_DIR}/project_env.sh"
: "${STREAMLIT_SERVER_PORT:?STREAMLIT_SERVER_PORT must be supplied by the runtime controller or CI smoke}"
export STREAMLIT_SERVER_PORT

cd "${APP_ROOT}"
uv run --frozen --no-sync python -c \
  "from eidp.config import settings; from eidp.web.identity import validate_identity_configuration; validate_identity_configuration(settings)"
exec uv run --frozen --no-sync streamlit run src/eidp/web/app.py \
  --server.address 127.0.0.1

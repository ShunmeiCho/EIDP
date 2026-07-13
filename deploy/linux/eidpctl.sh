#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=project_env.sh
source "${SCRIPT_DIR}/project_env.sh"
cd "${APP_ROOT}"
exec uv run --frozen --no-sync python -m eidp.ops.runtime_controller "$@"

#!/usr/bin/env bash

# Shared filesystem boundary for Linux dependency setup and runtime startup.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

export EIDP_APP_ROOT="${APP_ROOT}"
export EIDP_DATA_DIR="${APP_ROOT}/data"
export EIDP_DATABASE_URL="sqlite:///${APP_ROOT}/data/eidp.sqlite3"
export UV_PROJECT_ENVIRONMENT="${APP_ROOT}/.venv"
export UV_CACHE_DIR="${APP_ROOT}/.cache/uv"
export UV_PYTHON_INSTALL_DIR="${APP_ROOT}/.cache/uv/python"
export PLAYWRIGHT_BROWSERS_PATH="${APP_ROOT}/.cache/ms-playwright"
export XDG_CACHE_HOME="${APP_ROOT}/.cache"
export TMPDIR="${APP_ROOT}/.cache/tmp"
export HOME="${APP_ROOT}/.home"

mkdir -p "${EIDP_DATA_DIR}" "${PLAYWRIGHT_BROWSERS_PATH}" "${TMPDIR}" "${HOME}"

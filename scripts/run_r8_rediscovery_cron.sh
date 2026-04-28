#!/usr/bin/env bash
# Weekly R8 rediscovery cron wrapper.
#
# Owner decision (2026-04-28): Go crontab now, design for user-systemd later.
# Linger=no on venus + no sudo, so user-systemd would silently miss runs when
# junming is logged out. crontab is reboot-safe and runs regardless of session.
#
# This wrapper enforces:
#   - strict uv venv isolation (.venv/bin/python directly — no `uv run` sync)
#   - venv self-check fail-fast (refuse to run if .venv is broken)
#   - flock single-instance (last week's run can't double-trigger this week)
#   - timestamped append-mode log per run
#   - failure marker file for downstream alerting
#   - exit code propagation so cron's MAILTO can pick up failures

set -euo pipefail

REPO_DIR="${EIDP_REPO_DIR:-/home/junming/workspace/EIDP}"
VENV_PY="${REPO_DIR}/.venv/bin/python"
LOG_DIR="${REPO_DIR}/logs/r8-rediscovery"
LOCK_FILE="${LOG_DIR}/.lock"
FAIL_MARKER="${LOG_DIR}/.last_failure"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_FILE="${LOG_DIR}/run-${TS}.log"

mkdir -p "${LOG_DIR}"

# Pre-flight: refuse to run if .venv is missing or eidp not importable.
if [[ ! -x "${VENV_PY}" ]]; then
  echo "[$(date -Is)] FATAL: ${VENV_PY} not found or not executable" >&2
  echo "venv_missing" > "${FAIL_MARKER}"
  exit 78  # EX_CONFIG
fi

if ! "${VENV_PY}" -c "import sys, eidp; assert sys.prefix == '${REPO_DIR}/.venv', sys.prefix" 2>/dev/null; then
  echo "[$(date -Is)] FATAL: venv isolation check failed" >&2
  "${VENV_PY}" -c "import sys; print('sys.prefix=', sys.prefix)" >&2 || true
  echo "venv_isolation_broken" > "${FAIL_MARKER}"
  exit 78
fi

cd "${REPO_DIR}"

# Acquire non-blocking lock; if last week's run still alive, exit success-noop.
exec 9>"${LOCK_FILE}"
if ! flock -n 9; then
  echo "[$(date -Is)] previous run still holds lock at ${LOCK_FILE}; skipping" >&2
  exit 0
fi

# Append banner + run.
{
  echo "===================="
  echo "start_utc=${TS}"
  echo "repo=${REPO_DIR}"
  echo "python=${VENV_PY}"
  echo "args=$*"
  echo "===================="
} >> "${LOG_FILE}"

set +e
"${VENV_PY}" scripts/run_r8_rediscovery_weekly.py \
  --methods prefecture_aggregator \
  --current-fy 2026 \
  --batch-size 250 \
  --ingest-batch-size 500 \
  --rate-limit 1.5 \
  "$@" \
  >> "${LOG_FILE}" 2>&1
RC=$?
set -e

{
  echo "===================="
  echo "end_utc=$(date -u +%Y%m%dT%H%M%SZ)"
  echo "exit_code=${RC}"
  echo "===================="
} >> "${LOG_FILE}"

if [[ ${RC} -ne 0 ]]; then
  printf "%s exit=%d log=%s\n" "$(date -Is)" "${RC}" "${LOG_FILE}" > "${FAIL_MARKER}"
else
  rm -f "${FAIL_MARKER}"
fi

# Retain last 12 weekly logs (~3 months); rotate older.
ls -1t "${LOG_DIR}"/run-*.log 2>/dev/null | tail -n +13 | xargs -r rm -f

exit ${RC}

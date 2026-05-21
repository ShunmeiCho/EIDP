#!/usr/bin/env bash
# Idempotent crontab installer for EIDP weekly R8 rediscovery.
# Safe to re-run: removes any prior EIDP-R8-CRON line before appending fresh.
#
# Usage (on venus, as user junming, no sudo):
#   bash deploy/legacy-venus/cron/install.sh
#
# To uninstall:
#   crontab -l | grep -v 'EIDP-R8-CRON' | crontab -

set -euo pipefail

CRON_FRAGMENT="$(cd "$(dirname "$0")" && pwd)/eidp-r8-rediscovery.cron"
TAG='EIDP-R8-CRON'

if [[ ! -f "${CRON_FRAGMENT}" ]]; then
  echo "FATAL: ${CRON_FRAGMENT} not found" >&2
  exit 1
fi

TMP="$(mktemp)"
trap 'rm -f "${TMP}"' EXIT

# Preserve everything except prior EIDP-R8-CRON lines (and the MAILTO we own).
crontab -l 2>/dev/null \
  | grep -v "${TAG}" \
  | grep -v '^MAILTO=""$' \
  > "${TMP}" || true

# Append our fragment (skip comment-only lines? no — keep MAILTO + schedule lines).
grep -v '^[[:space:]]*#' "${CRON_FRAGMENT}" \
  | grep -v '^[[:space:]]*$' \
  >> "${TMP}"

crontab "${TMP}"

echo "[install] crontab updated. current entries:"
crontab -l | sed 's/^/    /'
echo
echo "[install] next fire (cron is timezone = system TZ):"
date '+%a %F %T %Z (now)'

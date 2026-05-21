# EIDP Legacy Target-Year Rediscovery Weekly Runbook

> Archived 2026-05-05 — Venus crontab/systemd operation is no longer the
> target deployment path. Use `docs/runbooks/eidp-windows.md` for Sprint 8
> Windows-PC operation. The legacy cron/systemd assets are kept under
> `deploy/legacy-venus/` for historical reference only.

## Purpose

Sprint 4 proved that one-time stale rediscovery has zero target-year yield before the
5-6月 publication peak. Sprint 7 converts that waiting period into a weekly
scheduled job:

1. Select 専門学校 with an older ingested target PDF and no FY2026 target PDF.
2. Revisit the current rediscovery method set:
   `prefecture_aggregator`, `seed_csv`, `corporation_pattern`,
   `operator_manual`, and `scrapling_stealth`.
3. Ingest only documents downloaded during the same run.
4. Write a JSON summary and rejection evidence under
   `output/target-year-discovery/` in the renamed Windows runner.

## Scheduling Choice

Owner decision (2026-04-28): **crontab** is the live scheduler. user-level
systemd was rejected because `loginctl show-user junming -p Linger` returns
`Linger=no` on venus and we don't have sudo to enable-linger. Without linger,
a user timer silently misses runs whenever junming is logged out — that
yields a "looks-installed-but-not-running" false sense of automation.

The systemd unit files under `deploy/legacy-venus/systemd/` are kept for the future
migration: once `sudo loginctl enable-linger junming` is run, the same
Python entrypoint can be moved over without rewriting the runner.

## Preflight (read-only)

```bash
cd ~/workspace/EIDP
git status --short
git pull --ff-only
.venv/bin/python -c "import sys, eidp; assert sys.prefix.endswith('/.venv'), sys.prefix; print('venv ok:', sys.prefix)"
.venv/bin/python scripts/run_weekly_target_year_discovery.py --dry-run --limit 5
```

The dry run is read-only against the database and should print a summary path,
the stale school count, and zero discovery/ingest stats.

## Install (crontab path — primary)

No sudo required. Idempotent — re-running replaces any prior `EIDP-R8-CRON`
entry.

```bash
cd ~/workspace/EIDP
bash deploy/legacy-venus/cron/install.sh
crontab -l
```

Schedule: every Monday at 02:00 in venus' system timezone.

```bash
timedatectl              # confirm system TZ is JST (Asia/Tokyo)
date '+%a %F %T %Z'      # current local time
```

Cron daemon survives reboot — `systemctl status cron` should show `active`.

### Manual smoke (real DB writes; owner authorization required)

```bash
.venv/bin/python scripts/run_weekly_target_year_discovery.py --limit 10
```

Or invoke the cron wrapper directly with the same flock/log/marker semantics:

```bash
bash deploy/legacy-venus/run_r8_rediscovery_cron.sh --limit 10
ls -lt logs/r8-rediscovery/run-*.log | head -3
cat logs/r8-rediscovery/.last_failure 2>/dev/null || echo "no failure marker"
```

To narrow a legacy run deliberately, pass a space-separated method list through
`EIDP_REDISCOVERY_METHODS`:

```bash
EIDP_REDISCOVERY_METHODS="prefecture_aggregator seed_csv" \
  bash deploy/legacy-venus/run_r8_rediscovery_cron.sh --limit 10
```

### Uninstall

```bash
crontab -l | grep -v 'EIDP-R8-CRON' | crontab -
```

## Install (systemd path — future, requires sudo + linger)

Only relevant after `sudo loginctl enable-linger junming` is allowed.

```bash
mkdir -p ~/.config/systemd/user
cp deploy/legacy-venus/systemd/eidp-r8-rediscovery.service ~/.config/systemd/user/
cp deploy/legacy-venus/systemd/eidp-r8-rediscovery.timer   ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now eidp-r8-rediscovery.timer
systemctl --user list-timers eidp-r8-rediscovery.timer
```

For system-wide install (heaviest, requires sudo):

```bash
sudo cp deploy/legacy-venus/systemd/eidp-r8-rediscovery.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemd-analyze verify eidp-r8-rediscovery.{service,timer}
sudo systemctl enable --now eidp-r8-rediscovery.timer
```

When migrating from cron to systemd, **uninstall the cron entry first** to
avoid double-firing.

## Outputs

Each run writes:

- `logs/r8-rediscovery/run-{utc-ts}.log`           — wrapper stdout/stderr (12-week ring buffer)
- `logs/r8-rediscovery/.last_failure`              — only present on non-zero exit
- `output/target-year-discovery/{run_id}-summary.json`
- `output/target-year-discovery/{run_id}-discovery-rejections.jsonl`
- `output/target-year-discovery/{run_id}-ingest-rejections.jsonl`
- `output/target-year-discovery/{run_id}-discovery-rca-batch-plan.json`

The summary contains before/after snapshots for coverage, PDF gaps, extraction,
new document IDs, discovery stats, ingest stats, deltas, and a `discovery_rca`
section pointing to the Codex RCA batch plan when discovery evidence was
recorded. It also records `target_pdf_auto_acquired_count`,
`target_pdf_auto_yield_pct`, `operator_reviewable_count`,
`operator_reviewable_yield_pct`, `ship_gate_operator_coverage_pct`, and
`ship_gate_status`; use the operator-reviewable fields as the direct weekly
evidence for the ship gate. The automatic target-PDF yield remains a diagnostic
field.

## Verification (after a run)

```bash
.venv/bin/python -m eidp report coverage --school-type 専門学校 --fy 2026
.venv/bin/python -m eidp report gaps --kind pdf --school-type 専門学校 --fy 2026
.venv/bin/python -m eidp report extraction --fy 2026
```

Expect `target_FY2026` to rise only when schools have actually published
FY2026（令和8年度） PDFs. A zero-delta weekly run is valid during the pre-peak period.

## Recovery

If the wrapper is interrupted (reboot mid-run, OOM, etc.), rerun it. Behavior:

- `flock` ensures at most one run at a time. If a previous invocation crashed
  without releasing the lock, the lock file is automatically released when its
  pid exits — re-running on the next schedule is safe.
- The runner only ingests documents created during the current run.
- Duplicate-hash rediscovery evidence is recorded without blocking later
  candidates (Sprint 4 fix `3a35642`).

To inspect the most recent failure:

```bash
cat ~/workspace/EIDP/logs/r8-rediscovery/.last_failure
tail -100 "$(ls -t ~/workspace/EIDP/logs/r8-rediscovery/run-*.log | head -1)"
```

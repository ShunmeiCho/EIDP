# EIDP R8 Rediscovery Timer Runbook

## Purpose

Sprint 4 proved that one-time stale rediscovery has zero R8 yield before the
5-6月 publication peak. Sprint 7 converts that waiting period into a weekly
systemd job:

1. Select 専門学校 with an older ingested target PDF and no FY2026 target PDF.
2. Revisit trusted `prefecture_aggregator` URLs.
3. Ingest only documents downloaded during the same run.
4. Write a JSON summary and rejection evidence under
   `output/r8-rediscovery-weekly/`.

## Preflight

```bash
cd ~/workspace/EIDP
git status --short
git pull --ff-only
uv run python scripts/run_r8_rediscovery_weekly.py --dry-run --limit 5
```

The dry run is read-only against the database and should print a summary path,
the stale school count, and zero discovery/ingest stats.

## Install

Production installation requires owner authorization because enabling the timer
causes recurring DB writes and PDF downloads.

```bash
sudo cp deploy/systemd/eidp-r8-rediscovery.service /etc/systemd/system/
sudo cp deploy/systemd/eidp-r8-rediscovery.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now eidp-r8-rediscovery.timer
systemctl list-timers eidp-r8-rediscovery.timer
```

Confirm the Venus host timezone is JST:

```bash
timedatectl
```

## Manual Run

Use a limited run first if you need a production smoke test:

```bash
uv run python scripts/run_r8_rediscovery_weekly.py --limit 10
```

For the same command through systemd:

```bash
sudo systemctl start eidp-r8-rediscovery.service
journalctl -u eidp-r8-rediscovery.service -f
```

## Outputs

Each run writes:

- `output/r8-rediscovery-weekly/{run_id}-summary.json`
- `output/r8-rediscovery-weekly/{run_id}-discovery-rejections.jsonl`
- `output/r8-rediscovery-weekly/{run_id}-ingest-rejections.jsonl`

The summary contains before/after snapshots for coverage, PDF gaps, extraction,
new document IDs, discovery stats, ingest stats, and deltas.

## Verification

After a run:

```bash
uv run eidp report coverage --school-type 専門学校 --fy 2026
uv run eidp report gaps --kind pdf --school-type 専門学校 --fy 2026
uv run eidp report extraction --fy 2026
```

Expect `target_FY2026` to rise only when schools have actually published R8
PDFs. A zero-delta weekly run is valid during the pre-peak period.

## Recovery

If the service is interrupted, rerun it. The runner only ingests documents
created during the current run, and duplicate-hash rediscovery evidence is
recorded without blocking later candidates.

Disable the schedule with:

```bash
sudo systemctl disable --now eidp-r8-rediscovery.timer
```

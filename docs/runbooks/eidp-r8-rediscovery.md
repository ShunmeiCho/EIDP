# Target-Year Rediscovery Runbook

The discovery runner is support-only for Linux/Web v1. Business users provide
or confirm the correct PDF; discovery yield is not a v1 release gate.

## Boundary

Run only from `/home/junming/EIDP` and its project virtual environment. Do not
install system packages, create files elsewhere, or configure cron/systemd as
part of this runbook.

## Preflight

```bash
cd /home/junming/EIDP
test "$(pwd -P)" = /home/junming/EIDP
test -x .venv/bin/python
.venv/bin/python -c 'import sys; assert sys.prefix.endswith("/.venv"); print(sys.prefix)'
git status --short
```

## Dry Run

```bash
EIDP_APP_ROOT=/home/junming/EIDP \
  .venv/bin/python scripts/run_weekly_target_year_discovery.py --dry-run --limit 5
```

The dry run must not mutate business tables. Review the generated summary under
`output/target-year-discovery/` before authorizing a write run.

## Authorized Write Run

```bash
EIDP_APP_ROOT=/home/junming/EIDP \
  .venv/bin/python scripts/run_weekly_target_year_discovery.py --limit 10
```

The runner shares the application lock with Web mutations. If the lock is busy,
do not bypass it; wait for the active writer or investigate a stale lock.

## Outputs

- `output/target-year-discovery/{run_id}-summary.json`
- `output/target-year-discovery/{run_id}-discovery-rejections.jsonl`
- `output/target-year-discovery/{run_id}-ingest-rejections.jsonl`
- `output/target-year-discovery/{run_id}-discovery-rca-batch-plan.json`

Treat automatic-yield fields as acquisition-health diagnostics. Excel output
continues to require confirmed fiscal year, identity, document type, confidence
or review acceptance, reconciliation, and audit evidence.

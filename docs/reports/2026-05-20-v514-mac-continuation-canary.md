# v514 Mac Continuation Canary

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
Source head: `36208f537cd9f00769f38748948cf6506774c168`
Package candidate: `dist/eidp-windows-v514.zip`

## Summary

This is a bounded Mac-side continuation canary after the v514 weekly
selected-site-count fix. It is not a substitute for the pending v514 Windows
side-by-side smoke.

The first attempted sandbox copied `data/eidp.sqlite3`, but that file is an
empty shell database in this checkout and has no `school` table. That run
failed before crawling and is not used as release evidence.

The usable canary copied the structured v513 isolated database from
`_temp/v513-mac-limit50/data/eidp.sqlite3` into a fresh sandbox:
`_temp/v514-mac-limit50-from-v513`. This makes the run a continuation canary
from the v513 isolated state, not a fresh Windows v502 replacement.

## Command

```bash
env \
  EIDP_APP_ROOT=$PWD/_temp/v514-mac-limit50-from-v513 \
  EIDP_DATABASE_URL=sqlite:///$PWD/_temp/v514-mac-limit50-from-v513/data/eidp.sqlite3 \
  EIDP_TARGET_FISCAL_YEAR=2026 \
  uv run python scripts/run_weekly_target_year_discovery.py \
    --current-fy 2026 \
    --limit 50 \
    --batch-size 50 \
    --rate-limit 0.1 \
    --request-timeout 12 \
    --ingest-batch-size 10 \
    --storage-dir _temp/v514-mac-limit50-from-v513/data/pdfs \
    --output-dir _temp/v514-mac-limit50-from-v513/data/output/target-year-discovery \
    --last-run-path _temp/v514-mac-limit50-from-v513/data/output/last_run.json \
    --logs-dir _temp/v514-mac-limit50-from-v513/logs \
    --no-lock \
    --json
```

## Evidence

The run wrote:

- `_temp/v514-mac-limit50-from-v513/data/output/target-year-discovery/20260519_233340-summary.json`
- `_temp/v514-mac-limit50-from-v513/data/output/target-year-discovery/20260519_233340-discovery-rca-batch-plan.json`
- `_temp/v514-mac-limit50-from-v513/data/output/target-year-discovery/20260519_233340-discovery-rejections.jsonl`
- `_temp/v514-mac-limit50-from-v513/data/output/last_run.json`

Result:

```json
{
  "selection_mode": "target_missing",
  "target_missing_school_count": 50,
  "discovery_stats": {
    "crawled": 56,
    "found": 50,
    "downloaded": 0,
    "failed": 3,
    "skipped": 952,
    "candidate_school_mismatch": 69,
    "rejection_reason_fiscal_year_mismatch": 260,
    "rejection_reason_target_fiscal_year_not_detected": 7
  },
  "target_pdf_auto_acquired_count": 2,
  "target_pdf_auto_yield_pct": 4.0,
  "operator_reviewable_count": 47,
  "operator_reviewable_yield_pct": 94.0,
  "ship_gate_status": "below_gate"
}
```

The run proves the v514 selected-site-count fix is active in a larger bounded
run: 50 selected schools expanded to 56 crawled site rows. It also confirms the
release blocker remains: no new strict FY2026/R8 target PDFs were downloaded,
and the current-FY ship gate is still below threshold.

## RCA Buckets

The RCA batch plan contains 20 items across 50 candidates:

| Bucket | Count |
| --- | ---: |
| `publication_lag_or_old_target_pdf` | 11 |
| `target_form_without_year_evidence` | 4 |
| `non_target_candidates_only` | 3 |
| `no_pdf_candidates` | 2 |

Top evidence reasons across RCA packets:

| Reason | Count |
| --- | ---: |
| `pre_filtered_non_target_hint` | 76 |
| `candidate_school_mismatch` | 15 |
| `fiscal_year_mismatch:2022` | 13 |
| `fiscal_year_mismatch:2020` | 12 |
| `fiscal_year_mismatch:2021` | 12 |
| `fiscal_year_mismatch:2024` | 12 |
| `fiscal_year_mismatch:2023` | 11 |
| `fiscal_year_mismatch:2025` | 11 |
| `fiscal_year_mismatch:2019` | 10 |
| `target_fiscal_year_not_detected` | 7 |
| `duplicate_hash` | 2 |
| `no_candidates_found` | 2 |
| `classified_non_target` | 1 |

## Same-Domain 2026 Probe

For the 11 `fiscal_year_mismatch:2025` target PDFs, a bounded same-domain
probe tried the obvious `2025 -> 2026` URL transformation.

Ten transformed URLs returned `404`. The remaining URL was a hash filename
without a year token, so the transformation did not change it; it returned
`200` only because it was the original FY2025 mismatch candidate. This gives
no current FY2026/R8 strict evidence.

## Release Boundary

This canary strengthens the FY2026/R8 no-go evidence. The dominant failure
mode is not the v514 site-row cap bug anymore; the selected schools are being
crawled. The dominant bounded-sample reasons are publication lag or old target
PDFs, target forms without FY2026/R8 year evidence, non-target candidates, and
a small residual no-candidate bucket.

The release remains blocked unless the current FY2026/R8 strict line reaches
the required threshold or the explicit `publication_lag` exception is approved
and owner Windows evidence is returned.

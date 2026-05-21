# v521 Mac Limit-50 Continuation Canary

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
Source commit: `22c64aeafbf46e5a57a2547c4e10e63cbbb1fdb2`
Package candidate remains: `dist/eidp-windows-v519.zip`

## Scope

This is a bounded Mac-side continuation canary after v520/v521 source changes:

- v520 added exact Katayanagi crawl entries while keeping NEEC no-year PDFs
  untrusted for target-FY fill.
- v521 suppresses same-school `corporation_pattern` rows when usable
  `school_domain_override` rows exist in the default discovery scope.

This is not a replacement for the pending Windows side-by-side smoke.

## Command

Sandbox:

```text
_temp/v521-mac-limit50-with-url-sources
```

```bash
env \
  EIDP_APP_ROOT=$PWD/_temp/v521-mac-limit50-with-url-sources \
  EIDP_DATABASE_URL=sqlite:///$PWD/_temp/v521-mac-limit50-with-url-sources/data/eidp.sqlite3 \
  EIDP_TARGET_FISCAL_YEAR=2026 \
  uv run python scripts/run_weekly_target_year_discovery.py \
    --current-fy 2026 \
    --limit 50 \
    --batch-size 60 \
    --rate-limit 0.1 \
    --request-timeout 12 \
    --ingest-batch-size 10 \
    --storage-dir _temp/v521-mac-limit50-with-url-sources/data/pdfs \
    --output-dir _temp/v521-mac-limit50-with-url-sources/data/output/target-year-discovery \
    --last-run-path _temp/v521-mac-limit50-with-url-sources/data/output/last_run.json \
    --logs-dir _temp/v521-mac-limit50-with-url-sources/logs \
    --no-lock \
    --json
```

## Evidence

- `_temp/v521-mac-limit50-with-url-sources/data/output/target-year-discovery/20260520_031446-summary.json`
- `_temp/v521-mac-limit50-with-url-sources/data/output/target-year-discovery/20260520_031446-discovery-rca-batch-plan.json`
- `_temp/v521-mac-limit50-with-url-sources/data/output/target-year-discovery/20260520_031446-discovery-rejections.jsonl`
- `_temp/v521-mac-limit50-with-url-sources/data/output/last_run.json`

URL-source import was active:

```json
{
  "seed_skipped_existing": 50,
  "corporation_inferred": 8,
  "corporation_skipped_has_url": 612,
  "school_override_inferred": 8,
  "school_override_skipped_existing": 109,
  "school_override_skipped_no_school": 0
}
```

Result:

```json
{
  "selection_mode": "target_missing",
  "target_missing_school_count": 50,
  "discovery_stats": {
    "crawled": 54,
    "found": 50,
    "downloaded": 0,
    "failed": 0,
    "skipped": 1038,
    "candidate_school_mismatch": 0,
    "rejection_reason_fiscal_year_mismatch": 302,
    "rejection_reason_classified_non_target": 95,
    "rejection_reason_pre_filtered_non_target_hint": 683,
    "rejection_reason_target_fiscal_year_not_detected": 5
  },
  "target_pdf_auto_acquired_count": 0,
  "target_pdf_auto_yield_pct": 0.0,
  "operator_reviewable_count": 50,
  "operator_reviewable_yield_pct": 100.0,
  "ship_gate_status": "below_gate"
}
```

## RCA Buckets

The RCA batch plan contains 20 items across 50 candidates:

| Bucket | Count |
| --- | ---: |
| `publication_lag_or_old_target_pdf` | 17 |
| `target_form_without_year_evidence` | 3 |

The v519 continuation canary had 16 publication-lag rows and 4 no-year rows.
After v521, `日本工学院北海道専門学校` moves into
`publication_lag_or_old_target_pdf` via the exact NKHS disclosure page, while
the NEEC Kamata/Hachioji rows remain `target_form_without_year_evidence`.

## Comparison To v519

| Metric | v519 canary | v521 canary |
| --- | ---: | ---: |
| `school_override_inferred` | 5 | 8 |
| `crawled` | 58 | 54 |
| `found` | 54 | 50 |
| `failed` | 4 | 0 |
| `candidate_school_mismatch` | 69 | 0 |
| strict target PDFs | 0/50 | 0/50 |
| operator-reviewable | 50/50 | 50/50 |
| `ship_gate_status` | `below_gate` | `below_gate` |

## Release Boundary

This is a crawl/RCA hygiene improvement, not release approval. It removes noisy
same-school corporation-root crawling and clarifies the Katayanagi evidence
without counting no-year NEEC PDFs as current FY2026/R8 successes.

The release remains blocked unless the current FY2026/R8 strict line reaches
the required threshold or the explicit `publication_lag` exception is approved
and owner Windows evidence is returned.

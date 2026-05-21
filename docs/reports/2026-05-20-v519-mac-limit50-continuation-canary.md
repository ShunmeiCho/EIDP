# v519 Mac Limit-50 Continuation Canary

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
Package candidate: `dist/eidp-windows-v519.zip`
Package source commit: `24fa09a49115196c2a977296eec127f6747e4426`
Package SHA256: `fbc2ae0016b7b293c0fd534d7b3e7eb881f74205fa6df19acda42a8d21ba195a`

## Scope

This is a bounded Mac-side continuation canary after the v517 Sanko exact-school
URL overrides and the v519 vocational-practice basic-information PDF filter. It
is not a substitute for the pending v519 Windows side-by-side smoke.

The canary copied the structured v516 target-selection sandbox database into a
fresh app root:

```text
_temp/v519-mac-limit50-with-url-sources
```

Unlike the first local attempt at `_temp/v519-mac-limit50-continuation`, this
app root also copied `data/url-discovery/`. The first attempt did not load the
checked-in URL source CSV files, so it did not exercise the v517 school-domain
overrides and is not used as the current v519 continuation evidence.

## Command

```bash
env \
  EIDP_APP_ROOT=$PWD/_temp/v519-mac-limit50-with-url-sources \
  EIDP_DATABASE_URL=sqlite:///$PWD/_temp/v519-mac-limit50-with-url-sources/data/eidp.sqlite3 \
  EIDP_TARGET_FISCAL_YEAR=2026 \
  uv run python scripts/run_weekly_target_year_discovery.py \
    --current-fy 2026 \
    --limit 50 \
    --batch-size 60 \
    --rate-limit 0.1 \
    --request-timeout 12 \
    --ingest-batch-size 10 \
    --storage-dir _temp/v519-mac-limit50-with-url-sources/data/pdfs \
    --output-dir _temp/v519-mac-limit50-with-url-sources/data/output/target-year-discovery \
    --last-run-path _temp/v519-mac-limit50-with-url-sources/data/output/last_run.json \
    --logs-dir _temp/v519-mac-limit50-with-url-sources/logs \
    --no-lock \
    --json
```

## Evidence

The run wrote:

- `_temp/v519-mac-limit50-with-url-sources/data/output/target-year-discovery/20260520_022139-summary.json`
- `_temp/v519-mac-limit50-with-url-sources/data/output/target-year-discovery/20260520_022139-discovery-rca-batch-plan.json`
- `_temp/v519-mac-limit50-with-url-sources/data/output/target-year-discovery/20260520_022139-discovery-rejections.jsonl`
- `_temp/v519-mac-limit50-with-url-sources/data/output/last_run.json`

URL-source import was active:

```json
{
  "seed_skipped_existing": 50,
  "corporation_inferred": 5,
  "corporation_skipped_has_url": 612,
  "school_override_inferred": 5,
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
    "crawled": 58,
    "found": 54,
    "downloaded": 0,
    "failed": 4,
    "skipped": 1060,
    "rejection_reason_fiscal_year_mismatch": 295,
    "rejection_reason_classified_non_target": 85,
    "rejection_reason_pre_filtered_non_target_hint": 722,
    "rejection_reason_target_fiscal_year_not_detected": 7
  },
  "target_pdf_auto_acquired_count": 0,
  "target_pdf_auto_yield_pct": 0.0,
  "operator_reviewable_count": 50,
  "operator_reviewable_yield_pct": 100.0,
  "ship_gate_status": "below_gate"
}
```

The run confirms the v517 URL overrides are exercised in the bounded queue:
school ID 55, `東京こども専門学校`, crawled
`https://www.sanko.ac.jp/tokyo-child/` and moved into
`publication_lag_or_old_target_pdf` evidence. It did not become an FY2026/R8
strict success.

## RCA Buckets

The RCA batch plan contains 20 items across 50 candidates:

| Bucket | Count |
| --- | ---: |
| `publication_lag_or_old_target_pdf` | 16 |
| `target_form_without_year_evidence` | 4 |

The 20 RCA schools are:

| School ID | School | Bucket |
| ---: | --- | --- |
| 44 | 東京ビューティ＆ブライダル専門学校 | `target_form_without_year_evidence` |
| 1 | 日本工学院専門学校 | `target_form_without_year_evidence` |
| 2 | 日本工学院八王子専門学校 | `target_form_without_year_evidence` |
| 3 | 日本工学院北海道専門学校 | `target_form_without_year_evidence` |
| 43 | 東京ビューティアート専門学校 | `publication_lag_or_old_target_pdf` |
| 29 | 札幌スポーツ&メディカル専門学校 | `publication_lag_or_old_target_pdf` |
| 42 | 千葉ビューティ＆ブライダル専門学校 | `publication_lag_or_old_target_pdf` |
| 49 | 福岡ビューティアート専門学校 | `publication_lag_or_old_target_pdf` |
| 18 | 東京医療秘書歯科衛生＆IT専門学校 | `publication_lag_or_old_target_pdf` |
| 32 | 東京リゾート＆スポーツ専門学校 | `publication_lag_or_old_target_pdf` |
| 55 | 東京こども専門学校 | `publication_lag_or_old_target_pdf` |
| 13 | 札幌医療秘書福祉＆IT専門学校 | `publication_lag_or_old_target_pdf` |
| 47 | 大阪ビューティアート専門学校 | `publication_lag_or_old_target_pdf` |
| 50 | 沖縄ビューティ＆ブライダル専門学校 | `publication_lag_or_old_target_pdf` |
| 51 | 札幌こども専門学校 | `publication_lag_or_old_target_pdf` |
| 21 | 名古屋医療秘書福祉&IT専門学校 | `publication_lag_or_old_target_pdf` |
| 14 | 仙台医療秘書福祉＆IT専門学校 | `publication_lag_or_old_target_pdf` |
| 22 | 大阪医療秘書福祉&IT専門学校 | `publication_lag_or_old_target_pdf` |
| 37 | 福岡リゾート＆スポーツ専門学校 | `publication_lag_or_old_target_pdf` |
| 52 | 仙台こども専門学校 | `publication_lag_or_old_target_pdf` |

## Release Boundary

This canary strengthens the FY2026/R8 blocker evidence. The latest v517-v519
source behavior improves review hygiene and removes the residual
`non_target_candidates_only` bucket in this bounded queue, but it still finds no
strict FY2026/R8 target-form PDF.

The release remains blocked unless the current FY2026/R8 strict line reaches
the required threshold or the explicit `publication_lag` exception is approved
and owner Windows evidence is returned.

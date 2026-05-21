# v522 Stale-Yearless RCA Bucket Source Report

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
Source commit: `8a5437042e9db0ebff144afcfc0cf84706b1ff80`
Package candidate remains: `dist/eidp-windows-v519.zip`

## Scope

v522 is a source-side RCA hygiene fix after the v521 limit-50 continuation
canary. It does not change PDF download, ingest, strict target-year acceptance,
or Windows packaging.

The v521 canary left three `target_form_without_year_evidence` RCA items. Two
are still true NEEC no-year target-form cases. The third, school ID 44
`東京ビューティ＆ブライダル専門学校`, had an old no-year/image-only row labeled
`2019年度` plus an explicit `2025年度` target-form PDF:

```text
https://www.sanko.ac.jp/tachikawa-beauty/disclosure/2025/docs/yoshiki2025.pdf
```

That shape is publication-lag evidence, not an unresolved current-year no-year
target-form candidate.

## Change

`src/eidp/scraper/discovery_evidence_summary.py` now treats
`target_fiscal_year_not_detected` rows as unresolved no-year target evidence
only when the candidate URL/anchor text does not already carry an explicit
stale fiscal-year hint below the target FY.

This preserves the existing NEEC-style behavior: a genuine target form with no
year label still lands in `target_form_without_year_evidence` and stays
operator-reviewable, not strict.

## Evidence

Red test before the fix:

```text
uv run pytest \
  tests/unit/test_discovery_evidence_summary.py::test_summarize_pdf_discovery_evidence_treats_stale_labeled_yearless_target_as_publication_lag \
  -q
```

Result before patch: failed with `target_form_without_year_evidence` instead of
`publication_lag_or_old_target_pdf`.

Focused verification after the fix:

```text
uv run pytest \
  tests/unit/test_discovery_evidence_summary.py::test_summarize_pdf_discovery_evidence_treats_stale_labeled_yearless_target_as_publication_lag \
  tests/unit/test_discovery_evidence_summary.py::test_summarize_pdf_discovery_evidence_prioritizes_yearless_target_over_old_year_target \
  -q
```

Result: `2 passed`.

Adjacent RCA/summary verification:

```text
uv run pytest tests/unit/test_discovery_evidence_summary.py tests/unit/test_cli_discovery_rca_packet.py -q
```

Result: `40 passed`.

Static checks and full suite:

```text
uv run ruff check src/eidp/scraper/discovery_evidence_summary.py tests/unit/test_discovery_evidence_summary.py
uv run mypy src
uv run pytest -q
```

Results:

- Ruff: pass
- Mypy: `Success: no issues found in 89 source files`
- Full unit suite: `1897 passed, 5 warnings`

## v521 Evidence Reclassification

Recomputing the v521 RCA batch plan from the existing v521 evidence:

```bash
env EIDP_DATABASE_URL=sqlite:///$PWD/_temp/v521-mac-limit50-with-url-sources/data/eidp.sqlite3 \
  uv run eidp discovery-rca-batch-plan \
    --evidence-log _temp/v521-mac-limit50-with-url-sources/data/output/target-year-discovery/20260520_031446-discovery-rejections.jsonl \
    --target-fiscal-year 2026 \
    --limit 20 \
    --json
```

The top 20 RCA bucket counts move from the v521 report's `17/3` split to:

| Bucket | Count |
| --- | ---: |
| `publication_lag_or_old_target_pdf` | 18 |
| `target_form_without_year_evidence` | 2 |

The first two RCA items remain:

| School ID | School | Bucket |
| ---: | --- | --- |
| 1 | 日本工学院専門学校 | `target_form_without_year_evidence` |
| 2 | 日本工学院八王子専門学校 | `target_form_without_year_evidence` |

School ID 44 now falls under `publication_lag_or_old_target_pdf`.

## Release Boundary

This improves RCA queue fidelity only. It does not create a FY2026/R8 strict
success and does not approve release. The v521 canary remains strict
`0/50 (0.0%)`, operator-reviewable `50/50 (100.0%)`, and
`ship_gate_status=below_gate`.

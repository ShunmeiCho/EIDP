# v515 Sanko Child Overrides Package

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
Package: `dist/eidp-windows-v515.zip`
Package source commit: `8430bb28013eaaacf6e46d86c55f602d558e354d`
Package SHA256: `cc92db4f905977653b64e8e0bffed7349f1969e1865747b9861d30d2d4081512`

## Summary

v515 is a Mac-side package rebuild after adding exact Sanko child-school URL
overrides for three residual schools from the v514 continuation RCA:

| School ID | School | Exact school root |
| ---: | --- | --- |
| 51 | 札幌こども専門学校 | `https://www.sanko.ac.jp/sapporo-child/` |
| 52 | 仙台こども専門学校 | `https://www.sanko.ac.jp/sendai-child/` |
| 53 | 大宮こども専門学校 | `https://www.sanko.ac.jp/omiya-child/` |

The v514 Mac continuation canary had these schools in the
`non_target_candidates_only` RCA bucket because they only had the shared
corporation URL `https://www.sanko.ac.jp/`. Live probes on 2026-05-20 confirmed
that each exact root and each matching disclosure page resolves.

This is a discovery-evidence fix, not a release-gate bypass. The new canary
finds school-level target-form PDFs through FY2025/R7 for all three schools,
but no FY2026/R8 target-form PDF. They therefore become operator-reviewable
publication-lag evidence, not strict current-FY auto-acquisitions.

## Canary Evidence

The canary copied the structured v513 isolated database into:

- `_temp/v515-mac-limit50-sanko-child/data/eidp.sqlite3`

and used current checked-in support data, including the new override CSV rows.

The run wrote:

- `_temp/v515-mac-limit50-sanko-child/data/output/target-year-discovery/20260519_235339-summary.json`
- `_temp/v515-mac-limit50-sanko-child/data/output/target-year-discovery/20260519_235339-discovery-rca-batch-plan.json`
- `_temp/v515-mac-limit50-sanko-child/data/output/target-year-discovery/20260519_235339-discovery-rejections.jsonl`

Result:

```json
{
  "target_missing_school_count": 50,
  "url_source_stats": {
    "corporation_inferred": 3,
    "school_override_inferred": 3
  },
  "discovery_stats": {
    "crawled": 59,
    "found": 53,
    "downloaded": 0,
    "failed": 3,
    "skipped": 1008,
    "rejection_reason_fiscal_year_mismatch": 281
  },
  "target_pdf_auto_acquired_count": 2,
  "target_pdf_auto_yield_pct": 4.0,
  "operator_reviewable_count": 50,
  "operator_reviewable_yield_pct": 100.0,
  "ship_gate_status": "below_gate"
}
```

RCA buckets in the 20-item batch plan:

| Bucket | Count |
| --- | ---: |
| `publication_lag_or_old_target_pdf` | 14 |
| `target_form_without_year_evidence` | 4 |
| `no_pdf_candidates` | 2 |
| `non_target_candidates_only` | 0 |

The three Sanko child schools each produced seven target-form rejections for
FY2019-FY2025. The latest visible target-form evidence is FY2025/R7:

| School ID | Latest target-form evidence | Result |
| ---: | --- | --- |
| 51 | `https://www.sanko.ac.jp/disclosure/sapporo-child/yoshiki2025.pdf` | `fiscal_year_mismatch:2025` |
| 52 | `https://www.sanko.ac.jp/disclosure/sendai-child/docs/yoshiki2025.pdf` | `fiscal_year_mismatch:2025` |
| 53 | `https://www.sanko.ac.jp/disclosure/omiya-child/docs/yoshiki2025.pdf` | `fiscal_year_mismatch:2025` |

Compared with v514, the bounded run moved from `crawled=56`, `found=50`,
operator-reviewable `47/50`, and three `non_target_candidates_only` RCA items
to `crawled=59`, `found=53`, operator-reviewable `50/50`, and no residual
`non_target_candidates_only` bucket. Strict FY2026/R8 yield remains
`2/50 (4.0%)`.

## Verification

| Check | Result |
| --- | --- |
| Focused URL discovery + weekly runner unit suites | `uv run pytest tests/unit/test_url_discovery.py tests/unit/test_run_weekly_target_year_discovery.py -q` -> `59 passed` |
| Ruff | `uv run ruff check tests/unit/test_url_discovery.py` -> pass |
| Whitespace check | `git diff --check` -> pass |
| Build | `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v515.zip --latest-alias` -> wrote v515 ZIP and refreshed latest alias |
| Core + OCR add-on verifier | `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v515.zip --ocr-addon dist/eidp-ocr-addon-windows-v497-smoke.zip --json` -> core `ok=true`, OCR add-on `ok=true` |
| Non-Windows release gate | `logs/win-v515-stage6-v515-non-windows-release-gates-20260520.json` -> `ok=true`, package/source fresh, full unit `1891 passed` |
| Post-docs-only release gate | `logs/win-v515-stage6-v515-post-docs-only-gates-20260520.json` -> `ok=true`, `docs_only_stale=true`, full unit `1891 passed` |

## Release Boundary

v515 is the latest package/source candidate. It has not completed Windows
side-by-side validation because the Windows OpenSSH/IP blocker remains
unresolved.

v502 remains the latest partial Windows side-by-side setup/canary package, and
v501 remains the latest complete Windows side-by-side smoke package.

v1.0 remains blocked until the FY2026/R8 strict-yield issue is resolved or the
`publication_lag` exception is explicitly approved, and until owner real-cycle
sign-off is returned.

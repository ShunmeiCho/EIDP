# v517 Remaining Sanko Child Overrides Package

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
Package: `dist/eidp-windows-v517.zip`
Package source commit: `12f11a64ebb40d3997adc3c128d0312131fad14a`
Package SHA256: `6fa1311c74954aaf5a8256a937935672d53e89c71d8e8cd0e70a3beddb582666`

## Summary

v517 is a Mac-side package rebuild after the v516 limit-50 target-missing
canary confirmed the queue fix and exposed one remaining Sanko child-school URL
gap.

The v516 canary at
`_temp/v516-mac-limit50-target-selection/data/output/target-year-discovery/20260520_004005-summary.json`
crawled 57 site rows for 50 selected target-missing schools, found 53 candidate
PDFs, downloaded 0 new strict current-FY PDFs, reported strict `0/50 (0.0%)`,
operator-reviewable `49/50 (98.0%)`, and kept `ship_gate_status=below_gate`.
The corresponding RCA batch excluded school IDs 4 and 7, confirming that
already confirmed current-FY target documents no longer re-enter the
target-missing acquisition queue.

The only residual `non_target_candidates_only` RCA item was school ID 55,
`東京こども専門学校`. Its registered site was only the Sanko corporation root:
`https://www.sanko.ac.jp/`. v517 adds the five remaining live-verified Sanko
child-school exact site overrides:

| Prefecture | School | URL |
| --- | --- | --- |
| 東京都 | 東京こども専門学校 | `https://www.sanko.ac.jp/tokyo-child/` |
| 神奈川県 | 横浜こども専門学校 | `https://www.sanko.ac.jp/yokohama-child/` |
| 愛知県 | 名古屋こども専門学校 | `https://www.sanko.ac.jp/nagoya-child/` |
| 大阪府 | 大阪こども専門学校 | `https://www.sanko.ac.jp/osaka-child/` |
| 沖縄県 | 沖縄こども専門学校 | `https://www.sanko.ac.jp/okinawa-child/` |

Each root page was fetched on 2026-05-20 and matched its school name in the
returned HTML.

## Targeted Sandbox Evidence

Against a copy of the v516 target-selection sandbox database, running URL
inference with the v517 CSV added 5 new school-domain overrides:

```text
inferred=5
school_override_inferred=5
school_override_skipped_existing=109
school_override_skipped_no_school=0
```

For school ID 55, the registered sites changed from:

```text
https://www.sanko.ac.jp/  corporation_pattern  0.5
```

to:

```text
https://www.sanko.ac.jp/tokyo-child/  school_domain_override  0.95
https://www.sanko.ac.jp/              corporation_pattern     0.5
```

A targeted `discover-pdfs --school-id 55` smoke on that sandbox crawled both
sites and found old-year target-form evidence instead of corporation-only
non-target evidence:

| Metric | Result |
| --- | ---: |
| `crawled` | 2 |
| `found` | 2 |
| `downloaded` | 0 |
| `failed` | 1 |
| `rejection_reason_fiscal_year_mismatch` | 7 |
| `rejection_reason_pre_filtered_non_target_hint` | 27 |
| `rejection_reason_classified_non_target` | 1 |

The seven target-form mismatches cover FY2019 through FY2025, with latest public
target-form URL:

```text
https://www.sanko.ac.jp/disclosure/tokyo-child/docs/yoshiki2025.pdf
```

This moves school ID 55 from `non_target_candidates_only` to
`publication_lag_or_old_target_pdf` style evidence. It does not create a
FY2026/R8 strict target-PDF success.

## Verification

| Check | Result |
| --- | --- |
| Red coverage test before CSV fix | `test_checked_in_school_domain_overrides_cover_sanko_exact_school_sites` failed with exactly the five missing Sanko child-school overrides |
| Focused coverage test | `uv run pytest tests/unit/test_url_discovery.py::test_checked_in_school_domain_overrides_cover_sanko_exact_school_sites -q` -> `1 passed` |
| URL discovery unit suite | `uv run pytest tests/unit/test_url_discovery.py -q` -> `28 passed` |
| Ruff | `uv run ruff check tests/unit/test_url_discovery.py` -> pass |
| Whitespace check | `git diff --check` -> pass |
| Build | `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v517.zip --latest-alias` -> wrote v517 ZIP and refreshed latest alias |
| Core + OCR add-on verifier | `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v517.zip --ocr-addon dist/eidp-ocr-addon-windows-v497-smoke.zip --json` -> core `ok=true`, OCR add-on `ok=true` |
| Non-Windows release gate | `logs/win-v517-stage6-v517-non-windows-release-gates-20260520.json` -> `ok=true`, package/source fresh, full unit `1892 passed` |
| Post-docs-only release gate | `logs/win-v517-stage6-v517-post-docs-only-gates-20260520.json` -> `ok=true`, `docs_only_stale=true`, full unit `1892 passed` |

## Release Boundary

v517 is the latest package/source candidate. It improves target-missing RCA
quality for Sanko child schools but does not improve the FY2026/R8 strict-yield
gate: the targeted smoke found latest FY2025 public target-form evidence for
school ID 55, not FY2026/R8.

v517 has not completed Windows side-by-side validation because the Windows
OpenSSH/IP blocker remains unresolved.

v502 remains the latest partial Windows side-by-side setup/canary package, and
v501 remains the latest complete Windows side-by-side smoke package.

v1.0 remains blocked until the FY2026/R8 strict-yield issue is resolved or the
`publication_lag` exception is explicitly approved, and until owner real-cycle
sign-off is returned.

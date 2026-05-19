# v501 Sanko URL Override Package Evidence

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
Package: `dist/eidp-windows-v501.zip`
Package source commit: `d2fa01d4f060e803f173ecae59bfb0867dbe3afd`
Package SHA256: `a301e4dbc295f5bfd3dc11bc4778db1887f2b8a55dda65f16708e9d8abff3f83`

## Verdict

`MAC_SIDE_PACKAGE_VERIFIED`.

v501 packages the v500 limit-50 RCA follow-up that adds 17 live-verified Sanko
exact school URL overrides. These schools were previously falling back to the
Sanko corporation root (`https://www.sanko.ac.jp/`), which made bounded
FY2026/R8 discovery crawl non-target corporate disclosure material instead of
school-specific pages.

This is not v1.0 approval. v501 has since completed the automated Windows
side-by-side smoke set: setup, validation, recovery, OCR runtime, UI health,
Excel exports, limit-50 canary, and Stage 6 evidence-bundle verification.

## Change

- `data/url-discovery/school_domain_overrides.csv`: added 17 exact Sanko school
  site rows from the v500 limit-50 RCA medical-secretary and resort/sports
  buckets.
- `tests/unit/test_url_discovery.py`: extended the checked-in Sanko override
  coverage test to include those rows.

## Verification

| Check | Result |
| --- | --- |
| Live URL/title probe | All 17 candidate URLs returned HTTP `200` and matching Sanko school titles on 2026-05-20 |
| CSV duplicate check | `104` rows, `104` unique keys, `0` duplicates |
| Targeted URL discovery test | `uv run pytest tests/unit/test_url_discovery.py::test_checked_in_school_domain_overrides_cover_sanko_exact_school_sites -q` -> `1 passed` |
| URL discovery suite | `uv run pytest tests/unit/test_url_discovery.py -q` -> `28 passed` |
| URL + weekly target-year suites | `uv run pytest tests/unit/test_url_discovery.py tests/unit/test_run_weekly_target_year_discovery.py -q` -> `58 passed` |
| Ruff on touched test | `uv run ruff check tests/unit/test_url_discovery.py` -> pass |
| v501 core verifier | `logs/win-v501-stage6-v501-verify-windows-distribution-20260520.json` -> `ok=true` |
| v501 core + OCR add-on verifier | `logs/win-v501-stage6-v501-verify-windows-distribution-with-ocr-addon-20260520.json` -> core `ok=true`, OCR add-on `ok=true` |
| v501 full non-Windows release gate | `logs/win-v501-stage6-v501-non-windows-release-gates-20260520.json` -> `ok=true`, package/source fresh, full unit suite `1880 passed` |
| v501 Windows side-by-side smoke | `docs/reports/2026-05-20-v501-full-windows-side-by-side-smoke.md` -> setup/validate/recovery, OCR runtime, UI, Excel, and Stage 6 verifier `ok=true`; limit-50 strict/Excel-ready `10.0%`, operator-reviewable `80.0%`, `ship_gate_status=below_gate` |
| PR #2 CI after commit | `Python quality gates` and `Ship gate contract` both `SUCCESS`; `mergeStateStatus=CLEAN` |

## Release Impact

v501 supersedes v500 for Mac-side package/source verification and Windows
side-by-side smoke evidence.

The FY2026/R8 ship gate remains blocked. This change improves school-site
coverage for a high-volume Sanko failure cluster, but it does not change strict
target-year acceptance rules and does not convert publication-lag or yearless
target forms into strict FY2026 successes.

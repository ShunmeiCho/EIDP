# v514 Weekly Selected-Site Count Package

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
Package: `dist/eidp-windows-v514.zip`
Package source commit: `928f0e9f4e81bd8874e17d7a09c5b161730c1449`
Package SHA256: `0a198f02a242c06bde9c9e3675e6aa597a1e5d3721c3d05bc9278a87042e0096`

## Summary

v514 is a Mac-side package rebuild after fixing a weekly-runner denominator
bug found while checking the v513 Sanko/NEEC RCA path.

The weekly runner selects a school queue, but `run_pdf_discovery` limits
`SchoolSite` rows. Before v514, a limit-50 run could select 50 schools and
then pass a site-row `batch_size` of only 50. If earlier selected schools had
multiple high-confidence URLs, later selected schools could remain in the
denominator without any crawl evidence. In the Mac v513 limit-50 smoke,
`日本工学院専門学校`, `日本工学院八王子専門学校`, and
`日本工学院北海道専門学校` were in the selected-school denominator but had no
evidence rows because higher-confidence site rows consumed the 50-site cap.

v514 counts crawlable `SchoolSite` rows for the selected school IDs and expands
the discovery batch to at least that site count. This keeps the weekly
denominator school-based while ensuring selected schools actually get crawled.

This is a correctness and evidence-coverage fix, not a release-gate bypass.
The focused NEEC post-fix smoke produced `downloaded=0`, because the visible
NEEC target-form PDFs still lack FY2026/R8 year evidence and include
wrong-school candidates. They remain operator-reviewable, not strict
FY2026/R8 auto-acquisitions.

## Evidence

The pre-fix isolated Mac v513 limit-50 smoke was run under
`_temp/v513-mac-limit50` and wrote:

- `_temp/v513-mac-limit50/data/output/target-year-discovery/20260519_230929-summary.json`
- `_temp/v513-mac-limit50/data/output/target-year-discovery/20260519_230929-discovery-rca-batch-plan.json`

It reported strict/Excel-ready `5/50 (10.0%)`,
operator-reviewable `41/50 (82.0%)`, and `ship_gate_status=below_gate`.
Direct DB/evidence inspection showed NEEC schools 1-3 still had only
`corporation_pattern` sites and no evidence rows from that run.

After the v514 source fix, a focused `--limit 3` smoke against the same
isolated DB wrote:

- `_temp/v513-mac-limit50/data/output/target-year-discovery-after-sitecount-fix/20260519_231930-summary.json`
- `_temp/v513-mac-limit50/data/output/target-year-discovery-after-sitecount-fix/20260519_231930-discovery-rca-batch-plan.json`

It crawled the three NEEC schools:

```json
{
  "target_missing_school_count": 3,
  "discovery_stats": {
    "crawled": 3,
    "found": 3,
    "downloaded": 0,
    "candidate_school_mismatch": 69,
    "rejection_reason_target_fiscal_year_not_detected": 6
  },
  "target_pdf_auto_yield_pct": 0.0,
  "operator_reviewable_yield_pct": 100.0,
  "ship_gate_status": "below_gate"
}
```

The post-fix RCA items are the expected three
`target_form_without_year_evidence` packets for school IDs 1, 2, and 3.

## Verification

| Check | Result |
| --- | --- |
| Focused weekly site-count test | `uv run pytest tests/unit/test_run_weekly_target_year_discovery.py::test_run_weekly_expands_discovery_batch_to_selected_site_count -q` -> `1 passed` |
| Weekly runner unit suite | `uv run pytest tests/unit/test_run_weekly_target_year_discovery.py -q` -> `31 passed` |
| Ruff | `uv run ruff check scripts/run_weekly_target_year_discovery.py tests/unit/test_run_weekly_target_year_discovery.py` -> pass |
| Mypy | `uv run mypy scripts/run_weekly_target_year_discovery.py` -> pass |
| Whitespace check | `git diff --check` -> pass |
| Build | `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v514.zip --latest-alias` -> wrote v514 ZIP and refreshed latest alias |
| Core + OCR add-on verifier | `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v514.zip --ocr-addon dist/eidp-ocr-addon-windows-v497-smoke.zip --json` -> core `ok=true`, OCR add-on `ok=true` |
| Non-Windows release gate | `logs/win-v514-stage6-v514-non-windows-release-gates-20260520.json` -> `ok=true`, package/source fresh, full unit `1891 passed` |

## Release Boundary

v514 is the latest package/source candidate. It has not completed Windows
side-by-side validation because the Windows OpenSSH/IP blocker is still
unresolved.

v502 remains the latest partial Windows side-by-side setup/canary package, and
v501 remains the latest complete Windows side-by-side smoke package.

v1.0 remains blocked until the FY2026/R8 strict-yield issue is resolved or the
`publication_lag` exception is explicitly approved, and until owner real-cycle
sign-off is returned.

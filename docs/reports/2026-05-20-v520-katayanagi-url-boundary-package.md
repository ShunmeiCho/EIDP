# v520 Katayanagi URL Boundary Package

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
Package candidate remains: `dist/eidp-windows-v519.zip`

## Scope

This is a source-side follow-up to the v519 Mac limit-50 continuation canary.
It addresses the remaining `target_form_without_year_evidence` RCA entries for:

- school ID 1, `日本工学院専門学校`
- school ID 2, `日本工学院八王子専門学校`
- school ID 3, `日本工学院北海道専門学校`

The change does not rebuild the Windows ZIP. It keeps the current v519 package
candidate frozen while tightening the next source candidate.

## Changes

- Added checked-in `school_domain_overrides.csv` entries for Katayanagi:
  - NEEC Kamata/Hachioji MEXT support page as exact `school` crawl entries.
  - NKHS public information page as an exact `disclosure` crawl entry.
- Added a URL-discovery unit test proving those checked-in rows remain present.
- Added a PDF-discovery guard so `school_domain_override_disclosure` cannot fill
  missing target FY for yearless PDFs stored under `/documents/portal/syllabus/`.

The NEEC rows are intentionally `url_type=school`, not `disclosure`, because
the live NEEC page lists target-form PDFs without an FY2026/Reiwa 8 label.

## Negative Control

An intermediate diagnostic run temporarily treated the two NEEC rows as
`url_type=disclosure`. That run downloaded 2 PDFs and reported strict
`2/3 (66.7%)`, but ingestion logged that the preserved FY2026 prevalidation
overrode parsed years `2019` and `2025`.

That result is not accepted as current-FY evidence. It is the reason v520 keeps
NEEC as an exact crawl entry without trusted-year fill.

## Final Smoke

Final sandbox:

```text
_temp/v520-katayanagi-overrides-limit3-untrusted-neec
```

Command:

```bash
env \
  EIDP_APP_ROOT=$PWD/_temp/v520-katayanagi-overrides-limit3-untrusted-neec \
  EIDP_DATABASE_URL=sqlite:///$PWD/_temp/v520-katayanagi-overrides-limit3-untrusted-neec/data/eidp.sqlite3 \
  EIDP_TARGET_FISCAL_YEAR=2026 \
  uv run python scripts/run_weekly_target_year_discovery.py \
    --current-fy 2026 \
    --limit 3 \
    --batch-size 10 \
    --rate-limit 0.1 \
    --request-timeout 12 \
    --ingest-batch-size 10 \
    --storage-dir _temp/v520-katayanagi-overrides-limit3-untrusted-neec/data/pdfs \
    --output-dir _temp/v520-katayanagi-overrides-limit3-untrusted-neec/data/output/target-year-discovery \
    --last-run-path _temp/v520-katayanagi-overrides-limit3-untrusted-neec/data/output/last_run.json \
    --logs-dir _temp/v520-katayanagi-overrides-limit3-untrusted-neec/logs \
    --no-lock \
    --json
```

Evidence:

- `_temp/v520-katayanagi-overrides-limit3-untrusted-neec/data/output/target-year-discovery/20260520_025011-summary.json`
- `_temp/v520-katayanagi-overrides-limit3-untrusted-neec/data/output/target-year-discovery/20260520_025011-discovery-rca-batch-plan.json`
- `_temp/v520-katayanagi-overrides-limit3-untrusted-neec/data/output/last_run.json`

Result:

```json
{
  "target_missing_school_count": 3,
  "url_source_stats": {
    "school_override_inferred": 8,
    "school_override_skipped_existing": 109,
    "school_override_skipped_no_school": 0
  },
  "discovery_stats": {
    "crawled": 6,
    "found": 6,
    "downloaded": 0,
    "failed": 0,
    "rejection_reason_target_fiscal_year_not_detected": 10,
    "rejection_reason_fiscal_year_mismatch": 7
  },
  "target_pdf_auto_acquired_count": 0,
  "target_pdf_auto_yield_pct": 0.0,
  "operator_reviewable_count": 3,
  "operator_reviewable_yield_pct": 100.0,
  "ship_gate_status": "below_gate"
}
```

The final smoke confirms the exact URL overrides improve bounded crawl evidence
without converting no-year NEEC PDFs into FY2026/R8 strict successes. The NKHS
page now exposes FY2019-FY2025 target-form evidence for the Hokkaido school,
which remains a publication-lag / review boundary rather than a current-year
success.

## Verification

```text
uv run pytest tests/unit/test_pdf_discovery.py::test_download_pdf_rejects_school_domain_override_yearless_syllabus_target_form -q
1 passed

uv run pytest tests/unit/test_url_discovery.py::test_checked_in_school_domain_overrides_cover_katayanagi_disclosures -q
1 passed

uv run pytest tests/unit/test_pdf_discovery.py::test_download_pdf_accepts_school_domain_override_specific_yearless_target_form tests/unit/test_pdf_discovery.py::test_download_pdf_rejects_school_domain_override_generic_yearless_target_form tests/unit/test_pdf_discovery.py::test_download_pdf_rejects_school_domain_override_yearless_syllabus_target_form tests/unit/test_pdf_discovery.py::test_download_pdf_accepts_school_domain_override_yearless_shinsei_target_form tests/unit/test_pdf_discovery.py::test_download_pdf_accepts_school_domain_override_embedded_studyspt_target_form tests/unit/test_pdf_discovery.py::test_download_pdf_accepts_trusted_prefecture_specific_yearless_target_form tests/unit/test_url_discovery.py::test_checked_in_school_domain_overrides_cover_katayanagi_disclosures -q
7 passed

uv run pytest tests/unit/test_pdf_discovery.py tests/unit/test_url_discovery.py -q
255 passed

uv run ruff check src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py tests/unit/test_url_discovery.py
All checks passed!

uv run pytest -q
1895 passed

uv run mypy src
Success: no issues found in 89 source files
```

## Release Boundary

This tightens source behavior and improves RCA quality, but it does not unblock
v1.0. FY2026/R8 strict yield remains below gate, the v519 Windows smoke remains
blocked by Windows connectivity, owner real-cycle evidence is missing, and the
`publication_lag` exception is still `NOT_APPROVED`.

# v521 School Override Corporation Suppression Package

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
Package candidate remains: `dist/eidp-windows-v519.zip`

## Scope

This is a source-side follow-up to v520. It fixes the remaining crawl-surface
problem exposed by the Katayanagi limit-3 smoke: checked-in exact
`school_domain_override` rows were added correctly, but older
`corporation_pattern` rows for the same school could still be crawled in the
same run and consume batch slots.

The change does not rebuild the Windows ZIP. It tightens source behavior for
the next package candidate.

## Change

`run_pdf_discovery` now suppresses a school's `corporation_pattern` site rows
when the same school has a usable `school_domain_override` row and the current
method scope includes school-domain overrides.

This is query-level suppression, before `batch_size` is applied. It prevents
old low-confidence corporation roots from occupying crawl capacity when a
checked-in exact school/disclosure entry exists.

Explicit diagnostic runs that request only `discovery_methods=["corporation_pattern"]`
still remain possible because the suppression is active only when
`school_domain_override` is in the method scope or the default method set is
used.

## Smoke

Final sandbox:

```text
_temp/v521-katayanagi-skip-corporation-limit3
```

Command:

```bash
env \
  EIDP_APP_ROOT=$PWD/_temp/v521-katayanagi-skip-corporation-limit3 \
  EIDP_DATABASE_URL=sqlite:///$PWD/_temp/v521-katayanagi-skip-corporation-limit3/data/eidp.sqlite3 \
  EIDP_TARGET_FISCAL_YEAR=2026 \
  uv run python scripts/run_weekly_target_year_discovery.py \
    --current-fy 2026 \
    --limit 3 \
    --batch-size 10 \
    --rate-limit 0.1 \
    --request-timeout 12 \
    --ingest-batch-size 10 \
    --storage-dir _temp/v521-katayanagi-skip-corporation-limit3/data/pdfs \
    --output-dir _temp/v521-katayanagi-skip-corporation-limit3/data/output/target-year-discovery \
    --last-run-path _temp/v521-katayanagi-skip-corporation-limit3/data/output/last_run.json \
    --logs-dir _temp/v521-katayanagi-skip-corporation-limit3/logs \
    --no-lock \
    --json
```

Evidence:

- `_temp/v521-katayanagi-skip-corporation-limit3/data/output/target-year-discovery/20260520_030507-summary.json`
- `_temp/v521-katayanagi-skip-corporation-limit3/data/output/target-year-discovery/20260520_030507-discovery-rca-batch-plan.json`
- `_temp/v521-katayanagi-skip-corporation-limit3/data/output/last_run.json`

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
    "crawled": 3,
    "found": 3,
    "downloaded": 0,
    "failed": 0,
    "candidate_school_mismatch": 0,
    "rejection_reason_target_fiscal_year_not_detected": 4,
    "rejection_reason_fiscal_year_mismatch": 7
  },
  "target_pdf_auto_acquired_count": 0,
  "target_pdf_auto_yield_pct": 0.0,
  "operator_reviewable_count": 3,
  "operator_reviewable_yield_pct": 100.0,
  "ship_gate_status": "below_gate"
}
```

Compared with the v520 final limit-3 smoke, crawl rows dropped from 6 to 3 and
`candidate_school_mismatch` dropped from 69 to 0. Strict current-FY success
remained 0, preserving the FY2026/R8 evidence boundary.

## Verification

```text
uv run pytest tests/unit/test_pdf_discovery.py::test_run_pdf_discovery_skips_corporation_pattern_when_school_override_exists -q
1 passed

uv run pytest tests/unit/test_pdf_discovery.py::test_run_pdf_discovery_uses_stable_site_order_for_equal_confidence tests/unit/test_pdf_discovery.py::test_run_pdf_discovery_prioritizes_high_confidence_disclosure_page tests/unit/test_pdf_discovery.py::test_run_pdf_discovery_skips_corporation_pattern_when_school_override_exists tests/unit/test_pdf_discovery.py::test_run_pdf_discovery_marks_school_domain_override_disclosure_as_trusted_year_evidence -q
4 passed

uv run pytest tests/unit/test_pdf_discovery.py -q
227 passed

uv run ruff check src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py
All checks passed!

uv run mypy src
Success: no issues found in 89 source files

uv run pytest -q
1896 passed
```

## Release Boundary

This improves crawl precision and operator RCA quality, but it does not unblock
v1.0. FY2026/R8 strict yield remains below gate, the v519/v521 Windows smoke
remains blocked by Windows connectivity, owner real-cycle evidence is missing,
and the `publication_lag` exception is still `NOT_APPROVED`.

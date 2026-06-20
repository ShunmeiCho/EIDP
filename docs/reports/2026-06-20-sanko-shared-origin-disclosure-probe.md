# Sanko Shared-Origin Disclosure Probe Fix

Date: 2026-06-20
Release conclusion: `NOT_READY`

## Current-State Audit

| Classification | Finding | Evidence |
| --- | --- | --- |
| P0 release blocker | FY2026/Reiwa 8 strict Excel-ready yield remains below gate. | v535 Stage 6 RCA summary: `12/50 (24.0%)`, `BELOW_GATE` |
| P0 release blocker | Owner real Windows cycle/sign-off is still missing. | Current release status and owner docs remain request/return artifacts, not returned sign-off evidence |
| P0 release blocker | `publication_lag` release exception is not approved. | `docs/reports/2026-05-19-publication-lag-release-exception-record.md`: `NOT_APPROVED` |
| P0 release blocker | v535 OCR scope remains unresolved. | Latest complete OCR runtime proof is older than v535 |
| P1 release hardening | One v535 RCA packet remains `non_target_candidates_only` for a Sanko official school root. | `scripts/summarize_stage6_rca.py` over v535 evidence reports school ID `41`, `大宮ビューティ＆ブライダル専門学校`, source `https://www.sanko.ac.jp/omiya-beauty/` |

## Change

The PDF discovery shared-origin throttle already preserves one priority
per-school derived disclosure probe for Sanko-style school roots. The v535 RCA
shows a remaining Sanko `non_target_candidates_only` case where the registered
source is a school root rather than an already-known disclosure page.

This patch keeps both stable same-host school-slug disclosure shapes under the
shared-origin throttle:

```text
https://www.sanko.ac.jp/disclosure/{slug}
https://www.sanko.ac.jp/{slug}/disclosure
```

The broader generic derived probes remain capped. This is not broad web/PDF
search and does not relax strict fiscal-year or school-identity gates.

## Verification

Targeted local verification:

```bash
uv run pytest tests/unit/test_pdf_discovery.py -k "derived_disclosure or shared_origin or sanko"
```

Result:

```text
13 passed, 226 deselected
```

Lint:

```bash
uv run ruff check src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py
```

Result:

```text
All checks passed!
```

Evidence sanity:

```bash
uv run python scripts/summarize_stage6_rca.py logs/win-v535-stage6/stage6-evidence-20260620-053032.zip --json
```

Result highlights:

```text
ok=true
strict_yield.conclusion=BELOW_GATE
strict_yield.excel_ready_acquired_count=12
strict_yield.denominator=50
school 41 bucket=non_target_candidates_only
school 41 registered_source=https://www.sanko.ac.jp/omiya-beauty/
```

## Remaining Risk

The fresh v536 Windows canary has now exercised this source hardening:

```text
docs/reports/2026-06-20-v536-sanko-fresh-windows-canary.md
logs/win-v536-stage6/stage6-evidence-20260620-074649.zip
```

It confirms `shared_origin_derived_fallback_skipped=0` and reaches
`https://www.sanko.ac.jp/omiya-beauty/disclosure/` for school `41`. The packet
still remains `non_target_candidates_only` because the official page currently
offers `schoolinfo.pdf` and school/program information PDFs rather than an
acceptable FY2026/R8 target document.

Old-year PDFs, missing-year candidates, school mismatch candidates, and
non-target PDFs must still remain out of Excel. Release remains `NOT_READY`.

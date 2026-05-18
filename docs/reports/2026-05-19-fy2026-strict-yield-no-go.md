# FY2026 Strict-Yield No-Go Evidence

Date: 2026-05-19  
Branch: `sprint8-handoff-finalize`  
Source package lane: `v485` active on the Windows operator PC

## Verdict

Do not proceed to v1.0 merge, tag, or owner sign-off under the strict current-FY
FY2026/R8 contract.

The current 60% strict target-PDF / Excel-ready ship line is mathematically
unreachable in the latest sandbox replay. After `607/1000` denominator schools,
the replay had discovered `0` FY2026 target documents. Even if every remaining
school passed, the maximum possible strict yield would be `39.3%`.

## Evidence

Local source artifacts:

- `logs/win-v485-stage6/fy2026-strict-yield-upper-bound-fail-20260519.json`
- `logs/win-v485-stage6/fy2026-strict-yield-rca-20260519.json`
- `logs/win-v485-stage6/fy2026-current-hint-target-samples-20260519.json`
- `logs/win-v485-stage6/final-objective-audit-current.json`

The replay used a sandbox copy of the URL-rich DB and did not modify the active
Windows operator DB.

Key metrics:

| Metric | Value |
| --- | ---: |
| Denominator | `1000` |
| Processed before mathematical failure bound | `607` |
| Latest school ID observed | `661` |
| FY2026 documents discovered | `0` |
| Remaining schools | `393` |
| Best-case final strict yield | `39.3%` |
| Required strict yield | `60.0%` |

Top rejection buckets:

| Reason | Count |
| --- | ---: |
| `pre_filtered_non_target_hint` | `8589` |
| `classified_non_target` | `1537` |
| `candidate_school_mismatch` | `958` |
| `fiscal_year_mismatch:2025` | `758` |
| `candidate_budget_dropped` | `645` |
| `fiscal_year_mismatch:2024` | `465` |
| `target_fiscal_year_not_detected` | `237` |
| `fiscal_year_mismatch:2023` | `131` |

For candidates with a `2026` / R8 hint in the URL or anchor text, the top buckets
were still non-target materials and old-year target forms:

| Reason | Count |
| --- | ---: |
| `pre_filtered_non_target_hint` | `2073` |
| `candidate_school_mismatch` | `243` |
| `candidate_budget_dropped` | `242` |
| `classified_non_target` | `61` |
| `fiscal_year_mismatch:2025` | `61` |
| `fiscal_year_mismatch:2024` | `54` |
| `target_fiscal_year_not_detected` | `8` |

## 2026-Hint Sample Probe

Four `2026`-path target-looking PDFs from the Kawahara group were downloaded
for a direct text probe. All four extracted only `令和6年度`, not FY2026/R8.
This confirms that URL upload path or timestamp is not safe fiscal-year
evidence.

| School ID | Probe result |
| ---: | --- |
| `389` | `令和6年度` |
| `389` | `令和6年度` |
| `389` | `令和6年度` |
| `391` | `令和6年度` |

## RCA

The observed failure is not a v485 packaging, Windows deployment, or CI problem.
The pipeline is finding many target-form PDFs, but they are overwhelmingly
FY2025/R7 or earlier. Many FY2026/R8-hinted PDFs are governance disclosures,
school information, syllabi, brochures, or other non-target materials.

Secondary algorithm work remains valuable, especially around
`target_fiscal_year_not_detected`, image-only/OCR handling, and dense-page
candidate ranking. Based on this replay, those secondary buckets are not large
enough to close the current FY2026 gap to 60% by themselves.

## Required Decision

Choose one path before requesting owner E2E or tagging v1.0:

1. Keep v1.0 blocked under the rolling FY2026/R8 contract until enough public
   current-year target PDFs exist.
2. Record an explicit release exception that scopes v1.0 to mature-year FY2025
   proof, then run owner E2E under that exception.

Without one of those decisions, the final objective audit remains `ok=false`.

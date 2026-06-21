# False-Reject Review Validation Summary

Archive: `logs/win-v545-f3eb166-canary/stage6-evidence-20260621-004156.zip`
Release Forecast: `NOT_READY`
Validation OK: `False`
Review status: `invalid`
Completed decisions: `0/53`
Blank decisions: `53`
Context mismatches: `0`

This summary is read-only. It does not fill the worksheet, approve rejected rows, or allow any row into Excel.

## Decision Counts

| Decision | Rows |
| --- | ---: |
| `blank` | 53 |

## Decisions By Bucket

| Bucket | false_reject | correct_reject | needs_operator_review | blank |
| --- | ---: | ---: | ---: | ---: |
| `classified_non_target` | 0 | 0 | 0 | 12 |
| `fiscal_year_mismatch` | 0 | 0 | 0 | 12 |
| `pre_filtered_non_target_hint` | 0 | 0 | 0 | 12 |
| `site_entry_fetch_identity` | 0 | 0 | 0 | 11 |
| `target_fiscal_year_not_detected` | 0 | 0 | 0 | 6 |

## Defect Framing

- Generic algorithm/model failure supported: `False`
- Specific algorithm/rule defect supported: `False`
- Status: `pending_review`
- Reason: Review decisions are incomplete; below-gate yield must not be labeled as an algorithm/model defect yet.

## Blocking Errors

- line 2: decision is required
- line 3: decision is required
- line 4: decision is required
- line 5: decision is required
- line 6: decision is required
- line 7: decision is required
- line 8: decision is required
- line 9: decision is required
- line 10: decision is required
- line 11: decision is required
- line 12: decision is required
- line 13: decision is required
- line 14: decision is required
- line 15: decision is required
- line 16: decision is required
- line 17: decision is required
- line 18: decision is required
- line 19: decision is required
- line 20: decision is required
- line 21: decision is required
- ... 33 more errors

## Next Action

- Fix the listed CSV errors before using this worksheet as release evidence.
- Keep old-year, unknown-year, non-target, school-mismatch, and low-confidence rows out of Excel.

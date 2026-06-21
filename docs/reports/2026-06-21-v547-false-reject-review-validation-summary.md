# False-Reject Review Validation Summary

Archive: `logs/win-v547-86c848f-canary/stage6-evidence-20260621-054545.zip`
Release Forecast: `NOT_READY`
Validation OK: `True`
Review status: `incomplete`
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

- None.

## Next Action

- Fill every blank decision with reviewer, reviewed_at, and required notes before using this worksheet as RCA evidence.
- Keep old-year, unknown-year, non-target, school-mismatch, and low-confidence rows out of Excel.

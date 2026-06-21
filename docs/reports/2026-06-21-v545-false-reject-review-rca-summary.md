# False-Reject RCA Summary

Archive: `logs/win-v545-f3eb166-canary/stage6-evidence-20260621-004156.zip`
Release Forecast: `NOT_READY`
RCA conclusion: `INVALID_RETURN`
Validation OK: `False`
Review status: `invalid`
Completed decisions: `0/53`
Blank decisions: `53`
Context mismatches: `0`

This summary is read-only. It does not relax strict FY2026/R8 evidence rules and does not allow rejected rows into Excel.

## Defect Framing

- Generic algorithm/model failure supported: `False`
- Specific algorithm/rule defect supported: `False`
- Status: `pending_review`
- False-reject rows: `0`
- Needs-operator-review rows: `0`
- Correct-reject rows: `0`
- Reason: Review decisions are incomplete; below-gate yield must not be labeled as an algorithm/model defect yet.

## Decision Counts

| Decision | Rows |
| --- | ---: |
| `blank` | 53 |

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

- Fix the returned CSV errors before using this worksheet as RCA evidence.
- Keep old-year, unknown-year, non-target, school-mismatch, and low-confidence rows out of Excel.
- A completed RCA worksheet is not a release sign-off; the full owner return gate must still pass.

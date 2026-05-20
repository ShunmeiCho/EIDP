# v522 Same-Domain FY2026 Negative Probe

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
Source code under probe: `8a5437042e9db0ebff144afcfc0cf84706b1ff80`
Evidence source: v521 Mac limit-50 continuation canary

## Scope

This is a bounded negative probe against the v521/v522 publication-lag evidence.
It checks whether visible FY2025 target-form URLs have simple same-domain
FY2026/R8 equivalents that the crawler missed.

This is not broad SERP crawling and not an operator search pass. It only tests
candidate URLs derived from already observed `fiscal_year_mismatch:2025`
target-form rows.

## Evidence Inputs

- Evidence JSONL:
  `_temp/v521-mac-limit50-with-url-sources/data/output/target-year-discovery/20260520_031446-discovery-rejections.jsonl`
- Candidate workspace:
  `_temp/v522-same-domain-2026-probe/`

## Probe 1: Simple `2025 -> 2026`

Candidate generation:

```bash
jq -r 'select(.reason == "fiscal_year_mismatch:2025" and (.pdf_type == "target" or .pdf_type == "image_only")) | [.school_id, .pdf_url, (.pdf_url | gsub("2025"; "2026"))] | @tsv' \
  _temp/v521-mac-limit50-with-url-sources/data/output/target-year-discovery/20260520_031446-discovery-rejections.jsonl \
  | awk -F '\t' '$2 != $3' \
  | sort -u \
  > _temp/v522-same-domain-2026-probe/candidates.tsv
```

Result:

- Candidates: `38`
- HEAD probe status codes: `404 x 38`

## Probe 2: Expanded Short-Year / R7 Variants

Candidate generation added these same-URL transforms:

- `2025 -> 2026`
- trailing `25.pdf -> 26.pdf`
- `_25 -> _26`
- `-25 -> -26`
- `R7 -> R8`
- `r7 -> r8`

Result:

- Candidates: `47`
- HEAD probe status codes: `404 x 47`
- ranged GET probe status codes: `404 x 47`

## Conclusion

No same-domain FY2026/R8 target-form PDF was found from the bounded replacement
probe. The publication-lag rows therefore remain publication-lag evidence, not
strict FY2026 successes.

This does not change the v521/v522 release boundary: strict remains
`0/50 (0.0%)`, operator-reviewable remains `50/50 (100.0%)`, and
`ship_gate_status=below_gate`.

# False-Reject Review Summary

Archive: `logs/win-v547-86c848f-canary/stage6-evidence-20260621-054545.zip`
Release Forecast: `NOT_READY`
Strict Excel-ready yield: `12/50` (`24.0%`), required `60.0%`.

This is read-only triage guidance. It does not fill the worksheet, approve rejected rows, or allow any row into Excel.

## Suggested Decision Counts

| Suggested decision | Rows |
| --- | ---: |
| `correct_reject` | 24 |
| `needs_operator_review` | 29 |

## Suggested Decisions By Bucket

| Bucket | correct_reject | needs_operator_review | false_reject | blank |
| --- | ---: | ---: | ---: | ---: |
| `classified_non_target` | 4 | 8 | 0 | 0 |
| `fiscal_year_mismatch` | 12 | 0 | 0 | 0 |
| `pre_filtered_non_target_hint` | 6 | 6 | 0 | 0 |
| `site_entry_fetch_identity` | 0 | 11 | 0 | 0 |
| `target_fiscal_year_not_detected` | 2 | 4 | 0 | 0 |

## Priority Review Rows

Rows listed here are not suggested as obvious `correct_reject`. They still require owner/operator decision before they can support any RCA claim.

| Audit row ID | Bucket | Suggested decision | School ID | Reason | Review focus |
| --- | --- | --- | ---: | --- | --- |
| `86200c2ac49b387a` | `pre_filtered_non_target_hint` | `needs_operator_review` | 13 | `pre_filtered_non_target_hint` | Non-target rejection is not obviously safe from anchor/URL evidence; operator must inspect the official PDF/page before confirming correct_reject or false_reject. |
| `92587dfd41a0493f` | `pre_filtered_non_target_hint` | `needs_operator_review` | 14 | `pre_filtered_non_target_hint` | Non-target rejection is not obviously safe from anchor/URL evidence; operator must inspect the official PDF/page before confirming correct_reject or false_reject. |
| `faeea51e26705740` | `pre_filtered_non_target_hint` | `needs_operator_review` | 16 | `pre_filtered_non_target_hint` | Non-target rejection is not obviously safe from anchor/URL evidence; operator must inspect the official PDF/page before confirming correct_reject or false_reject. |
| `b7fab3b4be5d26ca` | `pre_filtered_non_target_hint` | `needs_operator_review` | 17 | `pre_filtered_non_target_hint` | Non-target rejection is not obviously safe from anchor/URL evidence; operator must inspect the official PDF/page before confirming correct_reject or false_reject. |
| `48c7bea6d0b411c5` | `pre_filtered_non_target_hint` | `needs_operator_review` | 19 | `pre_filtered_non_target_hint` | Non-target rejection is not obviously safe from anchor/URL evidence; operator must inspect the official PDF/page before confirming correct_reject or false_reject. |
| `d1dd4a4bfcb73eec` | `pre_filtered_non_target_hint` | `needs_operator_review` | 21 | `pre_filtered_non_target_hint` | Non-target rejection is not obviously safe from anchor/URL evidence; operator must inspect the official PDF/page before confirming correct_reject or false_reject. |
| `3a0f8397307c16d4` | `classified_non_target` | `needs_operator_review` | 11 | `classified_non_target` | Non-target rejection is not obviously safe from anchor/URL evidence; operator must inspect the official PDF/page before confirming correct_reject or false_reject. |
| `9e251721aa515c6b` | `classified_non_target` | `needs_operator_review` | 13 | `classified_non_target` | Non-target rejection is not obviously safe from anchor/URL evidence; operator must inspect the official PDF/page before confirming correct_reject or false_reject. |
| `f36afe0d6149df33` | `classified_non_target` | `needs_operator_review` | 16 | `classified_non_target` | Non-target rejection is not obviously safe from anchor/URL evidence; operator must inspect the official PDF/page before confirming correct_reject or false_reject. |
| `e06645c66c9ec7fa` | `classified_non_target` | `needs_operator_review` | 17 | `classified_non_target` | Non-target rejection is not obviously safe from anchor/URL evidence; operator must inspect the official PDF/page before confirming correct_reject or false_reject. |
| `b9cf312d643233eb` | `classified_non_target` | `needs_operator_review` | 18 | `classified_non_target` | Non-target rejection is not obviously safe from anchor/URL evidence; operator must inspect the official PDF/page before confirming correct_reject or false_reject. |
| `f6127fb4fac870ec` | `classified_non_target` | `needs_operator_review` | 20 | `classified_non_target` | Non-target rejection is not obviously safe from anchor/URL evidence; operator must inspect the official PDF/page before confirming correct_reject or false_reject. |
| `4dc3324e137772b2` | `classified_non_target` | `needs_operator_review` | 21 | `classified_non_target` | Non-target rejection is not obviously safe from anchor/URL evidence; operator must inspect the official PDF/page before confirming correct_reject or false_reject. |
| `52ea4a2b283e7bef` | `classified_non_target` | `needs_operator_review` | 27 | `classified_non_target` | Non-target rejection is not obviously safe from anchor/URL evidence; operator must inspect the official PDF/page before confirming correct_reject or false_reject. |
| `3df9d0a93752f3c8` | `target_fiscal_year_not_detected` | `needs_operator_review` | 1 | `target_fiscal_year_not_detected` | Target-form-like row lacks trusted target-year evidence; operator must confirm official FY evidence. |
| `780758ff3aec558a` | `target_fiscal_year_not_detected` | `needs_operator_review` | 2 | `target_fiscal_year_not_detected` | Target-form-like row lacks trusted target-year evidence; operator must confirm official FY evidence. |
| `a3873ee6a0eb300e` | `target_fiscal_year_not_detected` | `needs_operator_review` | 1 | `target_fiscal_year_not_detected` | Target-form-like row lacks trusted target-year evidence; operator must confirm official FY evidence. |
| `ad9beff98fd03c72` | `target_fiscal_year_not_detected` | `needs_operator_review` | 2 | `target_fiscal_year_not_detected` | Target-form-like row lacks trusted target-year evidence; operator must confirm official FY evidence. |
| `cff41b0714a9200e` | `site_entry_fetch_identity` | `needs_operator_review` | 4 | `no_candidates_found` | No valid candidate was found or fetch failed; inspect the official SiteEntry/disclosure page. |
| `bb4da083a3ef33f6` | `site_entry_fetch_identity` | `needs_operator_review` | 5 | `no_candidates_found` | No valid candidate was found or fetch failed; inspect the official SiteEntry/disclosure page. |
| `b44dd14a9cc4f4ea` | `site_entry_fetch_identity` | `needs_operator_review` | 6 | `no_candidates_found` | No valid candidate was found or fetch failed; inspect the official SiteEntry/disclosure page. |
| `5cd47a3627fcae17` | `site_entry_fetch_identity` | `needs_operator_review` | 7 | `no_candidates_found` | No valid candidate was found or fetch failed; inspect the official SiteEntry/disclosure page. |
| `3866fd28354a97e1` | `site_entry_fetch_identity` | `needs_operator_review` | 8 | `no_candidates_found` | No valid candidate was found or fetch failed; inspect the official SiteEntry/disclosure page. |
| `0d0bc1d1fdce2dd1` | `site_entry_fetch_identity` | `needs_operator_review` | 9 | `no_candidates_found` | No valid candidate was found or fetch failed; inspect the official SiteEntry/disclosure page. |
| `f5d47fcd2d8aca3e` | `site_entry_fetch_identity` | `needs_operator_review` | 10 | `no_candidates_found` | No valid candidate was found or fetch failed; inspect the official SiteEntry/disclosure page. |
| `ca15518d6c5a6647` | `site_entry_fetch_identity` | `needs_operator_review` | 11 | `no_candidates_found` | No valid candidate was found or fetch failed; inspect the official SiteEntry/disclosure page. |
| `54fd6f6418ad0d27` | `site_entry_fetch_identity` | `needs_operator_review` | 12 | `no_candidates_found` | No valid candidate was found or fetch failed; inspect the official SiteEntry/disclosure page. |
| `bf12a235cd7aa235` | `site_entry_fetch_identity` | `needs_operator_review` | 20 | `pdf_school_mismatch` | Target-like document has school-identity risk; confirm it belongs to the same institution. |
| `efbe9d08dc2cfba2` | `site_entry_fetch_identity` | `needs_operator_review` | 25 | `pdf_school_mismatch` | Target-like document has school-identity risk; confirm it belongs to the same institution. |

## Review Rules

- Fill only `decision`, `reviewer`, `reviewed_at`, and `notes` in the CSV worksheet.
- Mark `false_reject` only with official FY2026/R8 evidence.
- Keep old-year, unknown-year, non-target, school-mismatch, and low-confidence rows out of Excel.
- Release remains blocked until the returned worksheet validates with `review_status=complete` and `context_mismatch_count=0`.

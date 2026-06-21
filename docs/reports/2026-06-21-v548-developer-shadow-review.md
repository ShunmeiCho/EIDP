# v548 Developer Shadow Review

Release Forecast: `NOT_READY`

Source worksheet: `docs/reports/2026-06-21-v548-false-reject-review-sheet.csv`

This is a developer diagnostic shadow review over the same 53 v548 rejection rows. It is not owner/operator approval, not release evidence, not Excel-ready authorization, and not a replacement for the canonical worksheet return. It uses only the existing v548 Stage 6 evidence fields; it does not perform live official-page or PDF inspection.

## Summary

| Shadow decision | Rows |
| --- | ---: |
| `likely_correct_reject` | 24 |
| `likely_needs_operator_review` | 29 |
| `likely_false_reject` | 0 |

## Priority Counts

| Priority | Rows |
| --- | ---: |
| `high` | 15 |
| `medium` | 14 |
| `normal` | 24 |

## Diagnostic Lanes

| Diagnostic lane | Rows |
| --- | ---: |
| `non_target_classifier_or_prefilter_review` | 14 |
| `obvious_non_target_anchor_or_url` | 10 |
| `old_or_non_target_year_evidence` | 12 |
| `old_year_image_pdf` | 2 |
| `site_entry_identity_review` | 11 |
| `target_form_missing_trusted_year_evidence` | 4 |

## Shadow Decisions By Bucket

| Bucket | likely_correct_reject | likely_needs_operator_review | likely_false_reject |
| --- | ---: | ---: | ---: |
| `classified_non_target` | 4 | 8 | 0 |
| `fiscal_year_mismatch` | 12 | 0 | 0 |
| `pre_filtered_non_target_hint` | 6 | 6 | 0 |
| `site_entry_fetch_identity` | 0 | 11 | 0 |
| `target_fiscal_year_not_detected` | 2 | 4 | 0 |

## High-Priority Owner Review Rows

These rows have target-form/year or identity risk in the existing evidence packet. They should be reviewed before treating the below-gate rate as publication lag or correct rejection.

| Audit row ID | School ID | Bucket | Diagnostic lane | Page URL | PDF URL |
| --- | ---: | --- | --- | --- | --- |
| `cff41b0714a9200e` | 4 | `site_entry_fetch_identity` | `site_entry_identity_review` | <https://www.mode.ac.jp/tokyo> | <https://www.mode.ac.jp/tokyo> |
| `bb4da083a3ef33f6` | 5 | `site_entry_fetch_identity` | `site_entry_identity_review` | <https://www.mode.ac.jp/osaka> | <https://www.mode.ac.jp/osaka> |
| `b44dd14a9cc4f4ea` | 6 | `site_entry_fetch_identity` | `site_entry_identity_review` | <https://www.mode.ac.jp/nagoya> | <https://www.mode.ac.jp/nagoya> |
| `5cd47a3627fcae17` | 7 | `site_entry_fetch_identity` | `site_entry_identity_review` | <https://www.hal.ac.jp/tokyo> | <https://www.hal.ac.jp/tokyo> |
| `3866fd28354a97e1` | 8 | `site_entry_fetch_identity` | `site_entry_identity_review` | <https://www.hal.ac.jp/osaka> | <https://www.hal.ac.jp/osaka> |
| `0d0bc1d1fdce2dd1` | 9 | `site_entry_fetch_identity` | `site_entry_identity_review` | <https://www.hal.ac.jp/nagoya> | <https://www.hal.ac.jp/nagoya> |
| `f5d47fcd2d8aca3e` | 10 | `site_entry_fetch_identity` | `site_entry_identity_review` | <https://www.iko.ac.jp/tokyo> | <https://www.iko.ac.jp/tokyo> |
| `ca15518d6c5a6647` | 11 | `site_entry_fetch_identity` | `site_entry_identity_review` | <https://www.iko.ac.jp/osaka> | <https://www.iko.ac.jp/osaka> |
| `54fd6f6418ad0d27` | 12 | `site_entry_fetch_identity` | `site_entry_identity_review` | <https://www.iko.ac.jp/nagoya> | <https://www.iko.ac.jp/nagoya> |
| `bf12a235cd7aa235` | 20 | `site_entry_fetch_identity` | `site_entry_identity_review` | <https://www.sanko.ac.jp/disclosure/yokohama-med/> | <https://www.sanko.ac.jp/disclosure/yokohama-med/yoshiki2026.pdf> |
| `efbe9d08dc2cfba2` | 25 | `site_entry_fetch_identity` | `site_entry_identity_review` | <https://www.sanko.ac.jp/disclosure/fukuoka-med/> | <https://www.sanko.ac.jp/disclosure/fukuoka-med/docs/99158211b0011c77cfb13002f8106b4eb79443a6.pdf> |
| `3df9d0a93752f3c8` | 1 | `target_fiscal_year_not_detected` | `target_form_missing_trusted_year_evidence` | <https://www.neec.ac.jp/portal/public/mext-scholarship/> | <https://www.neec.ac.jp/assets/contents/documents/portal/syllabus/hachioji/portal_syllabus_hachioji_yoshiki.pdf> |
| `a3873ee6a0eb300e` | 1 | `target_fiscal_year_not_detected` | `target_form_missing_trusted_year_evidence` | <https://www.neec.ac.jp/portal/public/mext-scholarship/> | <https://www.neec.ac.jp/assets/contents/documents/portal/syllabus/kamata/portal_syllabus_kamata_yoshiki.pdf> |
| `780758ff3aec558a` | 2 | `target_fiscal_year_not_detected` | `target_form_missing_trusted_year_evidence` | <https://www.neec.ac.jp/portal/public/mext-scholarship/> | <https://www.neec.ac.jp/assets/contents/documents/portal/syllabus/hachioji/portal_syllabus_hachioji_yoshiki.pdf> |
| `ad9beff98fd03c72` | 2 | `target_fiscal_year_not_detected` | `target_form_missing_trusted_year_evidence` | <https://www.neec.ac.jp/portal/public/mext-scholarship/> | <https://www.neec.ac.jp/assets/contents/documents/portal/syllabus/kamata/portal_syllabus_kamata_yoshiki.pdf> |

## Release Use

- If owner review confirms any `false_reject`, stop the release path and fix the specific discovery/filter/year-evidence rule with a regression test and a new bounded Windows canary.
- If owner review confirms mostly `correct_reject`, prepare the publication-lag / OCR `RC_ONLY` owner decision path while keeping unconfirmed rows out of Excel.
- If owner review leaves many rows as `needs_operator_review`, improve the review/adjudication queue and evidence display; do not relax Excel-ready gates.

Developer shadow output may guide RCA prioritization only. It must not be submitted to `scripts/verify_stage6_return.py` as owner evidence.

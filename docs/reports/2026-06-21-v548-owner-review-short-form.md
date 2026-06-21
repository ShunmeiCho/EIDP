# v548 Owner Review Short Form

Release Forecast: `NOT_READY`

This packet freezes `v548` as the current owner review baseline. It is generated from `docs/reports/2026-06-21-v548-false-reject-review-sheet.csv` and does not supersede the canonical v548 worksheet unless a new canary changes the packet.

## Files

- CSV short form: `docs/reports/2026-06-21-v548-owner-review-short-form.csv`
- XLSX short form with owner-decision dropdowns: `docs/reports/2026-06-21-v548-owner-review-short-form.xlsx`
- Canonical worksheet for returned verifier input: `docs/reports/2026-06-21-v548-false-reject-review-sheet.csv`

## Scope

This short form is owner evidence intake only. It does not approve rejected rows, does not make rejected rows Excel-ready, does not replace Stage 6 return verification, and does not change the v548 packaged runtime.

The owner should fill only `owner_decision` and `owner_notes` in the short form. Allowed owner decisions are `correct_reject`, `false_reject`, and `needs_operator_review`. After return, the developer maps completed decisions back to the canonical worksheet and validates it with `scripts/verify_stage6_return.py`.

The source worksheet does not include school names. The repo-local `data/eidp.sqlite3` is currently empty, so the short form uses trusted `school_id` labels rather than guessing school names from older samples.

## Mapping Back To The Canonical Worksheet

After the owner returns the short form, map it back to a canonical worksheet copy:

```bash
uv run python scripts/apply_owner_short_form_return.py \
  --canonical-review-csv docs/reports/2026-06-21-v548-false-reject-review-sheet.csv \
  --owner-short-form-csv <returned-owner-short-form.csv> \
  --reviewer "<owner-or-operator-id>" \
  --reviewed-at "<ISO timestamp>" \
  --require-complete \
  --output <returned-canonical-false-reject-review-sheet.csv> \
  --json
```

The mapper requires exact `audit_row_id` coverage and unchanged short-form
context (`school_id`, URLs, rejection bucket, and system suggestion). It only
prepares the returned canonical CSV. It does not write audit logs, approve
release, or allow rejected rows into Excel. After mapping, validate
`<returned-canonical-false-reject-review-sheet.csv>` with
`scripts/build_false_reject_audit.py --validate-review-csv --require-decisions`
and then run `scripts/verify_stage6_return.py` with the same returned canonical
CSV.

## Pack Counts

| Pack | Rows |
| --- | ---: |
| Pack A - suggested `correct_reject` | 24 |
| Pack B - suggested `needs_operator_review` | 29 |
| Pack C - suspected `false_reject` | 0 |
| Pack Z - no system suggestion | 0 |

## Suggested Decision Counts

| Suggested decision | Rows |
| --- | ---: |
| `correct_reject` | 24 |
| `needs_operator_review` | 29 |
| `false_reject` | 0 |
| `blank` | 0 |

## Suggested Decisions By Bucket

| Bucket | correct_reject | needs_operator_review | false_reject | blank |
| --- | ---: | ---: | ---: | ---: |
| `classified_non_target` | 4 | 8 | 0 | 0 |
| `fiscal_year_mismatch` | 12 | 0 | 0 | 0 |
| `pre_filtered_non_target_hint` | 6 | 6 | 0 | 0 |
| `site_entry_fetch_identity` | 0 | 11 | 0 | 0 |
| `target_fiscal_year_not_detected` | 2 | 4 | 0 | 0 |

## Release Boundary

Do not add more P1 hardening unless it directly unblocks owner return validation or Windows canary execution. The next release-unblocking action is owner/operator decision return, diagnostic developer shadow review, owner publication-lag/OCR decision brief, or a concrete rule fix for a confirmed `false_reject` row.

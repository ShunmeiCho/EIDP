# EIDP v541 Release Summary

Date: 2026-06-21
Release ID: v541

This one-page summary is the owner-facing release summary for the v541
handoff. It is short by design. The detailed engineering checklist remains in
the release evidence bundle and Stage 6 verifier output.

## Decision

Current release conclusion: `NOT_READY`

v541 is ready for side-by-side review and owner decision routing. It is not
approved for v1.0 GA, active Scheduled Task promotion, or final workbook
operation.

## Package

| Field | Value |
| --- | --- |
| Package | `dist/eidp-windows-v541.zip` |
| Windows staging path | `C:\EIDP-staging\eidp-windows-v541.zip` |
| SHA256 | `2ffb25884e15b9e2937f43bab7a8f5866d9434bc9f29f8067dbc1760397fa46f` |
| Source commit | `e62d074081e60428957a2f405c3a917bbceb31a0` |
| Package branch | `main` |
| Package dirty state | `false` |
| Side-by-side root | `%USERPROFILE%\EIDP-v541-e62d074-env0` |
| Active root to preserve | `%USERPROFILE%\EIDP-v527-69fe81f-env0` |

## Scope

- v1 scope is the vocational-school-first Windows single-operator workflow.
- v1 is a rolling fiscal-year operation, not a one-year PDF scrape.
- University production workflow, multi-user operation, PostgreSQL, cloud
  deployment, and complex frontend work remain v2+ scope.
- HTML demo prototypes, PPTX exports, and `support.js` are not production UI.

## Evidence Available

- GitHub CI for v541 evidence-docs commit `9981397`: success,
  run `27876116316`.
- GitHub CI for packaged source commit `e62d074`: success,
  run `27874800210`.
- Windows side-by-side v541 setup, bounded weekly canary, after-weekly
  validation, and Stage 6 evidence verification completed.
- Stage 6 verification result:
  `logs/win-v541-e62d074-canary/stage6-evidence-verify-20260621-003707.json`
  reports `ok=true`.
- Consolidated evidence report:
  `docs/reports/2026-06-21-v541-owner-signoff-verifier-windows-canary.md`.

## Current Metrics

| Metric | Current v541 bounded canary result |
| --- | --- |
| Strict FY2026/R8 Excel-ready yield | `12/50 (24.0%)` |
| Operator-reviewable yield | `47/50 (94.0%)` |
| Ship gate status | `below_gate` |

The `12/50` result is a bounded target-missing cohort canary. It is not
whole-database release readiness and does not satisfy the v1 `>= 60%` strict
Excel-ready gate.

## P0 Blockers

- Strict FY2026/R8 Excel-ready yield is below the v1 gate.
- Owner real Windows cycle and signed return evidence are missing.
- `publication_lag` exception is not approved.
- OCR scope is not explicitly selected for v1 release.

## Owner Decisions Needed

1. Keep v541 as `NOT_READY`, or choose the documented Route A / Route B path.
2. If Route A is chosen, approve the `publication_lag` RC-only exception.
3. Select OCR scope: core text-PDF only, or OCR add-on required.
4. Run the owner real Windows cycle and return signed evidence before any
   release promotion.

## Safety Rules

- Unconfirmed rows must not enter final Excel output.
- Prior-year PDFs must not be counted as current-year success.
- School mismatches, non-target PDFs, low-confidence rows, unresolved program
  changes, and unknown-year documents must remain excluded or review-blocked.
- v541 side-by-side evidence must not be treated as owner real-cycle sign-off.
- The active v527 Scheduled Task lane must remain unchanged unless an explicit
  promotion decision is made.

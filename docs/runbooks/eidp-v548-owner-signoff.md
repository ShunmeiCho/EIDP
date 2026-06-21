# EIDP v548 Owner Sign-off

Date: 2026-06-21
Release ID: v548

The owner signs this short form, not the engineering checklist. The checklist,
CI logs, Windows canary, Stage 6 evidence bundle, and release status remain
the sign-off basis.

Read first:

- `docs/runbooks/eidp-v548-release-summary.md`
- `docs/reports/current-release-status.md`
- `docs/release/owner-decisions/publication-lag.md`
- `docs/release/owner-decisions/ocr-scope.md`
- `docs/release/v1-known-limitations.md`

## Fixed Package Identity

| Field | Value |
| --- | --- |
| Package | `dist/eidp-windows-v548.zip` |
| SHA256 | `488d9e90a5dba99ef3a3eba3489832c6a878a8fa376bb1dd4808168e0975a67c` |
| Source commit | `c1a96903ed10f1cc9c48d1a6912061ba0aaf86be` |
| Current release conclusion | `NOT_READY` |

## Release Decision

Choose one:

- [ ] `READY`: formal v1.0 release
- [ ] `RC_ONLY`: limited trial / release candidate
- [ ] `NOT_READY`: do not release

For current v548 evidence, the supported decision is `NOT_READY`.
`publication_lag` approval can support at most `RC_ONLY` after owner real-cycle
return evidence and verifier success. It does not make v548 `READY`.

## Scope Acknowledgement

- [ ] v1 is the vocational-school-first Windows single-operator workflow.
- [ ] University production workflow is outside v1.
- [ ] HTML demos, PPTX exports, and UI prototypes are not the production
      system.

## Data Safety Acknowledgement

- [ ] Excel output contains only Excel-ready data.
- [ ] Unknown-year, old-year, school-mismatch, non-target, low-confidence, and
      unresolved program-change data remain excluded or review-blocked.
- [ ] Image-PDF/OCR rows do not enter final Excel unless the selected OCR scope
      and review evidence allow it.

## Known Limitations Acknowledgement

- [ ] Current strict FY2026/R8 Excel-ready yield is below the v1 gate.
- [ ] The `publication_lag` exception is not approved unless separately signed.
- [ ] OCR scope is not selected unless separately signed.
- [ ] Owner real Windows cycle evidence is not complete until the returned
      Stage 6 packet passes verification.

## Sign-off

Owner name:

Date:

Decision:

Notes:

Signature:

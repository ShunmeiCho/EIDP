# OCR Scope Owner Decision Brief

Status: decision required
Updated: 2026-06-21

This brief decides whether v1 requires OCR automation as a release condition or
whether v1 ships the text-PDF workflow while image PDFs enter OCR/manual review.

It is not approval by itself. The selected scope must still be reflected in the
release summary, known limitations, owner sign-off, and Stage 6 return
verification.

## What The Owner Chooses

Choose one:

- `CORE_TEXT_PDF_ONLY`: v1 does not require automatic OCR success for release.
  Text PDFs are in scope; image PDFs enter OCR/manual review queues.
- `OCR_ADDON_REQUIRED`: v1 release requires validated OCR add-on evidence on
  Windows before approval.
- `DEFER`: no release decision yet.

## Current v548 Evidence Snapshot

Release Forecast: `NOT_READY`

The current owner review baseline is v548:

- package: `dist/eidp-windows-v548.zip`
- package SHA256:
  `488d9e90a5dba99ef3a3eba3489832c6a878a8fa376bb1dd4808168e0975a67c`
- package/source commit:
  `c1a96903ed10f1cc9c48d1a6912061ba0aaf86be`
- current Windows canary:
  `docs/reports/2026-06-21-v548-windows-canary.md`

The v548 bounded Windows canary remains below gate and includes
`image_pending=3`. These rows are not Excel-ready. They must either stay in the
OCR/manual review queue or be proven by a current OCR add-on/runtime evidence
packet before approval if OCR is selected as a release requirement.

Owner decision impact from the current v548 evidence:

| Owner choice | Release impact now |
| --- | --- |
| `CORE_TEXT_PDF_ONLY` | Can support a text-PDF v1 scope only if image-only/OCR rows remain visible as review work and unreviewed OCR rows stay out of final Excel. It does not make v548 `READY` by itself. |
| `OCR_ADDON_REQUIRED` | Keeps release `NOT_READY` until the OCR add-on SHA256 and current Windows OCR runtime proof are attached and accepted. |
| `DEFER` | Keeps release `NOT_READY`; no OCR release-scope decision exists. |

## If `CORE_TEXT_PDF_ONLY` Is Chosen

This means:

- text-PDF discovery, extraction, review, audit, and Excel-ready gates remain
  in scope
- image-only PDFs do not block text-PDF release
- image-only PDFs must be visible as OCR/manual-review work
- OCR output is not an automatic trust signal
- unreviewed OCR rows must not enter final Excel output
- the limitation must be shown in the release summary and owner sign-off

This does not mean:

- image PDFs are ignored
- low-confidence OCR data can enter Excel
- OCR evidence can be omitted if the package advertises OCR support
- Windows validation can be skipped

## If `OCR_ADDON_REQUIRED` Is Chosen

This means:

- the OCR add-on ZIP, SHA256, and Windows runtime proof are required
- image-write or image-PDF proof must be included in the evidence bundle
- `scripts/verify_stage6_return.py` must accept the selected OCR scope
- missing OCR runtime proof remains a release blocker

## Required Evidence Before Use

Before this decision can affect a release, the release packet must reference:

- `docs/reports/current-release-status.md`
- selected OCR scope value in the owner/operator return
- latest CI result
- latest Windows canary or real-PC evidence
- OCR add-on SHA256 and runtime proof, if `OCR_ADDON_REQUIRED`
- review/audit evidence for OCR/manual-review rows, if present

## Release Conclusion

- With no OCR scope decision: `NOT_READY`.
- With `CORE_TEXT_PDF_ONLY`: release may proceed only if image PDFs are routed to
  OCR/manual review and unconfirmed rows stay out of Excel.
- With `OCR_ADDON_REQUIRED`: release may proceed only after current Windows OCR
  proof is present.

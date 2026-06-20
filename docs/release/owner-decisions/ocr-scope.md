# OCR Scope Owner Decision Brief

Status: decision required

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

# Linux/Web OCR Scope Decision

Status: pending acceptance evidence
Updated: 2026-07-11

Image-only PDFs are routed to an explicit manual/OCR exception lane. They are
never silently treated as extracted or Excel-ready.

The release decision must choose and prove one of:

- `CORE_TEXT_PDF_ONLY`: text PDFs are v1 core; image PDFs remain visible manual
  tasks and are excluded from final output until manually resolved.
- `OCR_REQUIRED`: the Venus runtime includes a tested OCR engine and image-lane
  E2E evidence.
- `DEFER_RELEASE`: do not release until the image-PDF population and required
  operator workload are measured.

Any selected option must document CPU/RAM/runtime cost, language data, failure
routing, review identity, and backup/retention behavior. OCR installation and
models must remain inside `/home/junming/EIDP` unless separately authorized.

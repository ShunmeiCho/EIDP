# v1 Known Limitations

Updated: 2026-06-20

This file records current v1 limitations so they are not accidentally presented
as completed scope. It does not weaken the release gates.

## Release-State Limitations

- The current release conclusion is `NOT_READY`, not `READY`.
- `RC_ONLY` is acceptable for internal trial or demonstration, but it is not GA.
- Mac/Linux tests and package verification do not prove Windows operator
  release readiness.
- Windows side-by-side smoke evidence is runtime evidence, not owner/operator
  sign-off.
- A `publication_lag` release path requires explicit owner approval, mature-year
  proof, and a verified owner return. The agent must not approve it.
- Owner decisions are tracked as short briefs under
  `docs/release/owner-decisions/`, but those briefs do not approve release by
  themselves.

## Product-Scope Limitations

- v1 targets vocational schools (`専門学校`) first.
- University rows in the MEXT index prove source availability, not university
  target-document discovery, extraction, review, or Excel output readiness.
- Multi-operator review, PostgreSQL, cloud deployment, FastAPI, and React/Next.js
  frontend work belong to post-v1 release trains.
- The HTML operations-console demo is a design reference, not production UI.

## Data-Quality Limitations

- Broad search such as `school name + PDF` is not a production PDF acquisition
  source.
- Prior-year target forms and year-unknown target forms remain review or
  publication-lag evidence unless the target year is explicitly proven.
- OCR output is not an automatic trust signal; it requires confidence and review
  handling.
- The v1 OCR release scope must be explicitly selected before approval:
  text-PDF-only with image PDFs routed to OCR/manual review, or OCR add-on
  required with current Windows runtime proof.
- Low-confidence, mismatched-school, non-target, old-year, and unresolved
  program-change rows must not silently enter final Excel output.

## Operational Limitations

- Generated ZIPs, logs, and release evidence must stay on the external SSD
  symlinked locations when available; do not rebuild large artifacts onto the
  internal SSD.
- Old PPTX or demo exports containing labels such as `DB転記済`,
  `要確認キュー`, or `Excelプレビュー` must not be used as the current UI
  baseline.
- Future post-v1 tasks must be assigned to a release train in
  `docs/roadmap/post-v1-roadmap.md` and
  `docs/roadmap/post-v1-decision-board.md` before implementation.

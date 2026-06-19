# Release Gates

These gates define what can be called a v1 Windows operator release. They do
not prevent RC, demo, or internal checkpoint builds, but they do prevent GA
claims.

## v1 Release Scope

v1 release validation is scoped to:

- vocational schools (`専門学校`)
- one Windows operator
- local SQLite
- Streamlit UI
- official index and official disclosure entry discovery
- target application PDF verification
- deterministic extraction, OCR fallback, and manual review
- Excel-ready gating and workbook export
- audit trail for manual decisions

University production support is v2+ unless a separate university gold set,
parser workflow, and operator validation gate are added.

## Required Evidence

A v1 release candidate must include evidence for:

- Mac/Linux unit and quality gates
- Windows ZIP build and distribution verification
- Windows VM offline validation
- real-PC operator validation when required by the runbook
- OCR add-on validation if OCR support is advertised
- SQLite file locking behavior
- Excel output and file-lock handling
- diagnostics bundle generation
- target-year discovery yield
- publication-lag decision
- owner/operator sign-off

Mac-side tests prove business logic and package shape only. They do not prove
Windows deployability.

## Target-Year Yield

Release status must distinguish:

- strict target-year Excel-ready count
- operator-reviewable count
- publication-lag cases
- OCR/manual-entry cases
- non-target and old-year exclusions

Do not claim GA if target-year strict yield is below the active release gate or
if publication-lag exceptions are unresolved.

Acceptable labels while gates are open:

- release candidate
- demo
- publication-lag-aware operator tool
- v1-scoped vocational-school release candidate

Forbidden labels while gates are open:

- GA
- 2400-school full coverage
- FY2026/R8 automatic collection stable
- university production ready

## Excel Export Gate

Workbook export must be blocked or visibly downgraded when:

- target fiscal year is unconfirmed
- PDF identity is mismatched
- document kind is not target application form
- extraction confidence is below the auto-accept threshold
- OCR output lacks review where review is required
- program reconciliation is unresolved
- manual audit evidence is missing
- workbook template is missing
- output path is not writable
- an Excel file lock prevents safe output

Partial export behavior must show which institutions were excluded and why.

## Parser And Discovery Changes

Parser or discovery changes that affect business acceptance require:

- regression tests for the new acceptance or rejection behavior
- negative tests for near-miss PDFs or URLs
- evidence that non-target and old-year documents remain excluded
- school-identity mismatch coverage when relevant
- no bypass of URL safety or crawl throttling

PDF parser main logic should not change without fixtures or gold samples that
cover target PDFs, prior-year PDFs, non-target PDFs, image PDFs, school mismatch,
year-unknown cases, and program-change cases when applicable.

## PR Checklist

Use this checklist for non-trivial PRs:

- [ ] Does this affect official index ingestion or PDF discovery?
- [ ] Does this affect fiscal-year judgment?
- [ ] Does this affect document-kind classification?
- [ ] Does this affect school identity matching?
- [ ] Does this affect extraction confidence or OCR behavior?
- [ ] Does this affect program reconciliation?
- [ ] Does this affect Excel-ready status or workbook export?
- [ ] Does this add or change workflow status names?
- [ ] Does this record audit events for manual business decisions?
- [ ] Does this preserve append-only revision contracts?
- [ ] Does this include regression tests or gold samples where required?
- [ ] Does this need Windows VM or real-PC validation?
- [ ] Does this keep v1 scoped to vocational schools?
- [ ] Does this keep demo UI separate from production UI?

## Documentation Consistency

README, architecture docs, UI prototype docs, release reports, and stakeholder
materials must use the same scope and release language.

Do not let one document claim v1 supports universities or GA while another
states the release is still gated on vocational-school target-year yield,
publication lag, Windows validation, or owner sign-off.

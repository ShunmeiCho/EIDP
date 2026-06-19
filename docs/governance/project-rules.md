# EIDP Project Rules

EIDP changes must serve an official-evidence-driven, fiscal-year-explicit,
operator-reviewed, Excel-traceable disclosure pipeline.

This document is a governance baseline, not a style guide. It prevents the
project from drifting from a production data workflow into a crawler, manual
patch set, or demo UI.

## Scope

v1 is scoped to vocational schools (`専門学校`) and the one-operator Windows
workflow. University (`大学`) data and roadmap material may remain in the
repository, but production university parsers, gold sets, and operator flows are
v2+ work.

Do not add "700 universities production-ready" to a v1 release gate or public
claim.

## Product Boundary

EIDP is not a generic crawler, search tool, bulk downloader, or AI-agent demo.
Every production feature must fit this workflow:

1. Resolve an official disclosure entry.
2. Discover a target application PDF.
3. Verify the target fiscal year.
4. Extract via deterministic PDF parsing, OCR fallback, or manual entry.
5. Reconcile programs and annual metrics.
6. Route exceptions to human review.
7. Mark rows Excel-ready only after gates pass.
8. Export workbooks with an audit trail.

Any URL candidate must answer whether it is official, belongs to the target
institution, belongs to the target fiscal year, is a target form, is traceable,
and can be reproduced.

## Source Trust

Production discovery must expand from high-trust official sources:

| Tier | Source | Auto-use policy |
| --- | --- | --- |
| T0 | MEXT official information | May seed production evidence |
| T1 | Prefecture or confirming-authority index | May seed production evidence |
| T2 | Other official authority or competent department | May seed production evidence |
| T3 | School or operating-body official disclosure page | May seed production evidence |
| T4 | Operator-provided official URL | Review and audit required |
| T5 | Search-engine candidate | Review-only; never direct-write |

Search results from "school name + PDF" must never write directly to
`school_site`, `document`, extracted metrics, or Excel outputs.

Government index pages and third-party directories may be evidence or source
artifacts. They must not be registered as the school or operating-body
disclosure entry used by the production PDF crawler.

## Fiscal-Year Evidence

Target fiscal year must be evidence-backed. Download time is not fiscal-year
evidence.

Strong evidence:

- PDF body explicitly says `令和8年度`, `2026年度`, or equivalent target-year text.

Medium evidence:

- URL or filename contains the target year, and the PDF is otherwise confirmed
  as the target application form.

Weak evidence:

- Prior-year comparison is plausible, but the PDF body does not identify the
  year.

Never auto-confirm:

- A prior-year PDF as the current fiscal year because the download happened
  this year.
- A `令和7年度` PDF with unchanged numbers as `令和8年度`.
- A year-unknown PDF into `target_fiscal_year` without an explicit review state.

## Document Classification

Only target application forms enter the business extraction chain.

Required document kinds include:

- `target_application_form`
- `prior_year_target_form`
- `target_application_attachment`
- `support_recipient_only`
- `non_target_disclosure`
- `school_evaluation`
- `vocational_practice_form`
- `admission_document`
- `unknown_pdf`

Non-target PDFs, old-year PDFs, school evaluation PDFs, vocational-practice
course documents, admission documents, and support-only PDFs must not feed the
student-count workbook chain.

## Identity And Confidence

School identity mismatch blocks ingestion. This is especially important for
same-corporation sibling schools, group disclosure pages, renamed schools, old
names, and PDFs whose filenames omit the school name.

Low-confidence data must not enter final Excel output. OCR is a fallback method,
not a primary trust signal. OCR results must record extraction method,
confidence, source page evidence, and review status.

## Program Reconciliation

Program changes require formal reconciliation. Do not overwrite or merge annual
metrics using only a program-name string match.

Review is required for:

- new programs
- discontinued programs
- renames
- merges
- splits
- course-length changes
- day/night changes
- same-name different programs

Each accepted change must produce a review task, operator decision, audit event,
and mapping evidence.

## Data Writes And Audit

Business tables that carry annual metrics or status history must preserve the
append-only revision contract. Do not silently overwrite historical facts.

Correct pattern:

1. Mark the previous current row non-current.
2. Insert a new revision.
3. Write the operator or system audit event.

`manual_action_log` is the authoritative audit table. JSONL files are outbox
projections and diagnostics, not the source of truth.

Any manual action that changes business output must record an audit event:

- manual URL addition
- bulk URL import
- target/non-target PDF decision
- fiscal-year override
- manual metrics entry
- OCR confirmation
- low-confidence acceptance
- program-change decision
- Excel preview or export
- settings change

## Excel Gate

Excel is the deliverable. Workbook export must be guarded by an Excel-ready
gate, not by a "PDF found" or "DB written" flag.

Excel-ready requires:

- target fiscal year confirmed
- institution identity confirmed
- target document type confirmed
- extraction confidence gate passed or operator-confirmed
- program changes resolved
- non-target, old-year, and publication-lag cases excluded with reason
- audit evidence complete

The export UI must show which institutions are included, which are excluded, why
they are excluded, and which review tasks still block output.

## UI And Status Names

Operator UI must use business language, not implementation language.

Avoid new production UI labels such as:

- `DB転記`
- `スキップ`
- `待機`
- `要確認キュー`
- `Excelプレビュー`
- `年度判定・修正`

Prefer labels such as:

- `Excel出力可`
- `公開待ち`
- `人の確認が必要`
- `対象年度確認`
- `Excel出力`
- `確認して保存`
- `対象外として記録`

All pages should converge on the same three fields:

- `current_lane`
- `blocking_reason`
- `next_action`

Do not let pages invent separate strings for the same workflow state.

## Security And Crawl Safety

All URL requests must pass safety checks. Do not request localhost, loopback,
metadata, private, link-local, unsupported schemes, or URLs without bounded
timeouts.

Crawling must be throttled and evidence-producing. Failures must record the URL,
status or exception, and reason category such as no candidates, non-target
candidates only, publication lag, timeout, TLS failure, or blocked request.

Do not trade crawl politeness and reproducibility for short-term hit rate.

## Hard Red Lines

- Do not put university production support into the v1 release gate.
- Do not auto-ingest "school name + PDF" search results.
- Do not register third-party directories or government index pages as school
  disclosure entries.
- Do not infer fiscal year from download date.
- Do not confirm prior-year unchanged PDFs as the target year.
- Do not write non-target PDFs into business metrics.
- Do not write a mismatched school's PDF into the target school.
- Do not let low-confidence data enter final Excel.
- Do not overwrite append-only history.
- Do not bypass `manual_action_log` for manual decisions.
- Do not export unconfirmed data into shared workbooks.
- Do not use demo HTML or `support.js` as production UI code.
- Do not let UI pages invent raw workflow status names.
- Do not rewrite the stack only for "modernization".
- Do not bypass URL safety or crawl throttling.
- Do not release a Windows operator ZIP based only on Mac/Linux tests.
- Do not claim GA while target-year yield or publication-lag gates are open.
- Do not change parser main logic without regression fixtures or gold samples.
- Do not let README, architecture, UI prototype, and release status contradict
  each other.

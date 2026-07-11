# Domain Naming Deep Review

Date: 2026-06-19

Scope: review the proposed naming architecture, source trust boundary, UI
information architecture, and Agent-Reach positioning against the current EIDP
codebase.

## Findings

| Proposal | Review result | Reason / adjustment |
| --- | --- | --- |
| Naming is architecture, not cosmetic cleanup. | Confirmed | Current code stores business-critical state in legacy strings across ORM models, pipeline rebuild logic, and Streamlit labels. |
| Prefer business object plus state machine over technical action names. | Confirmed | `prefecture_aggregator`, `url_discovery`, `school_website_crawl`, and `pdf/extractor.py` describe implementation phases more than durable domain objects. |
| Establish a controlled domain vocabulary. | Confirmed | Added `docs/domain-vocabulary.md`; new code should route document kinds, review tasks, statuses, and trust tiers through `src/eidp/domain/`. |
| Use `Institution` instead of adding new `School` concepts. | Confirmed with compatibility boundary | Existing DB tables and ORM classes remain `School` for release safety; new domain APIs and UI copy should move toward `Institution`. |
| Prefer `Program` over `Department`. | Confirmed with compatibility boundary | Existing `Department` / `DepartmentYearly` tables remain. New copy and adapters should use `Program` / `ProgramAnnualMetrics`. |
| Rename `prefecture_aggregator` concept to `AuthorityIndex`. | Confirmed for domain language | Module rename is deferred. The current module remains the primary official-index implementation and should be wrapped before any path move. |
| PDF acquisition must expand from official indexes, not school-name hard search. | Confirmed | Search-derived evidence is now documented as T4 candidate evidence with `auto_accept_allowed=false`. |
| Do not treat every PDF as the same kind of document. | Confirmed | Added a controlled `DocumentKind` taxonomy for target forms, attachments, support-only files, old-year target forms, school evaluation, admission documents, and unknown PDFs. |
| Separate machine status, UI label, next action, and blocking reason. | Confirmed | Added `docs/status-taxonomy.md` and domain status enums. Current legacy values are mapped instead of renamed in-place. |
| UI should be an operator workbench, not a feature list. | Confirmed | Added `docs/ui-information-architecture.md`; safe label updates can land first while page ids remain compatible. |
| Agent-Reach should not enter the production core. | Confirmed | Added `docs/tools/agent-reach-rca.md`; Agent-Reach is T4 external research assistance only. |
| Agent-Reach can support developer/admin RCA. | Confirmed | It may produce candidate evidence, but must not write production business tables. |
| Add tests for registered labels and trust policies. | Confirmed | Added domain taxonomy tests to keep new enum values from shipping without operator labels or next actions. |
| Use the operations-console demo as a UI blueprint. | Confirmed with boundary | It remains a design reference only; see `docs/design/operations-console-demo/README.md`. |
| Rename database tables now. | Deferred | Table rename belongs after vocabulary, adapters, UI copy, tests, and release evidence stabilize. |
| Move modules into the proposed 9-layer package tree now. | Deferred | Large path moves would create avoidable regression risk on the release branch. Compatibility wrappers should come first. |

## Current Code Evidence

- `src/eidp/db/models.py` still exposes `School`, `SchoolSite`, `Document`,
  `Department`, `DepartmentYearly`, `SupportRecipient`, and `ReviewItem`.
- `src/eidp/pipeline/school_fiscal_year_status.py` computes legacy values such
  as `no_url`, `pref_url`, `confirmed_target`, `target_year_unverified`,
  `ocr_pending`, and `parse_failed`.
- `src/eidp/review/app.py` still uses feature-list navigation labels such as
  `学校別タスク`, `PDF確認・手入力`, and `Excel プレビュー`.
- `src/eidp/scraper/prefecture_aggregator.py` is the real official-index
  ingestion implementation today, so it should be wrapped before being moved.

## Decision

Proceed in phases:

1. Freeze vocabulary and status taxonomy.
2. Add controlled enums, Japanese labels, next actions, and source trust policy.
3. Update operator labels while keeping existing page ids and DB columns.
4. Add adapters for `Institution`, `SiteEntry`, `TargetDocument`, `Program`, and
   `WorkbookExport`.
5. Wrap and then move official-index modules.
6. Consider database table rename only after release-safety evidence is stable.

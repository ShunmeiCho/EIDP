# Post-v1 Roadmap

This roadmap defines what happens after v1, so follow-up work does not pollute
the current release path. It is a release train, not a loose backlog.

## v1.0 GA

Goal: release a vocational-school-first Windows single-operator tool.

Must satisfy:

- Windows setup, start, weekly run, and diagnose are validated.
- PDF discovery runs from official sources and official disclosure entries.
- dangerous fiscal-year interactions are blocked.
- PDF/OCR/manual-entry chain is usable.
- Excel-ready gate is active.
- audit log covers key manual actions.
- release evidence bundle exists.
- owner/operator sign-off is complete.

Not included:

- university production workflow
- multi-operator support
- PostgreSQL
- React production UI
- complete school-detail evidence-chain product
- complete official-index management UI

## v1.0.x Patch

Goal: fix issues found immediately after release without expanding scope.

Allowed work:

- operator feedback fixes
- blocker bug fixes
- UI wording drift
- diagnostics improvements
- Windows path issues
- Excel file-lock messages
- OCR add-on detection issues
- log readability
- stale PPTX/HTML/reference cleanup

Forbidden work:

- university support
- React rewrite
- multi-operator workflow
- PostgreSQL migration
- large new pages
- broad architecture changes

## v1.1 Hardening

Goal: move v1 from runnable to maintainable.

Focus:

- formalize `current_lane`, `blocking_reason`, and `next_action`
- converge raw workflow strings into enums or constants
- centralize Japanese UI labels
- harden Excel-ready gates
- automate release-gate checks
- expand audit coverage
- standardize failure and RCA buckets
- verify demo artifacts never enter production packaging

## v1.2 Source Reliability

Goal: turn official-index parsing into a maintainable data asset.

Focus:

- `authority_index_source` configuration or table
- `authority_index_artifact` cache and content hash
- `authority_index_entry` normalization
- source URL, fetched time, parser name, and parser version tracking
- prefecture source registry
- parse-result diff
- unmatched-school review
- index update diagnostics

## v1.3 Extraction Quality

Goal: reduce manual review by improving extraction and reconciliation quality.

Focus:

- target PDF gold set
- non-target PDF regression set
- image/OCR PDF set
- program-change samples
- school-mismatch tests
- R7/R8 fiscal-year misclassification tests
- new/discontinued/renamed/merged/split program review flow
- confidence calibration

## v1.5 Operator Console

Goal: rebuild the production Streamlit UI into a clearer operations console,
using the HTML demo as a contract rather than runtime code.

Focus:

- dashboard ViewModel
- school queue ViewModel
- PDF review ViewModel
- fiscal-year review ViewModel
- Excel export ViewModel
- `labels_ja.py`
- status pills and reusable components
- componentized Streamlit pages

Required boundary:

```text
HTML demo -> UI contract -> Streamlit implementation
```

Forbidden shortcut:

```text
HTML demo -> iframe -> production
```

## v2.0 University Expansion

Goal: expand to approximately 700 universities after the vocational-school
pipeline is stable.

Entry conditions:

- vocational-school v1 has run through a stable cycle
- source registry is maintainable
- PDF/OCR gold-set method is mature
- Excel-ready gate is stable
- program reconciliation is usable
- university sample gold set exists

Focus:

- university disclosure-page research
- university PDF/HTML gold set
- university parser fixtures
- university field mapping
- university Excel output-scope decision
- university UI label extensions
- pilot prefecture or sample run

## v2.x Multi-User / Cloud

Only start when there is real demand for:

- multiple operators
- remote review
- role-based permissions
- central backup
- PostgreSQL
- FastAPI backend
- React or Next.js frontend
- PDF object storage
- queue workers

Do not build v2.x platform infrastructure just to make the architecture feel
more advanced.

## Classification Rule

After v1 completion, do not start arbitrary next tasks. Every post-v1 task must
be assigned to one of:

- `v1.0.x patch`
- `v1.1 hardening`
- `v1.2 source reliability`
- `v1.3 extraction quality`
- `v1.5 operator console`
- `v2.0 university expansion`
- `v2.x multi-user/cloud`
- `research`

If a task cannot be assigned, put it in `research` and do not implement it until
its release train is explicit.

## Priority Order

Post-v1 work should advance in this order unless an owner-approved incident or
release decision changes priority:

1. `v1.0.x patch`: keep the just-released operator build usable.
2. `v1.1 hardening`: strengthen status machines, audit, Excel gates, and release
   gates.
3. `v1.2 source reliability`: turn official indexes into tracked data assets.
4. `v1.3 extraction quality`: expand gold sets, parser coverage, OCR handling,
   and program-change reconciliation.
5. `v1.5 operator console`: rebuild production Streamlit UI from ViewModels and
   the demo-derived UI contract.
6. `v2.0 university expansion`: add university support only after the
   vocational-school pipeline has completed a stable cycle.
7. `v2.x multi-user/cloud`: add platform infrastructure only when a real
   multi-operator or remote-operation requirement exists.

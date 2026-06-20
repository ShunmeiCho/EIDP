# Goal Execution Discipline

These rules apply when EIDP is advanced through a long-running `/goal` or other
autonomous work loop. They are intended to keep progress evidence-first,
release-scoped, and reversible.

## Scope Control

Treat the stated final product vision as broader than the v1 release scope.

Current v1 release scope is:

- vocational schools (`専門学校`) first
- one-operator Windows workflow
- weekly PDF discovery
- target fiscal-year judgment
- extraction, OCR fallback, and manual review
- audit trail
- Excel-ready gate and workbook output

University production workflow, multi-operator support, PostgreSQL, full React
frontend, full official-index management UI, and complete school-detail evidence
chain productization are roadmap work unless explicitly approved for a release.

## Current-State Audit First

Before starting a new slice, establish the current facts from live repository
evidence. Do not rely only on README text, old PPTX files, old HTML, or memory.

The audit must identify:

- existing capability
- missing capability
- contradictory artifacts
- release blockers
- post-release items
- files likely to be touched
- verification commands

If documentation, prototype, code, release reports, or PPTX materials disagree,
record the mismatch as artifact drift. Do not claim the feature is complete.

## Finding Severity

Classify findings before acting:

| Severity | Meaning | Current release path |
| --- | --- | --- |
| P0 Release Blocker | Can put wrong data into Excel, wrong year, wrong school, or prevent release validation | Must fix or explicitly block release |
| P1 Release Hardening | Improves reliability or operator safety but may not block RC | May enter current release path |
| P2 Documentation / Demo Drift | Artifact inconsistency that does not change core data behavior | Fix when cheap; otherwise track |
| P3 Roadmap | Valuable but outside v1 | Do not implement in v1 without approval |

Only P0 and P1 items may enter the current release path by default.

## Slice Discipline

Each work round should advance one verifiable slice. Do not combine UI
restructure, official-index modeling, parser changes, Excel export, audit, and
Windows packaging in one uncontrolled sweep.

Good slices include:

- release-scope and document wording alignment
- design artifact inventory and drift cleanup
- `current_lane` / `blocking_reason` / `next_action`
- R7/R8 fiscal-year misclassification tests
- Excel-ready gate hardening
- program-change review task
- audit coverage
- Windows packaging validation
- release evidence bundle

Each slice must state entry files, change boundary, verification command,
acceptance criteria, and rollback point.

## Evidence-First Reporting

Every work round must report:

1. `Done`: what changed and which files were touched.
2. `Verified`: commands or checks run, with result summary.
3. `Still Blocking`: release blockers or decisions still open.
4. `Next Slice`: exactly one next smallest verifiable action.

Avoid unsupported claims such as "basically complete" or "ready enough".

## Release Forecast Cadence

Daily or per-slice progress does not require filling the full release checklist.
It does require a short, fixed Release Forecast so "can run" is not mistaken
for "can ship":

```text
Release Forecast: READY / RC_ONLY / NOT_READY
Why: one-line reason
Evidence: source head, packaged commit, latest CI, latest Windows canary
P0: open release blockers
Next: one smallest verifiable slice
```

Formal `READY`, `RC_ONLY`, package handoff, or owner-facing release decisions
must use the full release gate checklist and evidence bundle. A release forecast
is not a substitute for the checklist; it is the lightweight daily signal that
keeps source/package, bounded/global, Windows, owner-decision, and Excel-ready
evidence boundaries visible.

## Release Conclusion Vocabulary

Use only these release conclusions:

- `READY`: all release gates passed and an evidence bundle exists.
- `RC_ONLY`: core workflow can be demonstrated or trialed, but known limits or
  owner decisions remain.
- `NOT_READY`: at least one P0 blocker remains.

Each conclusion must cite evidence, blockers, required owner decisions, and the
next smallest action.

## Stop-The-Line Conditions

Do not claim release-ready when any of these are present:

- fiscal-year judgment lacks evidence
- a prior-year PDF can be confirmed as the target year
- non-target PDF enters business metrics
- school mismatch enters the target school
- low-confidence data can enter final Excel
- program changes bypass review
- manual actions bypass audit logging
- Excel-ready gate is missing or bypassed
- Windows validation is missing
- README, architecture, UI prototype, PPTX, and release status contradict each
  other on scope or readiness

## Demo And Production Boundary

The HTML operations-console prototype is a design reference and demo artifact.
Do not iframe it into Streamlit, copy generated runtime into `src/eidp`, use
mock dashboard numbers as production metrics, or package it as the operator app.

Old PPTX files containing terms such as `DB転記済`, `要確認キュー`,
`Excelプレビュー`, or `DBに転記して次へ` must not be used as the current UI
baseline or stakeholder demo without regeneration from the current prototype.

## Data Safety

Do not modify production-like SQLite data, sample data, or Excel outputs just to
make status look green.

Any data migration requires:

- database backup
- schema before/after description
- dry-run mode
- rollback plan
- migration test
- append-only contract verification
- no direct edits to production Excel as system output

## Dependency Discipline

Do not add heavyweight dependencies unless the proposal explains:

- why existing dependencies cannot solve the problem
- Windows offline wheelhouse impact
- ZIP size impact
- Defender / SmartScreen impact
- required operator configuration
- fallback behavior

Node services, browser runtimes, LLM SDKs, Agent-Reach, cloud databases, or new
OCR engines are not default answers for v1.

## Windows-First Release Evidence

Mac/Linux tests prove business logic and package shape only. Release-ready
claims require Windows VM or real-PC evidence for:

- `EIDP-setup.bat`
- `EIDP-start.bat`
- `weekly_run.bat`
- `EIDP-diagnose.bat`
- SQLite file locking
- Excel output
- OCR add-on, if advertised
- Windows paths and encoding
- Defender / SmartScreen notes where applicable

## Owner Decisions

The agent may prepare a decision brief. It must not approve owner decisions.

Owner decisions include:

- accepting a publication-lag release exception
- changing strict yield gates
- excluding schools from the release denominator
- accepting a manual workload percentage
- changing Excel output scope
- expanding v1 scope beyond vocational schools

## Red-Line Checks To Automate

Prefer tests or scripts over documentation-only rules where practical:

- current UI does not use dangerous old labels
- prior-year identical PDFs cannot be confirmed as target year
- Excel export excludes unconfirmed rows
- low-confidence rows do not become current Excel rows
- school mismatch blocks ingest
- non-target PDFs block ingest
- manual business actions are audited
- design prototype files are not packaged as production runtime

# Post-v1 Decision Board

This board keeps post-v1 work assigned to a release train. It is not a promise
that all items are ready to implement.

> **2026-07-11 track consolidation.** The three former tracks are collapsed
> into Linux/Web-only `main`. The product direction is accepted; release still
> requires served-app evidence. See
> `docs/reports/2026-07-11-owner-v1-track-decision-brief.md` and
> `docs/decisions/ADR-2026-07-linux-web-pivot.md`. The `C1`–`C3` rows below are
> v1-pivot-track items tracked here for visibility.

| ID | Task | Phase | Priority | Entry condition | Exit condition | Status |
| --- | --- | --- | --- | --- | --- | --- |
| P1 | Patch operator-facing wording drift | v1.0.x patch | P1 | v1 tag or RC scope frozen | Current UI/docs no longer use dangerous old labels as current baseline | planned |
| P2 | Polish Excel file-lock recovery message | v1.0.x patch | P1 | operator feedback or validation issue | Operator can recover without administrator help | planned |
| P3 | Improve diagnostics bundle readability | v1.0.x patch | P2 | v1 validation feedback | Bundle names release blockers and next action clearly | planned |
| H1 | Formalize `current_lane` enum or constants | v1.1 hardening | P0 | v1 tag created or RC stabilization begins | UI pages share one lane vocabulary | planned |
| H2 | Centralize Japanese UI labels | v1.1 hardening | P1 | current label inventory complete | production pages import labels from one map | planned |
| H3 | Convert Excel-ready gate to an auditable hard rule | v1.1 hardening | P0 | existing export behavior audited | unconfirmed rows block or are excluded with reason | planned |
| H4 | Add automated checks for demo/prototype packaging boundary | v1.1 hardening | P1 | design package inventory complete | standalone HTML and generated runtime are excluded from production runtime | planned |
| S1 | Create authority index source registry | v1.2 source reliability | P1 | source audit complete | source URL, format, trust tier, and parser are tracked | planned |
| S2 | Track authority index artifacts with hash and parser version | v1.2 source reliability | P1 | artifact storage boundary agreed | fetched artifacts can be reproduced and diffed | planned |
| S3 | Add unmatched authority-index entry review flow | v1.2 source reliability | P2 | index entries normalized | operator can resolve unmatched entries with audit | planned |
| X1 | Expand target and non-target PDF gold set | v1.3 extraction quality | P1 | parser inventory complete | regression suite covers target, old-year, non-target, and image PDFs | planned |
| X2 | Add fiscal-year misclassification regression set | v1.3 extraction quality | P0 | R7/R8 risk cases identified | prior-year identical values cannot auto-confirm target year | planned |
| X3 | Build program-change review samples | v1.3 extraction quality | P1 | sample PDFs collected | new/discontinued/renamed/merged/split cases have fixtures | planned |
| U1 | Build Streamlit dashboard ViewModel | v1.5 operator console | P1 | lane/status vocabulary stable | dashboard renders from ViewModel, not scattered queries | planned |
| U2 | Build school queue ViewModel | v1.5 operator console | P1 | `current_lane` and labels stable | queue rows show blocker and next action consistently | planned |
| V2U1 | Create university pilot gold set | v2.0 university expansion | P2 | vocational-school v1 stable cycle complete | 50 university samples classified with parser notes | blocked |
| V2P1 | Evaluate PostgreSQL and multi-operator architecture | v2.x multi-user/cloud | P3 | real multi-operator requirement exists | decision brief approved by owner | research |
| C1 | Consolidate Linux/Web as single `main` | v1 (pivot) | P0 | direction decided 2026-07-11 | `main` converged; Windows assets and merged branches/worktrees removed | in-progress (branch cleanup pending) |
| C2 | Define Linux/Web served-app release gate | v1 (pivot) | P0 | pivot ADR accepted | gate documented and enforced in CI; Venus/LAN evidence collected | in-progress (deployment evidence pending) |
| C3 | Ohara reach-10 vs accept-7 decision | v1 (pivot) | P1 | Rung 1c 7/7 clean gate green | owner authorises scoped reach-10 fold, or accepts the honest 7-school clean gate | needs owner decision |

## Board Rules

- Do not implement `blocked` or `research` items without an owner-approved
  phase decision.
- Do not move university work earlier than v2.0 without changing release scope.
- Do not move React/PostgreSQL platform work earlier than v2.x unless
  multi-operator or remote operation becomes a real requirement.
- Add new tasks only if they have an entry condition and an exit condition.

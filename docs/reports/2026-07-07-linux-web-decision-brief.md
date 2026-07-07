# Linux/Web v1 — Owner/PI Decision Brief (diff-engine convergence + ADR reconciliation)

- Status: Decision brief (no approval, no code change)
- Date: 2026-07-07
- Branch: `integration/linux-web-v1` (HEAD after P2 guard)
- Release Forecast: `NOT_READY` (unchanged)
- Author role: main-line implementation owner — surfacing decisions, NOT self-approving

## Purpose

Two architecture-debt items accumulated on `integration/linux-web-v1` as the Ohara
core and the Linux/Web slices merged. Neither is a correctness blocker (the P2
`department_key` guard closed the last known correctness hole), but both create
confusion and future-bug risk. This brief states the facts, options, and a
recommendation for each, and separates "what the implementation owner may do
without sign-off" from "what needs owner/PI."

---

## Decision 1 — Three diff engines, three vocabularies

### Facts

| Engine | Entry point | Status model | Gate? | Consumer |
| --- | --- | --- | --- | --- |
| `excel/master_diff.py` | `diff_metric_rows` + `rung_gate` | 5-category (exact_match / value_mismatch / missing_actual / unexpected_actual / ambiguous_key) | YES — HARD_GATE_METRICS must be exact; `ambiguous_key` BLOCKING | Rung 1a/1b/1c acceptance |
| `pipeline/review_master_diff.py` | `diff_reviewed_against_master` | `MatchStatus` (7 values) | No — report only | Web page 04 review_diff |
| `pipeline/double_check_compare.py` | `compare_external_to_reviewed` | `DoubleCheckStatus` (7 values, TRUE/FALSE) | No — `excel_ready` always False | Web page 05 double_check |

Each engine carries its OWN near-identical join key (`school + 分野 + department_key
+ FY + metric`), its own `_values_equal` / `_comparable_value`, and its own
ambiguous-key handling. The P2 bug was a direct symptom: the bare-コース false-merge
was blocked in `excel/master_diff` but NOT in the other two, because the correctness
logic is copy-pasted, not shared. The fix had to edit two engines identically.

### Options

- **A. Full unify** — one status model + one diff core; the three engines become
  thin adapters. Highest cleanup, highest churn; risks over-merging genuinely
  different domain semantics (acceptance gate vs review report vs TRUE/FALSE).
- **B. Document-only** — a contract doc plus a "mirror every change across all
  three" checklist. Cheapest, but the copy-paste correctness risk (the P2 class)
  persists.
- **C. Extract the shared correctness core** — pull the load-bearing primitives
  (loose + strict `department_key` comparison, ambiguity / collision detection,
  comparable-value coercion) into one module; keep the three status vocabularies.
  Kills the P2 bug class without forcing a status-model merge.

### Recommendation: **C**

The three status models serve genuinely different consumers and should stay. But
the correctness primitives must have ONE home so a guard can never again live in
1 of 3 engines. This is a contained, behavior-preserving refactor (a new
`src/eidp/pipeline/department_join.py`, or an extension of `master_ground_truth`),
already covered by the three existing test suites.

### Split

- **Implementation owner (no sign-off needed):** Option C — internal, additive,
  reversible, TDD with full-suite green. Default action.
- **Owner/PI:** only if you prefer **A** (full unify) or **B** (doc-only).

---

## Decision 2 — Three ADRs on the pivot / architecture

### Facts

| ADR | Status | Lang | Scope |
| --- | --- | --- | --- |
| `ADR-2026-07-linux-web-pivot.md` | Proposed | EN | The product pivot (Windows → Linux/Web): the WHY + open owner/PI decisions |
| `ADR-2026-07-multi-user-web-architecture.md` | Proposed | EN | Multi-user architecture boundary (Python core + FastAPI + PostgreSQL + React target) + multi-user contracts + Goal 4 boundary |
| `ADR-2026-07-web-multiuser-architecture.md` | DRAFT | CN | The SAME architecture decision (D1–D10 + Phase A–E + Rung-1c guardrail + 内网 deployment detail) |

- `linux-web-pivot` has a distinct scope (the product WHY) — keep it as the
  foundational ADR.
- The other two are the SAME decision (multi-user: Python core + FastAPI +
  PostgreSQL + React) written twice — different language, different status
  (Proposed vs DRAFT), complementary detail. The EN one carries the multi-user
  contracts and the Goal 4 boundary; the CN one carries the 内网 deployment detail
  (D7), the domain objects (D8), the UI page priority (D9), and the Rung-1c-gate
  guardrail.

### Contradiction to resolve (owner/PI)

The two multi-user ADRs place React / FastAPI / PostgreSQL as the **v1** multi-user
target (Phase B–E). But `docs/roadmap/post-v1-decision-board.md` row **V2P1**
("Evaluate PostgreSQL and multi-operator architecture") pins that work to **v2.x**,
priority **P3**, status **research**, entry condition "real multi-operator
requirement exists" — and a board rule forbids moving React/PostgreSQL earlier than
v2.x "unless multi-operator or remote operation becomes a real requirement." The
pivot ADR, meanwhile, states that v1 IS now a multi-user Linux/Web tool.

→ Owner/PI must resolve: **is multi-user React / FastAPI / PostgreSQL a v1
deliverable, or a v2.x one?** The meaning of "v1 done" and every phase mapping
downstream depends on this single answer.

### Options for the two duplicate ADRs

- **A. Merge into ONE canonical ADR** — keep
  `ADR-2026-07-multi-user-web-architecture.md`, fold the CN ADR's D7/D8/D9 +
  Rung-1c guardrail into it, mark the CN DRAFT as `Superseded-by`. Single status,
  single source of truth.
- **B. Keep both** — cross-link and demote one to a language mirror.

### Recommendation: **A (merge to one)**, pending the v1-vs-v2.x resolution

Merge the two multi-user ADRs into one canonical ADR; keep `linux-web-pivot`
separate as the WHY. Do NOT escalate the merged ADR's status past `Proposed` until
owner/PI resolves the v1-vs-v2.x scope question — the status and phase mapping
depend on that answer.

### Split

- **Implementation owner:** the mechanical merge of the two duplicate ADRs into
  one (cross-linked, no status escalation) — after owner/PI answers the scope
  question, or explicitly says "merge now, keep Proposed."
- **Owner/PI:** (1) v1 multi-user React/Postgres, or v2.x? (2) approve the merge.

---

## What is NOT changing

- No code changed by this brief.
- No ADR status escalated to `Accepted` / `READY`.
- Release Forecast: `NOT_READY`.
- `main` untouched; the Windows track remains legacy / fallback (not deleted).

## Recommended next actions (ordinal, not a schedule)

1. [owner, no sign-off] Option **C**: extract the shared diff correctness core —
   removes the P2 bug class (a guard that lives in only some engines).
2. [owner/PI] Answer: multi-user React / FastAPI / PostgreSQL = **v1** or **v2.x**?
   (unblocks the merged ADR's status + phase mapping)
3. [owner, after #2] Merge the two duplicate multi-user ADRs into one canonical ADR.
4. [owner] P3 housekeeping: prune the scratch candidate worktrees.

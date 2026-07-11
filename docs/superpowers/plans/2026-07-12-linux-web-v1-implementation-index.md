# Linux/Web v1 Program Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the approved internally acceptable Linux/Web v1 from protected source publication through served workflow, evidence integrity, partial export, Venus deployment and PI acceptance.

**Architecture:** The program is split into five independently reviewable implementation phases plus the publication phase. Each phase produces working, tested software or an external evidence gate; every code phase merges through a short-lived PR into the sole product mainline before its dependent phase starts.

**Tech Stack:** Python 3.12, Streamlit 1.56, SQLAlchemy, Alembic, SQLite, openpyxl, Bash, uv, pytest, GitHub Actions, institutional reverse proxy

## Global Constraints

- Authoritative design: `docs/superpowers/specs/2026-07-12-linux-web-v1-venus-design.md`.
- Current release conclusion remains `NOT_READY` until Phase 5 evidence and PI sign-off.
- Windows remains retired; React/FastAPI/PostgreSQL remain v2 scope.
- `main` is the sole product definition. Short-lived PR branches are transport/review mechanisms only.
- Never direct-push protected `main`; every phase requires `Python quality gates` and `Ship gate contract`.
- Do not SSH to initialize Venus before Phases 0–4 are merged and green.
- Do not write outside `/home/junming/EIDP` on Venus.
- Preserve `data/master.xlsx` read-only, append-only business/audit revisions, global write lock and no-secret logging.
- Never delete the red-line facts of record: `data/eidp.sqlite3`, `data/audit/manual-actions.jsonl`, or `data/master.xlsx`.

## Ordered Plan Suite

| Order | Plan | Independently testable outcome |
| --- | --- | --- |
| 0 | `2026-07-12-linux-web-v1-phase-0-publication.md` | consolidated source is published through real required GitHub CI |
| 1 | `2026-07-12-linux-web-v1-phase-1-runtime-recovery.md` | local project controller, manifest, finalized backup and isolated restore work |
| 2 | `2026-07-12-linux-web-v1-phase-2-identity-served-workflow.md` | trusted identity and served intake-to-persisted-double-check flow work with DB audit |
| 3 | `2026-07-12-linux-web-v1-phase-3-source-evidence.md` | one full-SHA registry, provenance, retention and safe cleanup replace legacy paths |
| 4 | `2026-07-12-linux-web-v1-phase-4-partial-export.md` | served partial export emits finalized workbook plus complete audited manifest |
| 5 | `2026-07-12-linux-web-v1-phase-5-venus-acceptance.md` | Venus/LAN/off-host/business/PI evidence supports the release conclusion |

## Dependency Gate

```text
Phase 0 protected publication
  -> Phase 1 runtime/recovery
  -> Phase 2 identity + served decisions
  -> Phase 3 canonical source evidence
  -> Phase 4 partial export
  -> Phase 5 Venus + ICT + business + PI acceptance
```

Phase 3 consumes Phase 2 identity/audit. Phase 4 consumes Phase 2 decisions and Phase 3 canonical source hashes. Phase 5 starts only after every earlier PR is merged and both required checks are green.

## Program Checkpoints

- [ ] **Checkpoint 0:** Publish current consolidated source; observe real CI rather than assuming green.
- [ ] **Checkpoint 1:** Prove controller/manifest/backup/restore locally; do not claim off-host recovery.
- [ ] **Checkpoint 2:** Prove actual Streamlit pages reach extraction and persist audited decisions; core-only E2E is insufficient.
- [ ] **Checkpoint 3:** Prove full-hash no-overwrite storage and close every legacy overwrite/delete bypass.
- [ ] **Checkpoint 4:** Prove row-scoped export, complete manifest and staged-to-finalized audit lifecycle.
- [ ] **Checkpoint 5:** Obtain authorized SSH/ICT/business/PI evidence; only then evaluate `READY`.

## Review Policy

After every task commit, run its focused tests and request an independent review. Before every phase PR, run Ruff, high-severity Bandit, strict mypy and full pytest with at least 80% project coverage. A failed GitHub job or external gate stops the phase and produces a concrete evidence-based fix plan; it is never bypassed by weakening tests, scope or security controls.

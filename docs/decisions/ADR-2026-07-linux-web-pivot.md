# ADR-2026-07: Linux-server Web pivot for EIDP v1

- **Status: PROPOSED** — *not* Accepted. Pending owner / PI (一貴) sign-off.
- Date: 2026-07-05
- Branch: `feature/table-aware-ohara-extraction` (isolated; `main` untouched).

> **Scope of this ADR.** It records a **development direction only**. It does
> **NOT** change `/goal`, the release forecast/conclusion (baseline stays
> `NOT_READY` on v548), or any governance doc, and it does **NOT** declare the
> Windows track dead. Every ratification step below is owner-gated.

---

## Context

- The Windows automated-discovery path caps at **~24% end-to-end** (`12/50`) for a
  deliberately hard **50-school target-missing cohort** (companion `47/50 = 94%`
  operator-reviewable). This `24%` is a per-school end-to-end *strict Excel-ready*
  rate for a hard cohort — **not** an extraction-failure, PDF-fetch, or completion
  rate. The 76% non-auto is **upstream-dominated** (discovery non-target
  filtering, dense multi-brand sibling mismatch, ~20%-reliable content-based
  year-judgment), with extraction/table-parsing a secondary contributor.
- The 2026-07-05 planning meeting decided **v1 = correct-PDF input + extraction +
  double-check**: a human hands over the correct-fiscal-year
  `機関要件確認申請書` PDF (automated year-judgment dropped as a blocking gate),
  EIDP extracts with a table-grid-first extractor, and an operator-run external
  cross-check ("double-check") is reconciled by a human.

## Decision (PROPOSED — pending owner / PI 一貴 sign-off)

- **v1 direction = Linux-server Web app, browser-accessed**, prioritising
  専門学校 (university production stays v2+).
- **Windows single-machine track = historical / fallback — NOT declared dead.**
  It remains the only currently runnable deliverable; the release baseline stays
  `NOT_READY` on v548 until the owner rules otherwise.

### Deployment-agnostic assets that stay (survive either branch)

- Extractor (`src/eidp/pdf/extractor.py`)
- Table-grid extractor (`src/eidp/pdf/table_grid_extractor.py`)
- `master.xlsx` ground-truth diff — loader (`src/eidp/excel/master_loader.py`) +
  engine (`src/eidp/excel/master_diff.py`); acceptance line = G1 `diff=0`
- Confidence cascade (`src/eidp/extraction_confidence.py`, 0.85/0.70/0.50)
- Excel / XLOOKUP exporter (`src/eidp/excel/exporter.py`,
  `competition_exporter.py`)
- Four-table append-only fiscal_year override + audit (`manual_action_log` +
  JSONL outbox)

### Current no-regret work — DONE (on the isolated branch)

- **Field aliases** — `src/eidp/pdf/field_aliases.py` (canonical metric labels;
  生徒|学生 seito/gakusei → capacity/enrollment/intl_students).
- **Table-aware extraction** — `src/eidp/pdf/table_grid_extractor.py ::
  extract_table_grid_records` (grid-cell reads with page/table/row/col evidence).
- **`master.xlsx` diff loader + engine** — `master_loader.py ::
  load_master_metric_rows` (READ-ONLY) and `master_diff.py :: diff_metric_rows`;
  helper `master_ground_truth.py`.
- Tests green; `extractor.py` not modified. Re-baseline the plan to start at the
  `master.xlsx` ground-truth diff slice.

## Pending owner-gated items

- **Pivot ratification** — Linux/Web as *released* v1 vs keep Windows v548.
- **Linux/Web release gate** — define the served-app acceptance gate.
- **Network reachability** — only education-net/STF reaches the lab Linux server;
  a go/no-go pre-check, not a post-hoc gate.
- **Copilot / NotebookLM PII / external-cloud policy** — default disabled;
  operator-driven import only, no auto-upload of disclosure PDFs.
- **OCR scope** — image-only PDFs (`CORE_TEXT_PDF_ONLY` vs `OCR_ADDON_REQUIRED`).
- **SQLite multi-user concurrency** — single-writer lock contract
  (`src/eidp/db/locking.py`) vs multi-user web writes; possible real DB decision.

---

## Related documents

- `docs/governance/release-gates.md`, `docs/governance/owner-release-signoff.md`
- `docs/release/owner-decisions/publication-lag.md`,
  `docs/release/owner-decisions/ocr-scope.md`
- `CLAUDE.md` (G1–G15, four-table override contract, lock contract, red-line files)
- Owner decision package (evidence, gate matrices, portable/archive split,
  adversarial critique) — source input for this ADR.

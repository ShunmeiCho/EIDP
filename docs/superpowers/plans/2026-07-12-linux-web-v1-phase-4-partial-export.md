# Linux/Web v1 Phase 4 Partial Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate recoverable server-side Excel bundles containing only eligible reviewed rows, with a complete exclusion/hold manifest and an audited staged-to-finalized lifecycle.

**Architecture:** A pure eligibility planner classifies every selected row and summarizes institutions. A dedicated long-form workbook writer consumes included rows only; an export-bundle service stages workbook/manifest, records a deterministic audit event, flushes the outbox, then atomically publishes a finalized package that alone is downloadable.

**Tech Stack:** Python 3.12, SQLAlchemy, openpyxl, Streamlit, pytest, Streamlit AppTest

## Global Constraints

- Execute only after Phase 2 audited review/mismatch persistence and Phase 3 canonical source identity are merged.
- Do not modify or call the legacy `export_master_workbook()` for served review output.
- Gate at row scope: one institution may be `included_partial`; an ineligible row never suppresses an eligible sibling row.
- Refuse exports with zero eligible target-year rows.
- Workbook contains only `included`; JSON manifest contains every `included`, `withheld`, and `excluded` row.
- Manifest schema ID is exactly `eidp.export-manifest.v1` and bundle path is `output/exports/{export_id}`.
- Audit-pending rows are withheld. A staged bundle is not downloadable or business-usable.
- `data/master.xlsx` is read-only.

Before Task 1:

```bash
git fetch --prune origin
git switch -c feat/linux-web-v1-phase4-partial-export origin/main
```

---

### Task 1: Assemble One Authoritative Export Candidate Per Metric

**Files:**
- Create: `src/eidp/pipeline/export_candidates.py`
- Create: `tests/unit/test_export_candidates.py`

**Interfaces:**
- Consumes: immutable base review records in the selected intake scope, latest Phase 2 review decisions, immutable comparison results/resolutions, canonical Phase 3 documents/holds and audit projection state
- Produces: `ExportCandidate` and one authoritative instance per stable metric row for target-year classification

- [ ] **Step 1: Write failing candidate-assembly tests**

Build a temporary intake root and SQLite session containing accepted, corrected, excluded, unresolved-mismatch, resolved-mismatch, audit-pending, image, old-year and non-target rows. Assert the assembler uses the latest review decision, binds a resolution to the exact immutable comparison result/review revision, carries canonical source/classification/active-hold state and returns one deterministic candidate per metric/task key. Legitimately absent decisions/hashes/comparison results remain nullable only with one protecting hold. Missing canonical documents, zero/multiple holds, duplicate IDs/metric keys and dangling or contradictory references fail closed instead of choosing arbitrarily.

```python
def test_candidate_assembly_binds_exact_review_and_comparison_snapshot(
    candidate_fixture: CandidateFixture,
) -> None:
    rows = load_export_candidates(
        candidate_fixture.session,
        intake_root=candidate_fixture.intake_root,
        target_fiscal_year=2026,
        comparison_run_id=candidate_fixture.comparison_run_id,
    )
    row = next(item for item in rows if item.metric == "capacity")
    assert row.review_action_id == candidate_fixture.review_action_id
    assert row.comparison_status == "resolved_match"
    assert row.resolution_action_id == candidate_fixture.resolution_action_id
    assert row.source_sha256 == candidate_fixture.source_sha256
```

- [ ] **Step 2: Verify failure**

```bash
uv run pytest tests/unit/test_export_candidates.py -v
```

Expected: FAIL because no authoritative candidate assembler exists.

- [ ] **Step 3: Implement the assembler**

```python
@dataclass(frozen=True)
class ExportCandidate:
    review_id: str
    school_id: int
    school_name: str
    reported_fiscal_year: int
    department_key: str | None
    department_name: str | None
    course_name: str | None
    metric: str | None
    review_value: int | None
    accepted_value: int | None
    review_status: str
    confidence: float
    task_type: str
    document_fiscal_year: int | None
    target_disposition: str | None
    document_target_status: str | None
    pdf_kind: str | None
    source_lane: str
    comparison_run_id: str
    comparison_status: str | None
    review_action_id: str | None
    review_actor: str | None
    review_identity_source: str | None
    reviewed_at: datetime | None
    review_audit_exported: bool
    resolution_action_id: str | None
    resolution_audit_exported: bool
    source_document_id: int | None
    source_sha256: str | None
    active_hold_id: int
    active_hold_type: str
    active_hold_source_key: str
    blocking_task_id: str | None
    business_excluded_reason: str | None


def load_export_candidates(
    session: Session, *, intake_root: Path, target_fiscal_year: int,
    comparison_run_id: str,
    intake_record_ids: Sequence[str] | None = None,
) -> list[ExportCandidate]:
    """Join immutable base rows to exact persisted decisions/evidence; fail on ambiguity."""
```

Read every immutable base candidate in the selected intake-record scope; `target_fiscal_year` is classification context and must not filter old/non-target rows out before planning. Preserve the intake year only as `reported_fiscal_year`; canonical classification and metric keys use nullable `document_fiscal_year`. Overlay only the highest persisted `ExtractionReviewDecision` revision for each review ID. Require an explicit immutable `comparison_run_id`; join results only from that run and only when stored review ID, decision revision and review audit action ID match the exact decision. Never silently choose the latest run. Resolve source identity/fiscal year/target status/PDF kind/source lane through canonical DB state; never trust a JSON filename/hash as authority.

Require exactly one active Phase 3 workflow hold for every candidate, keyed `metric:{review_id}` for metric rows or `task:{review_id}` for image/non-metric tasks. Carry its ID/type/key. Zero, multiple, or state-incompatible holds are `ExportCandidateIntegrityError` (or require explicit reconciliation before retry), never an ordinary withheld condition. Terminal includable/business-excluded/old/non-target rows require an `export` hold; unresolved rows require their exact `review` or `diff` hold.

A legitimate missing decision/hash/comparison result remains nullable and withheld only while that exact hold protects it. Missing canonical document for a row that claims source provenance, or any present-but-dangling reference, is structural failure. Build complete metric keys from school, canonical document fiscal year, department, course and metric; if a component is missing, use unique `task:{review_id}` only for manifest/withheld display and never include it. Reject duplicate complete metric keys and duplicate review IDs. Add tests for reported year differing from canonical year, two same-school image tasks remaining distinct, and two comparison runs for one review revision selecting only the explicit run. JSON contributes immutable extraction facts only; DB decisions, comparison state, identity, hold and audit readiness are authoritative.

Keep `review_value` separate from the final `accepted_value`. For an exact `MATCH`, accepted value is the snapshot-bound EIDP/review value. For a mismatch with `ACCEPT_EIDP`, `ACCEPT_EXTERNAL`, or `CORRECT`, use only the persisted Phase 2 resolution `effective_value`; never recompute from mutable UI/import data. Review- or resolution-level `EXCLUDE`, missing comparison, unresolved mismatch, incompatible snapshot, or unaudited resolution yields `accepted_value=None`. Parameterize candidate/workbook tests for all outcomes, especially `ACCEPT_EXTERNAL` writing the external snapshot value rather than the prior EIDP review value.

- [ ] **Step 4: Run tests and commit**

```bash
uv run pytest tests/unit/test_export_candidates.py tests/unit/test_review_decision.py tests/unit/test_double_check_resolution.py -v
uv run ruff check src/eidp/pipeline/export_candidates.py tests/unit/test_export_candidates.py
uv run mypy src/eidp/pipeline/export_candidates.py
git add src/eidp/pipeline/export_candidates.py tests/unit/test_export_candidates.py
git commit -m "feat: assemble authoritative export candidates" -m "Goals: G1, G2, G3, G10"
```

### Task 2: Deterministic Eligibility Planning

**Files:**
- Create: `src/eidp/pipeline/export_eligibility.py`
- Create: `tests/unit/test_export_eligibility.py`

**Interfaces:**
- Consumes: `ExportCandidate` from `export_candidates.py`
- Produces: `ExportPlan`, row disposition/reason and institution state

- [ ] **Step 1: Write failing classification tests**

Test same-institution mixed inclusion, all nine hold reasons, institution four-state summary, missing source hash/review identity/audit projection, mismatch with/without resolution, image/old/non-target/business exclusion, and zero included.

```python
def test_same_institution_can_be_included_partial(eligible_row: ExportCandidate, held_row: ExportCandidate) -> None:
    plan = plan_partial_export(
        candidates=[eligible_row, held_row],
        fiscal_year=2026,
    )
    assert [row.disposition for row in plan.rows] == [Disposition.INCLUDED, Disposition.WITHHELD]
    assert plan.institutions[eligible_row.school_id] == InstitutionState.INCLUDED_PARTIAL
```

- [ ] **Step 2: Verify failure**

```bash
uv run pytest tests/unit/test_export_eligibility.py -v
```

Expected: FAIL because the planner does not exist.

- [ ] **Step 3: Implement exact enums and immutable results**

```python
class Disposition(StrEnum):
    INCLUDED = "included"
    WITHHELD = "withheld"
    EXCLUDED = "excluded"


class HoldReason(StrEnum):
    UNREVIEWED = "unreviewed"
    LOW_CONFIDENCE = "low_confidence"
    IMAGE_EXCEPTION = "image_exception"
    AMBIGUOUS_KEY = "ambiguous_key"
    DOUBLE_CHECK_MISMATCH = "double_check_mismatch"
    AUDIT_PENDING = "audit_pending"
    NON_TARGET = "non_target"
    OLD_YEAR = "old_year"
    BUSINESS_EXCLUDED = "business_excluded"


class InstitutionState(StrEnum):
    INCLUDED_COMPLETE = "included_complete"
    INCLUDED_PARTIAL = "included_partial"
    WITHHELD = "withheld"
    EXCLUDED = "excluded"


class NoEligibleRowsError(ValueError):
    """Raised by staging when a complete plan contains no includable row."""


@dataclass(frozen=True)
class PlannedExportRow:
    candidate: ExportCandidate
    row_key: str
    disposition: Disposition
    reason: HoldReason | None
    all_reasons: tuple[HoldReason, ...]
    reason_detail: str | None


@dataclass(frozen=True)
class ExportPlan:
    rows: tuple[PlannedExportRow, ...]
    institutions: Mapping[int, InstitutionState]

    @property
    def included_rows(self) -> tuple[ExportCandidate, ...]:
        return tuple(row.candidate for row in self.rows if row.disposition == Disposition.INCLUDED)


def stable_export_row_key(candidate: ExportCandidate) -> str:
    if candidate.document_fiscal_year is None or not candidate.department_key or not candidate.metric:
        return f"task:{candidate.review_id}"
    payload = [candidate.school_id, candidate.document_fiscal_year, candidate.department_key, candidate.course_name or "", candidate.metric]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()


def plan_partial_export(*, candidates: Sequence[ExportCandidate], fiscal_year: int) -> ExportPlan:
    """Classify every candidate deterministically and always return the full preview."""
```

Use this exact precedence for the primary `reason`, while retaining every applicable value in `all_reasons`:

1. Excluded: `OLD_YEAR`, `NON_TARGET`, `BUSINESS_EXCLUDED`.
2. Withheld: `IMAGE_EXCEPTION`, `AMBIGUOUS_KEY`, `UNREVIEWED`, `LOW_CONFIDENCE`, `DOUBLE_CHECK_MISMATCH`, `AUDIT_PENDING`.

Canonical `target_disposition="old_year"` maps to `OLD_YEAR`; other canonical non-target classifications map to `NON_TARGET`. Neither is inferred from `task_type`. `BUSINESS_EXCLUDED` is terminal only when the Phase 2 EXCLUDE decision has a nonblank bounded reason, actor/source, exported audit action and exact export hold; otherwise the row is withheld (`UNREVIEWED` or `AUDIT_PENDING`) and its hold cannot be released. `UNREVIEWED` also covers a missing accepted/corrected decision, accepted value, review actor/source/time or full source hash while an exact active hold remains. `AMBIGUOUS_KEY` covers a missing/unstable school-department-course-metric key, including image/non-metric tasks; their `task:{review_id}` key prevents collision but never makes them includable. `DOUBLE_CHECK_MISMATCH` remains until a persisted resolution is bound to the exact comparison result. `AUDIT_PENDING` applies when any required review/resolution action lacks a successful outbox projection. Add parameterized tests for every rule, multi-reason precedence, and an EXCLUDE missing reason/identity/audit so a later refactor cannot silently terminalize it.

Institution state is exact: all rows included -> `INCLUDED_COMPLETE`; at least one included plus any non-included -> `INCLUDED_PARTIAL`; no included plus at least one withheld -> `WITHHELD`; all rows excluded -> `EXCLUDED`. Parameterize included+excluded and excluded+withheld. A zero-included plan is still returned so the page can show every reason; `stage_export_bundle()` is the boundary that raises `NoEligibleRowsError`.

- [ ] **Step 4: Run tests and commit**

```bash
uv run pytest tests/unit/test_export_eligibility.py -v
uv run ruff check src/eidp/pipeline/export_eligibility.py tests/unit/test_export_eligibility.py
uv run mypy src/eidp/pipeline/export_eligibility.py
git add src/eidp/pipeline/export_eligibility.py tests/unit/test_export_eligibility.py
git commit -m "feat: plan row-scoped partial exports" -m "Goals: G1, G2, G3, G10"
```

### Task 3: Review-Output Workbook Writer

**Files:**
- Create: `src/eidp/excel/review_exporter.py`
- Create: `tests/unit/test_review_exporter.py`

**Interfaces:**
- Consumes: `Sequence[ExportCandidate]` from `ExportPlan.included_rows`
- Produces: long-form XLOOKUP-compatible `.xlsx` without held/excluded rows

- [ ] **Step 1: Write failing workbook tests**

Assert exact sheet/header order, stable keys, numeric accepted values, no withheld rows, no formula/macro injection from text fields, deterministic ordering and source/review references.

```python
EXPECTED_COLUMNS = (
    "school_id", "school_name", "fiscal_year", "department_key",
    "department_name", "course_name", "metric", "accepted_value",
    "source_sha256", "review_action_id", "resolution_action_id",
)
```

- [ ] **Step 2: Verify failure**

```bash
uv run pytest tests/unit/test_review_exporter.py -v
```

Expected: FAIL because the dedicated writer is absent.

- [ ] **Step 3: Implement the focused writer**

```python
def write_reviewed_rows_workbook(*, rows: Sequence[ExportCandidate], path: Path) -> Path:
    """Write one deterministic long-form data sheet to a new path and return it."""
```

Create a new workbook, write the exact columns, and populate `fiscal_year` only from non-NULL canonical `document_fiscal_year` (never `reported_fiscal_year`). Normalize untrusted text as literal strings, save only to a non-existing staged path, reopen it for structural verification, and never load/write `master.xlsx`. Add a fiscal-year-override regression where stale review JSON reports the old year but key/manifest/workbook all use the current canonical year.

- [ ] **Step 4: Run tests and commit**

```bash
uv run pytest tests/unit/test_review_exporter.py -v
git add src/eidp/excel/review_exporter.py tests/unit/test_review_exporter.py
git commit -m "feat: write reviewed XLOOKUP workbooks" -m "Goals: G1, G2, G6, G15"
```

### Task 4: Audited Staged-To-Finalized Export Bundles

**Files:**
- Modify: `src/eidp/db/audit.py`
- Create: `src/eidp/pipeline/export_bundle.py`
- Create: `tests/unit/test_export_bundle.py`
- Modify: `tests/unit/test_audit_outbox.py`

**Interfaces:**
- Consumes: `ExportPlan`, workbook writer, identity, audit writer/outbox
- Produces: `stage_export_bundle()`, `finalize_export_bundle()`, `resume_export_bundle()`

- [ ] **Step 1: Write failing lifecycle/idempotency tests**

Cover zero-included staging rejection with the unchanged preview, staged unavailable, outbox failure, deterministic retry with no duplicate audit, checksum tamper, crash before/after audit commit, crash after directory publish/before projection, crash after projection/before marker, finalized-marker-only download, export evidence holds remaining open while staged, and idempotent hold release only after finalized publication. Reject `../`, absolute/control-character/overlong export IDs, symlink roots and conflicting pre-existing paths. Include one document with an included row and a withheld sibling: finalization releases only the included row's exact hold ID and leaves the sibling hold open. An EXCLUDE missing reason/identity/audit remains withheld and its hold is never released.

```python
def test_outbox_failure_leaves_bundle_staged_and_unavailable(bundle_fixture: BundleFixture) -> None:
    staged = bundle_fixture.stage()
    bundle_fixture.fail_outbox_flush()
    with pytest.raises(ExportNotFinalizedError):
        finalize_export_bundle(bundle_fixture.session, staged=staged)
    assert staged.path.parent.name == ".staging"
    assert not bundle_fixture.public_path.exists()
```

- [ ] **Step 2: Verify failure**

```bash
uv run pytest tests/unit/test_export_bundle.py tests/unit/test_audit_outbox.py -v
```

Expected: FAIL because bundle lifecycle and deterministic audit IDs are absent.

- [ ] **Step 3: Add optional deterministic audit ID without changing defaults**

Change the audit writer to accept `action_id: str | None = None`; when absent it still uses UUID4. Export uses:

```python
def export_action_id(export_id: str) -> str:
    return str(uuid5(UUID("f42ec47d-31a0-4a7d-9a45-94cc23227504"), f"export:{export_id}:staged"))
```

`new_export_id()` returns a canonical lowercase UUID4 string. `require_export_id()` accepts only that exact canonical representation. The served page never accepts a free-form ID; it generates one for a new bundle and obtains retry IDs only from persisted staged/finalized records. Stage/resume validate before any path join, resolve output/evidence paths beneath their approved roots, reject symlink components and fail on conflicting existing content. Existing audit callers and action-ID dedup tests remain unchanged.

If the deterministic action ID already exists, validate that its action type, actor/source, export ID and staged manifest/workbook checksums exactly match the retry. A conflicting existing payload raises `ExportAuditConflictError`; it must never be treated as a successful idempotent retry.

- [ ] **Step 4: Implement manifest and lifecycle**

```python
@dataclass(frozen=True)
class StagedExportBundle:
    export_id: str
    path: Path
    workbook_sha256: str
    audit_action_id: str


def stage_export_bundle(
    session: Session, *, app_root: Path, export_id: str | None = None,
    plan: ExportPlan, identity: ResolvedIdentity, deployed_commit: str,
) -> StagedExportBundle:
    """Generate/validate ID, stage workbook/manifest, insert deterministic audit; no publish."""


def finalize_export_bundle(
    session: Session, *, staged: StagedExportBundle,
) -> Path:
    """Require exported audit row, set finalized manifest, fsync and atomically publish."""


def resume_export_bundle(session: Session, *, app_root: Path, export_id: str) -> Path | None:
    """Idempotently finish or report the one persisted lifecycle for export_id."""
```

Manifest top-level/row fields and reason enums exactly match the approved design. Never expose a path below `.staging`. The staged manifest binds every row to canonical document/review identity and its exact active hold ID/type/key; staging refuses an included or terminal-excluded row whose bound hold is not `export`. Its audit payload binds the staged-manifest/workbook SHA-256.

Finalization writes/fsyncs `export-manifest.v1.json` in staging with the staged manifest SHA, audit action ID, selected comparison run ID and workbook SHA; atomically renames the directory to `output/exports/{export_id}`; atomically writes/fsyncs the non-secret `eidp.restore-evidence-expectation.v1` projection below `evidence/runtime/exports/{export_id}.json`; and **last** atomically writes/fsyncs `FINALIZED` containing exactly `<final-manifest-sha256>\n`. Reject symlink/outside-root projection paths. The marker is the sole final commit point: a directory/projection without it is never downloadable. `resume_export_bundle()` handles crashes after directory publish or after projection/before marker by re-verifying manifest/workbook/audit/projection and only then writing the marker; any marker/projection digest conflict fails closed.

Staging never releases a hold. After verified publication/marker, finalization releases only the explicit bound hold IDs for terminal `included` and `excluded` rows; `withheld` rows' review/diff/export holds stay open. Tests include canonical old-year/non-target rows transitioning to export and closing only after their finalized excluded manifest entry. A crash after publish but before DB commit leaves holds conservatively open, and resume idempotently releases the same manifest-bound IDs after re-verifying finalized checksums. The UI validates marker content, final manifest and workbook hash before download.

- [ ] **Step 5: Run tests and commit**

```bash
uv run pytest tests/unit/test_export_bundle.py tests/unit/test_audit_outbox.py -v
uv run ruff check src/eidp/pipeline/export_bundle.py src/eidp/db/audit.py tests/unit/test_export_bundle.py
uv run mypy src/eidp/pipeline/export_bundle.py src/eidp/db/audit.py
git add src/eidp/pipeline/export_bundle.py src/eidp/db/audit.py tests/unit/test_export_bundle.py tests/unit/test_audit_outbox.py
git commit -m "feat: finalize audited export bundles" -m "Goals: G2, G9, G10, G15"
```

### Task 5: Served Export Page

**Files:**
- Create: `src/eidp/web/pages/export_bundle.py`
- Create: `src/eidp/web/pages/06_export_bundle.py`
- Create: `tests/unit/test_web_export_bundle_app.py`
- Modify: `tests/unit/test_web_write_lock_contract.py`

**Interfaces:**
- Consumes: persisted reviewed/resolved candidates, eligibility planner, bundle service, identity/Web lock
- Produces: preview counts/reasons, Generate/Resume, finalized-only download

- [ ] **Step 1: Write failing AppTests**

Assert mixed included/withheld/excluded display, reason visibility, zero-eligible error, busy lock no write, staged no download, finalized download and no master write.

- [ ] **Step 2: Verify failure**

```bash
uv run pytest tests/unit/test_web_export_bundle_app.py tests/unit/test_web_write_lock_contract.py -v
```

Expected: FAIL because page/service wiring is absent.

- [ ] **Step 3: Implement page behavior**

`render_export_bundle_page(*, identity: ResolvedIdentity, session_factory: sessionmaker[Session] = SessionLocal)` receives identity from the thin wrapper, requires the operator to select one explicit persisted comparison run, calls `load_export_candidates()`, builds a read-only preview, and performs Generate/Resume under `acquire_web_write_lock`. The selected run ID is persisted in the staged/final manifest. AppTests inject temporary SQLite sessions and never touch the developer database. The page displays every hold reason and only calls `st.download_button` for a verified finalized bundle; it never resolves identity a second time or silently substitutes a newer run.

- [ ] **Step 4: Run tests and commit**

```bash
uv run pytest tests/unit/test_web_export_bundle_app.py tests/unit/test_web_write_lock_contract.py -v
git add src/eidp/web/pages/export_bundle.py src/eidp/web/pages/06_export_bundle.py tests/unit/test_web_export_bundle_app.py tests/unit/test_web_write_lock_contract.py
git commit -m "feat: serve audited partial exports" -m "Goals: G1, G2, G6, G11, G15"
```

### Task 6: Full Served-Chain Release Gate

**Files:**
- Modify: `tests/integration/test_served_linux_web_chain.py`
- Modify: `tests/integration/test_linux_web_e2e_chain.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `tests/unit/test_ci_workflow_contract.py`
- Modify: `docs/runbooks/venus-init-and-acceptance.md`

**Interfaces:**
- Consumes: all Phase 2–4 services/pages
- Produces: exact browser-reachable v1 technical chain and ship-gate evidence; no Venus/LAN claim

- [ ] **Step 1: Extend the failing served chain through export**

The real page chain must retain exact 28 departments, 84 rows and 3 course nodes, include at least one accepted/corrected/excluded/mismatch-resolved row, produce a mixed partial manifest, withhold audit-pending data, finalize after JSONL flush, and download the workbook with only included rows.

- [ ] **Step 2: Run and close only observed chain gaps**

```bash
uv run pytest tests/integration/test_served_linux_web_chain.py tests/integration/test_linux_web_e2e_chain.py -v
```

Expected: PASS after wiring; the core test remains independent and exact.

- [ ] **Step 3: Run all quality gates**

```bash
uv run ruff check .
uv run --with bandit bandit -q --severity-level high -r src/eidp scripts
uv run mypy src
uv run pytest --cov=src/eidp --cov-report=term --cov-fail-under=80
```

Expected: all pass.

- [ ] **Step 4: Update ship gate, truth labels and commit**

Add the served full-chain test to `Ship gate contract`. Update runbook PENDING labels only for behavior proven by the real page test; keep Venus, ICT, off-host restore and PI gates PENDING.

```bash
git add tests/integration .github/workflows/ci.yml tests/unit/test_ci_workflow_contract.py docs/runbooks/venus-init-and-acceptance.md
git commit -m "test: gate the served export workflow" -m "Goals: G1, G2, G3, G6, G10, G15"
```

After explicit external-write authorization:

```bash
git push -u origin feat/linux-web-v1-phase4-partial-export
gh pr create --base main --head feat/linux-web-v1-phase4-partial-export --title "feat: finalize audited partial exports" --body $'Summary:\n- assemble and classify authoritative export candidates\n- publish finalized workbook and complete disposition manifest\n\nVerification:\n- full local quality gates passed\n\nGoals: G1, G2, G3, G6, G10, G15'
gh pr checks feat/linux-web-v1-phase4-partial-export --watch --interval 10
```

Require both named checks green and explicit owner merge authorization, then:

```bash
gh pr merge feat/linux-web-v1-phase4-partial-export --merge --delete-branch
git fetch --prune origin
git switch main
git merge --ff-only origin/main
test "$(git rev-list --left-right --count origin/main...main | tr '\t' ' ')" = "0 0"
git status --short --branch
```

A partial export proves operation, not `READY`; high-risk mismatches in the accepted scope must be zero or permanently excluded with audited reasons. Phase 5 starts only from this clean merged `origin/main`.

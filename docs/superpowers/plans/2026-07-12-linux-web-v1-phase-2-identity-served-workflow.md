# Linux/Web v1 Phase 2 Identity And Served Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing Streamlit multipage shell into a recoverable intake-to-double-check workflow with fail-closed identity and DB-authoritative audited human decisions.

**Architecture:** Request identity is resolved once at every Streamlit entrypoint and passed as a typed value; free-form reviewer identity is removed. Extraction remains a reproducible core operation reached through a served bridge, while review and mismatch decisions move from mutable JSON to append-only SQLite rows committed with `manual_action_log`; JSON becomes a projection only.

**Tech Stack:** Streamlit 1.56, Python 3.12, Pydantic Settings, SQLAlchemy, Alembic, SQLite, pytest, Streamlit AppTest

## Global Constraints

- Execute only after the Phase 1 PR is merged and local `main` is reconciled to protected `origin/main`; do not run code phases in parallel.
- Keep Streamlit/SQLite; do not introduce React, FastAPI, PostgreSQL, a queue service, or role-based workflow.
- Trusted mode validates `X-Auth-User` and `X-EIDP-Proxy-Secret`; invalid/missing values reject the entire app request except Streamlit liveness.
- Fallback ignores request identity headers, uses one configured actor, and retains the explicit Venus-local-account trust limitation.
- Historical audit rows are never updated; NULL `identity_source` reads as `legacy_unspecified`.
- Business decision and audit row commit in one DB transaction. JSON cannot be the authoritative decision store.
- `data/master.xlsx` remains read-only; external comparison never overwrites EIDP without a reasoned human decision.
- Every Web write remains inside `acquire_web_write_lock()`.

Before Task 1:

```bash
git fetch --prune origin
git switch -c feat/linux-web-v1-phase2-served-audit origin/main
```

---

### Task 1: Identity Domain And Additive Audit Schema

**Files:**
- Create: `src/eidp/identity.py`
- Modify: `src/eidp/config.py`
- Modify: `src/eidp/db/models.py`
- Modify: `src/eidp/db/audit.py`
- Modify: `src/eidp/db/audit_outbox.py`
- Modify: `src/eidp/db/sqlite_bootstrap.py`
- Create: `migrations/versions/8c9d0e1f2a3b_add_audit_identity_source.py`
- Create: `tests/unit/test_identity.py`
- Modify: `tests/unit/test_audit_outbox.py`
- Modify: `tests/unit/test_sqlite_bootstrap.py`

**Interfaces:**
- Consumes: current `ManualActionLog`, centralized audit writer and outbox
- Produces: `IdentitySource`, `ResolvedIdentity`, identity settings, nullable audit column propagated to JSONL

- [ ] **Step 1: Write failing domain, legacy-upgrade and outbox tests**

```python
def test_legacy_null_identity_source_exports_as_legacy_unspecified(session: Session, tmp_path: Path) -> None:
    row = ManualActionLog(
        action_id=str(uuid4()), actor="operator", action_type="legacy",
        target_table="document", identity_source=None,
    )
    session.add(row)
    session.commit()
    flush_audit_outbox(session, jsonl_path=tmp_path / "manual-actions.jsonl")
    payload = json.loads((tmp_path / "manual-actions.jsonl").read_text().splitlines()[0])
    assert payload["identity_source"] == "legacy_unspecified"
```

Also prove SQLite upgrade adds the nullable column without UPDATE/table rebuild, action-ID dedup is unchanged, and the writer persists all four enum values.

- [ ] **Step 2: Verify failure**

```bash
uv run pytest tests/unit/test_identity.py tests/unit/test_audit_outbox.py tests/unit/test_sqlite_bootstrap.py -v
```

Expected: FAIL because identity domain/column do not exist.

- [ ] **Step 3: Implement typed identity and settings**

```python
class IdentitySource(StrEnum):
    TRUSTED_PROXY = "trusted_proxy"
    CONFIGURED_FALLBACK = "configured_fallback"
    SYSTEM = "system"
    LEGACY_UNSPECIFIED = "legacy_unspecified"


@dataclass(frozen=True)
class ResolvedIdentity:
    actor: str
    source: IdentitySource


SYSTEM_IDENTITY = ResolvedIdentity(actor="system", source=IdentitySource.SYSTEM)
LEGACY_OPERATOR_IDENTITY = ResolvedIdentity(
    actor="operator", source=IdentitySource.LEGACY_UNSPECIFIED,
)
```

Add settings `identity_mode`, `fallback_actor`, and secret-valued `proxy_shared_secret`; fix header names in code rather than making arbitrary headers configurable. Preserve current callers with this compatible audit boundary:

```python
def _resolve_audit_identity(
    *, identity: ResolvedIdentity | None, actor: str | None,
) -> ResolvedIdentity:
    if identity is not None and actor is not None:
        raise ValueError("pass identity or actor, not both")
    if identity is not None:
        return identity
    return ResolvedIdentity(actor or "operator", IdentitySource.LEGACY_UNSPECIFIED)
```

`log_manual_action` accepts both optional keywords, uses the resolver, and writes actor/source. All new Web services pass `identity`; existing `actor=` callers remain valid and are labeled `legacy_unspecified` until their domain is explicitly classified. Known background callers touched in this phase pass `SYSTEM_IDENTITY`. Outbox coalesces historical NULL at read/export time.

- [ ] **Step 4: Implement additive upgrade paths**

Revision `8c9d0e1f2a3b` has `down_revision = "7b8c9d0e1f2a"` and adds only the nullable column. SQLite bootstrap detects the column with `PRAGMA table_info(manual_action_log)` and executes exactly `ALTER TABLE manual_action_log ADD COLUMN identity_source VARCHAR(32)` when absent; it never runs an UPDATE or rebuild.

- [ ] **Step 5: Run tests, type checks and commit**

```bash
uv run pytest tests/unit/test_identity.py tests/unit/test_audit_outbox.py tests/unit/test_sqlite_bootstrap.py -v
uv run ruff check src/eidp/identity.py src/eidp/config.py src/eidp/db tests/unit/test_identity.py
uv run mypy src/eidp/identity.py src/eidp/config.py src/eidp/db
git add src/eidp/identity.py src/eidp/config.py src/eidp/db migrations/versions/8c9d0e1f2a3b_add_audit_identity_source.py tests/unit/test_identity.py tests/unit/test_audit_outbox.py tests/unit/test_sqlite_bootstrap.py
git commit -m "feat: record audit identity provenance" -m "Goals: G2, G8, G10, G13"
```

### Task 2: Fail-Closed Streamlit Identity Bootstrap

**Files:**
- Create: `src/eidp/web/identity.py`
- Create: `src/eidp/web/bootstrap.py`
- Modify: `src/eidp/web/app.py`
- Modify: `src/eidp/web/pages/01_pdf_intake.py`
- Modify: `src/eidp/web/pages/02_extraction_queue.py`
- Modify: `src/eidp/web/pages/03_extraction_review.py`
- Modify: `src/eidp/web/pages/04_review_diff.py`
- Modify: `src/eidp/web/pages/05_double_check.py`
- Modify: `src/eidp/web/pages/pdf_intake.py`
- Modify: `src/eidp/web/pages/extraction_queue.py`
- Modify: `src/eidp/web/pages/extraction_review.py`
- Modify: `src/eidp/web/pages/review_diff.py`
- Modify: `src/eidp/web/pages/double_check.py`
- Create: `tests/unit/test_web_identity.py`
- Create: `tests/unit/test_web_bootstrap_app.py`
- Modify: `tests/unit/test_web_pdf_intake_app.py`

**Interfaces:**
- Consumes: `ResolvedIdentity`, settings and `st.context.headers`
- Produces: `validate_identity_configuration()`, `resolve_request_identity()`, `bootstrap_web_request()`

- [ ] **Step 1: Write failing identity tests**

```python
def test_fallback_ignores_spoofed_headers() -> None:
    config = identity_settings(mode="configured_fallback", fallback_actor="pilot-operator")
    identity = resolve_request_identity(
        headers={"X-Auth-User": "attacker", "X-EIDP-Proxy-Secret": "spoof"},
        config=config,
    )
    assert identity == ResolvedIdentity("pilot-operator", IdentitySource.CONFIGURED_FALLBACK)


def test_invalid_trusted_secret_rejects_entire_request() -> None:
    config = identity_settings(mode="trusted_proxy", proxy_shared_secret="expected")
    with pytest.raises(IdentityRejectedError):
        resolve_request_identity(
            headers={"X-Auth-User": "user-1", "X-EIDP-Proxy-Secret": "wrong"},
            config=config,
        )
```

Also test missing trusted startup config, valid constant-time path, blank/oversized actor, no secret in exception/log text, and direct multipage entry cannot bypass bootstrap.

- [ ] **Step 2: Verify failure**

```bash
uv run pytest tests/unit/test_web_identity.py tests/unit/test_web_bootstrap_app.py -v
```

Expected: FAIL because the bootstrap does not exist.

- [ ] **Step 3: Implement resolver and bootstrap**

```python
def validate_identity_configuration(config: Settings) -> None:
    if config.identity_mode == "trusted_proxy" and not config.proxy_shared_secret.get_secret_value():
        raise IdentityConfigurationError("trusted_proxy requires proxy shared secret")


def resolve_request_identity(*, headers: Mapping[str, str], config: Settings) -> ResolvedIdentity:
    if config.identity_mode == "configured_fallback":
        return ResolvedIdentity(config.fallback_actor.strip(), IdentitySource.CONFIGURED_FALLBACK)
    supplied = headers.get("X-EIDP-Proxy-Secret", "")
    expected = config.proxy_shared_secret.get_secret_value()
    actor = headers.get("X-Auth-User", "").strip()
    if not actor or not secrets.compare_digest(supplied, expected):
        raise IdentityRejectedError("trusted proxy identity rejected")
    return ResolvedIdentity(actor, IdentitySource.TRUSTED_PROXY)


def bootstrap_web_request() -> ResolvedIdentity:
    validate_identity_configuration(settings)
    return resolve_request_identity(headers=st.context.headers, config=settings)
```

Every app/page wrapper calls bootstrap before rendering and passes the returned identity down. In this task, change all five body render signatures to require `identity: ResolvedIdentity`; intake/queue/review/diff/double-check may temporarily leave it unused, but no wrapper discards or re-resolves it. Later tasks add behavior through the same stable signatures. Render one generic rejection page and stop execution; do not show a read-only app.

- [ ] **Step 4: Run AppTest and commit**

```bash
uv run pytest tests/unit/test_web_identity.py tests/unit/test_web_bootstrap_app.py tests/unit/test_web_pdf_intake_app.py -v
uv run ruff check src/eidp/web tests/unit/test_web_identity.py tests/unit/test_web_bootstrap_app.py
uv run mypy src/eidp/web
git add src/eidp/web src/eidp/config.py tests/unit/test_web_identity.py tests/unit/test_web_bootstrap_app.py tests/unit/test_web_pdf_intake_app.py
git commit -m "security: require trusted Web request identity" -m "Goals: G2, G5, G13"
```

### Task 3: Served Extraction Run And Retry

**Files:**
- Create: `src/eidp/web/services/__init__.py`
- Create: `src/eidp/web/services/extraction.py`
- Modify: `src/eidp/web/pages/extraction_queue.py`
- Create: `tests/unit/test_web_extraction_queue_app.py`
- Modify: `tests/unit/test_web_write_lock_contract.py`

**Interfaces:**
- Consumes: `process_intake_record()`, `extract_table_grid_records`, `ResolvedIdentity`, Web lock
- Produces: `run_extraction()` and visible Run/Retry actions for TEXT items only

- [ ] **Step 1: Write failing AppTests**

Test that Run reaches the real core, persists evidence rows, failed extraction retains the source/error and exposes Retry, image lane has no Run action, and lock busy changes no queue state.

```python
def test_text_queue_run_reaches_core_and_persists_evidence(app_test: QueueAppFixture) -> None:
    app = app_test.with_text_pdf().run()
    app.button(key="run_extraction").click().run()
    item = load_extraction_queue(app_test.intake_root)[0]
    assert item.status == ExtractionStatus.EXTRACTION_COMPLETED
    assert load_extracted_rows(app_test.intake_root, item.intake_record_id)
```

- [ ] **Step 2: Verify failure**

```bash
uv run pytest tests/unit/test_web_extraction_queue_app.py -v
```

Expected: FAIL because no Run/Retry control or service exists.

- [ ] **Step 3: Implement the served bridge**

```python
def run_extraction(
    *, intake_root: Path, intake_record_id: str, identity: ResolvedIdentity,
    extractor_func: ExtractorFunc = extract_table_grid_records,
) -> ExtractionQueueItem:
    item = process_intake_record(
        intake_root=intake_root,
        intake_record_id=intake_record_id,
        extractor_func=extractor_func,
    )
    return item
```

The page acquires the Web lock before calling the service, shows Run only for pending TEXT, Retry only for failed TEXT, and renders the persisted failure reason. Emit a structured `served_extraction_requested` event containing actor and identity-source enum (never headers/secrets) and test it; the derived extraction is not misrepresented as an audited human decision.

- [ ] **Step 4: Run tests and commit**

```bash
uv run pytest tests/unit/test_web_extraction_queue_app.py tests/unit/test_extraction_queue.py tests/unit/test_web_write_lock_contract.py -v
git add src/eidp/web/services src/eidp/web/pages/extraction_queue.py tests/unit/test_web_extraction_queue_app.py tests/unit/test_web_write_lock_contract.py
git commit -m "feat: run extraction from the served queue" -m "Goals: G1, G5, G6, G11"
```

### Task 4: DB-Authoritative Review Decisions And Audit

**Files:**
- Modify: `src/eidp/db/models.py`
- Create: `src/eidp/pipeline/review_decision.py`
- Modify: `src/eidp/pipeline/extraction_review.py`
- Modify: `src/eidp/web/pages/extraction_review.py`
- Create: `migrations/versions/9d0e1f2a3b4c_add_extraction_review_decisions.py`
- Create: `tests/unit/test_review_decision.py`
- Modify: `tests/unit/test_extraction_review.py`
- Create: `tests/unit/test_web_extraction_review_app.py`
- Modify: `tests/integration/test_linux_web_e2e_chain.py`

**Interfaces:**
- Consumes: immutable extracted/base review records, Session, identity and audit writer
- Produces: append-only `ExtractionReviewDecision`, `apply_review_decision()`, DB-overlaid review state

- [ ] **Step 1: Write failing atomicity and identity tests**

```python
def test_review_decision_and_audit_commit_together(session: Session, record: ExtractionReviewRecord) -> None:
    result = apply_review_decision(
        session,
        record=record,
        decision=ReviewDecision.ACCEPT,
        corrected_value=None,
        note="source checked",
        identity=ResolvedIdentity("reviewer-1", IdentitySource.TRUSTED_PROXY),
    )
    session.commit()
    assert result.audit_action_id
    assert session.scalar(select(ManualActionLog).where(ManualActionLog.action_id == result.audit_action_id))
```

Also inject audit insert failure and prove no decision commits; lock busy writes neither; UI has no `reviewed_by` text field; JSON base data is not rewritten by decisions. `EXCLUDE` requires a trimmed 1–500 character business reason in both service and UI; blank/oversized reasons commit neither decision nor audit.

- [ ] **Step 2: Verify failure**

```bash
uv run pytest tests/unit/test_review_decision.py tests/unit/test_web_extraction_review_app.py -v
```

Expected: FAIL because the DB decision model/service do not exist.

- [ ] **Step 3: Add the append-only decision model and migration**

```python
class ReviewDecision(StrEnum):
    ACCEPT = "accept"
    CORRECT = "correct"
    NEEDS_REVIEW = "needs_review"
    EXCLUDE = "exclude"


class ExtractionReviewDecision(Base):
    __tablename__ = "extraction_review_decision"
    id: Mapped[int] = mapped_column(primary_key=True)
    decision_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    review_id: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    revision: Mapped[int] = mapped_column(nullable=False)
    decision: Mapped[str] = mapped_column(String(24), nullable=False)
    corrected_value: Mapped[int | None]
    note: Mapped[str | None] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(50), nullable=False)
    identity_source: Mapped[str] = mapped_column(String(32), nullable=False)
    audit_action_id: Mapped[str] = mapped_column(
        ForeignKey("manual_action_log.action_id"), unique=True, nullable=False,
    )
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
```

Enforce `(review_id, revision)` uniqueness. Do not update prior rows.
Add a cross-dialect CHECK equivalent to `decision != 'exclude' OR length(trim(coalesce(note, ''))) BETWEEN 1 AND 500`, plus the same validation in the service for a clear error. The matching audit payload includes the approved exclusion reason.
Revision `9d0e1f2a3b4c` has `down_revision = "8c9d0e1f2a3b"`.

- [ ] **Step 4: Implement one transaction service and DB overlay**

```python
def apply_review_decision(
    session: Session, *, record: ExtractionReviewRecord,
    decision: ReviewDecision, corrected_value: int | None,
    note: str | None, identity: ResolvedIdentity,
) -> ExtractionReviewDecision:
    """Insert next revision and matching ManualActionLog without committing."""


def overlay_review_decisions(
    session: Session, records: Sequence[ExtractionReviewRecord],
) -> list[ExtractionReviewRecord]:
    """Return base records overlaid with each review_id's highest decision revision."""
```

Change `accept_review_record`, `correct_review_record`, `mark_review_needs_review`, and `exclude_review_record` to require `session` and `identity` and delegate to this DB service; they must no longer rewrite decision fields in JSON. `_write_review_record` remains private to immutable base-candidate projection creation. Migrate unit tests, the core E2E and all Web callers so no public JSON decision mutator remains.

`render_extraction_review_page` accepts `identity: ResolvedIdentity` and injectable `session_factory: sessionmaker[Session]`; the wrapper supplies `SessionLocal`, while AppTests use temporary SQLite. The page calls the service inside the shared lock/session transaction, fills `reviewed_at` from `decided_at`, and flushes audit outbox only after commit. Remove free-form `reviewed_by`.

- [ ] **Step 5: Run tests and commit**

```bash
uv run pytest tests/unit/test_review_decision.py tests/unit/test_extraction_review.py tests/unit/test_web_extraction_review_app.py tests/unit/test_audit_outbox.py -v
uv run ruff check src/eidp/pipeline/review_decision.py src/eidp/web/pages/extraction_review.py tests/unit/test_review_decision.py
uv run mypy src/eidp/pipeline/review_decision.py src/eidp/web/pages/extraction_review.py
git add src/eidp/db/models.py src/eidp/pipeline/review_decision.py src/eidp/pipeline/extraction_review.py src/eidp/web/pages/extraction_review.py migrations/versions/9d0e1f2a3b4c_add_extraction_review_decisions.py tests/unit/test_review_decision.py tests/unit/test_extraction_review.py tests/unit/test_web_extraction_review_app.py tests/integration/test_linux_web_e2e_chain.py
git commit -m "feat: persist audited extraction review decisions" -m "Goals: G2, G6, G10, G11, G13"
```

### Task 5: Persistent External Comparison And Human Resolution

**Files:**
- Modify: `src/eidp/db/models.py`
- Create: `src/eidp/pipeline/double_check_resolution.py`
- Modify: `src/eidp/web/pages/double_check.py`
- Create: `migrations/versions/ae1f2a3b4c5d_add_double_check_resolutions.py`
- Create: `tests/unit/test_double_check_resolution.py`
- Create: `tests/unit/test_web_double_check_app.py`

**Interfaces:**
- Consumes: reviewed DB-overlaid rows, immutable uploaded external evidence, comparison result, identity/audit
- Produces: `ExternalComparisonRun`, append-only `DoubleCheckResolution`, `resolve_double_check()`

- [ ] **Step 1: Write failing persistence and overwrite-boundary tests**

Test uploaded evidence hash/run persistence, unresolved mismatch after restart, reason required, external value cannot directly overwrite, decision+audit atomicity, and latest append-only resolution overlay.

```python
def test_external_value_never_overwrites_without_reasoned_resolution(session: Session, mismatch: MismatchFixture) -> None:
    with pytest.raises(DoubleCheckResolutionError, match="reason is required"):
        resolve_double_check(
            session,
            comparison_result_id=mismatch.comparison_result_id,
            outcome=ResolutionOutcome.ACCEPT_EXTERNAL,
            corrected_value=mismatch.external_value,
            reason="",
            identity=mismatch.identity,
        )
```

- [ ] **Step 2: Verify failure**

```bash
uv run pytest tests/unit/test_double_check_resolution.py tests/unit/test_web_double_check_app.py -v
```

Expected: FAIL because comparison runs/resolutions are transient.

- [ ] **Step 3: Implement models and service**

Create `ExternalComparisonRun` with run ID, source system, full file hash, original filename, actor/source and UTC time. Store immutable external bytes/report under a full-hash path below `data/web-intake/external`.

Create immutable `ExternalComparisonResult` rows for every computed row with run ID, stable row key, review ID/decision revision/action ID, external source-row key/value/file hash, EIDP value, computed status and mismatch reason. Create `DoubleCheckResolution` with resolution ID, comparison-result ID FK, outcome, corrected value, reason, actor/source, audit action ID FK, revision and decision time. Unique `(run_id, row_key)` snapshots make later review changes create a new run rather than mutate old evidence.
Revision `ae1f2a3b4c5d` has `down_revision = "9d0e1f2a3b4c"`.

```python
class ResolutionOutcome(StrEnum):
    ACCEPT_EIDP = "accept_eidp"
    ACCEPT_EXTERNAL = "accept_external"
    CORRECT = "correct"
    EXCLUDE = "exclude"


def resolve_double_check(
    session: Session, *, comparison_result_id: int,
    outcome: ResolutionOutcome, corrected_value: int | None,
    reason: str, identity: ResolvedIdentity,
) -> DoubleCheckResolution:
    """Insert one append-only resolution and matching audit row without committing."""
```

Persist immutable `effective_value` on `DoubleCheckResolution` and derive it from the exact snapshot:

- `ACCEPT_EIDP`: `corrected_value` must be NULL; `effective_value = ExternalComparisonResult.eidp_value`.
- `ACCEPT_EXTERNAL`: `corrected_value` is required and must equal the snapshot external value; that becomes `effective_value`.
- `CORRECT`: a non-negative `corrected_value` is required and becomes `effective_value`.
- `EXCLUDE`: `corrected_value/effective_value` are NULL and the nonblank bounded reason is the terminal exclusion reason.

Every outcome requires a trimmed 1–500 character reason and matching audit payload. Invalid combinations write neither resolution nor audit. `render_double_check_page` accepts typed identity and an injectable session factory. The page renders persisted snapshot rows, requires explicit outcome/reason/value as applicable, commits under the Web lock, and uses the stored run after restart. External values never overwrite a different review revision silently. Parameterize service/UI tests for all four outcome/value contracts and audit projection.

- [ ] **Step 4: Run tests and commit**

```bash
uv run pytest tests/unit/test_double_check_resolution.py tests/unit/test_double_check_compare.py tests/unit/test_web_double_check_app.py -v
git add src/eidp/db/models.py src/eidp/pipeline/double_check_resolution.py src/eidp/web/pages/double_check.py migrations/versions/ae1f2a3b4c5d_add_double_check_resolutions.py tests/unit/test_double_check_resolution.py tests/unit/test_web_double_check_app.py
git commit -m "feat: persist audited double-check resolutions" -m "Goals: G2, G6, G10, G11"
```

### Task 6: Served Workflow Integration Gate

**Files:**
- Create: `tests/integration/test_served_linux_web_chain.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `tests/unit/test_ci_workflow_contract.py`
- Modify: `docs/runbooks/venus-init-and-acceptance.md`

**Interfaces:**
- Consumes: Tasks 1–5
- Produces: browser-reachable intake -> extraction -> review -> diff -> persisted double-check flow; export remains Phase 4

- [ ] **Step 1: Write the failing served-chain AppTest**

Drive the actual page entrypoints rather than calling pipeline functions directly. Assert exact 28 departments, 84 rows and 3 independent course nodes; accept/correct/exclude decisions and mismatch resolution survive a new AppTest session and each decision has DB+JSONL audit evidence.

- [ ] **Step 2: Verify failure, then close page wiring gaps**

```bash
uv run pytest tests/integration/test_served_linux_web_chain.py -v
```

Expected before final wiring: FAIL at the first served page transition that is still disconnected. Make only the page/service wiring needed for the test; do not add export here.

- [ ] **Step 3: Add the served-chain test to ship gate and run all gates**

```bash
uv run pytest tests/integration/test_served_linux_web_chain.py tests/integration/test_linux_web_e2e_chain.py -v
uv run ruff check .
uv run --with bandit bandit -q --severity-level high -r src/eidp scripts
uv run mypy src
uv run pytest --cov=src/eidp --cov-report=term --cov-fail-under=80
```

Expected: all pass. The original core E2E remains; the new test proves served reachability.

- [ ] **Step 4: Commit and open the Phase 2 PR**

```bash
git add .github/workflows/ci.yml tests/unit/test_ci_workflow_contract.py tests/integration/test_served_linux_web_chain.py docs/runbooks/venus-init-and-acceptance.md src/eidp
git commit -m "test: gate the served review workflow" -m "Goals: G1, G2, G6, G10, G11, G13"
```

After explicit authorization for both the remote branch push and GitHub PR creation:

```bash
git push -u origin feat/linux-web-v1-phase2-served-audit
gh pr create --base main --head feat/linux-web-v1-phase2-served-audit --title "feat: serve audited Linux Web workflow" --body $'Summary:\n- add fail-closed request identity\n- connect served extraction, review and persisted double-check\n\nVerification:\n- full local quality gates passed\n\nGoals: G1, G2, G6, G10, G11, G13'
gh pr checks feat/linux-web-v1-phase2-served-audit --watch --interval 10
```

Require both named checks green and explicit owner merge authorization, then:

```bash
gh pr merge feat/linux-web-v1-phase2-served-audit --merge --delete-branch
git fetch --prune origin
git switch main
git merge --ff-only origin/main
test "$(git rev-list --left-right --count origin/main...main | tr '\t' ' ')" = "0 0"
git status --short --branch
```

Keep export/CAS claims PENDING. Phase 3 branches only from this clean merged `origin/main`.

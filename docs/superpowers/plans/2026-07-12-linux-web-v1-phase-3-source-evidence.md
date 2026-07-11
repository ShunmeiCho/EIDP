# Linux/Web v1 Phase 3 Source Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace hash-prefix file storage and split deduplication with one immutable full-SHA source registry, durable intake provenance, live-reference retention and operator-confirmed cleanup backed by off-host evidence.

**Architecture:** A focused source store owns immutable blobs; `Document.file_hash UNIQUE` is the only content-registration decision. Append-only intake events preserve every claim/upload, current DB rows define liveness, and cleanup is a locked/revalidated state machine that removes only hot storage after a verified backup receipt.

**Tech Stack:** Python 3.12, pathlib/os stdlib, SQLAlchemy, Alembic batch migration, SQLite, pytest

## Global Constraints

- Execute after Phase 2 identity/audit interfaces are merged; backup receipt integration consumes Phase 1 packages.
- Canonical uploaded `Document.file_hash` is a validated non-NULL 64-hex SHA-256.
- Blob path is `data/source-pdfs/sha256/{digest[:2]}/{digest}.pdf`; original name/year/school never determines storage identity.
- Existing blobs are never replaced. Incoming inconsistency is quarantined; canonical evidence is marked suspect and extraction stops.
- Same-school/same-hash reuses one `Document`; cross-school claim is append-only review evidence and never silently reassigns ownership.
- Same school/source URL may produce new bytes over time. Remove URL uniqueness and keep a non-unique lookup index.
- Fiscal-year corrections preserve the existing revision/demotion contract: create a new revision, demote the prior `is_current` row, and audit collateral demotion; never replace these tables with in-place updates.
- Current `DepartmentYearly`, `SchoolYearStatus`, and `SupportRecipient` references always block cleanup.
- Retention anchor begins when the last live reference closes; reactivation clears it. Default is 365 days.
- Cleanup requires global lock, fresh revalidation, explicit manifest confirmation, finalized backup and verified off-host receipt.
- Cleanup is limited to verified source-PDF/CAS and tracked legacy-copy items. Never delete `data/eidp.sqlite3`, `data/audit/manual-actions.jsonl`, or `data/master.xlsx`.

Before Task 1:

```bash
git fetch --prune origin
git switch -c feat/linux-web-v1-phase3-source-evidence origin/main
```

---

### Task 1: Immutable Full-SHA Source Store

**Files:**
- Create: `src/eidp/pdf/source_store.py`
- Create: `tests/unit/test_source_store.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: raw PDF bytes and project `data_dir`
- Produces: `StoredSourcePdf`, `store_source_pdf()`, `verify_source_pdf()`

- [ ] **Step 1: Write failing no-overwrite and boundary tests**

```python
def test_existing_wrong_blob_is_not_overwritten(tmp_path: Path) -> None:
    payload = b"%PDF-1.7\ncanonical"
    digest = hashlib.sha256(payload).hexdigest()
    target = tmp_path / "source-pdfs" / "sha256" / digest[:2] / f"{digest}.pdf"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"%PDF-1.7\nwrong")
    with pytest.raises(SourceBlobConflictError) as caught:
        store_source_pdf(data_dir=tmp_path, pdf_bytes=payload)
    assert target.read_bytes() == b"%PDF-1.7\nwrong"
    assert UUID(caught.value.incident_id)
    assert caught.value.quarantine_path.is_relative_to(tmp_path / "source-pdfs" / "quarantine")
    assert caught.value.quarantine_path.exists()
```

Also test exact 64-hex path, same 12-hex prefix stays distinct, identical reuse, concurrent create-if-absent, symlink/path escape refusal and extraction-time digest verification.

- [ ] **Step 2: Verify failure**

```bash
uv run pytest tests/unit/test_source_store.py -v
```

Expected: FAIL because `source_store` does not exist.

- [ ] **Step 3: Implement the source-store interfaces**

```python
@dataclass(frozen=True)
class StoredSourcePdf:
    sha256: str
    relative_path: str
    byte_size: int
    reused: bool


def source_pdf_relative_path(sha256: str) -> Path:
    digest = _require_sha256(sha256)
    return Path("source-pdfs") / "sha256" / digest[:2] / f"{digest}.pdf"


def store_source_pdf(*, data_dir: Path, pdf_bytes: bytes) -> StoredSourcePdf:
    """Create a same-filesystem temp and publish without replacing an existing target."""


def verify_source_pdf(
    *, data_dir: Path, expected_sha256: str, expected_size: int,
    expected_bytes: bytes | None = None,
) -> Path:
    """Rebuild the canonical path, reject escapes/symlinks/mismatch, and return it."""
```

`store_source_pdf()` generates the incident UUID internally; caller-controlled text is never a quarantine path component. `SourceBlobConflictError` exposes only the generated incident ID and safe quarantine path. Use exclusive creation/link semantics; on an existing target verify before reuse. `verify_source_pdf()` derives the only allowed path from `data_dir + expected_sha256` and never accepts an arbitrary path. Never call `Path.replace()` on a canonical target.
Add `/data/source-pdfs/` to `.gitignore`; source evidence is runtime data, never Git content.

- [ ] **Step 4: Run tests and commit**

```bash
uv run pytest tests/unit/test_source_store.py -v
uv run ruff check src/eidp/pdf/source_store.py tests/unit/test_source_store.py
uv run mypy src/eidp/pdf/source_store.py
git add .gitignore src/eidp/pdf/source_store.py tests/unit/test_source_store.py
git commit -m "feat: add immutable source PDF storage" -m "Goals: G2, G3, G9, G13"
```

### Task 2: Canonical Document Registry And Intake Events

**Files:**
- Modify: `src/eidp/db/models.py`
- Modify: `src/eidp/db/sqlite_bootstrap.py`
- Create: `src/eidp/pipeline/document_intake.py`
- Modify: `src/eidp/cli.py`
- Modify: `src/eidp/ops/runtime_controller.py`
- Create: `migrations/versions/bf2a3b4c5d6e_add_document_intake_registry.py`
- Create: `tests/unit/test_document_intake.py`
- Modify: `tests/unit/test_sqlite_bootstrap.py`
- Modify: `tests/unit/test_linux_runtime_controller.py`

**Interfaces:**
- Consumes: source store, resolved integer `School.id`, `PdfIntakeMetadata`, `ResolvedIdentity`
- Produces: intake events/resolutions, blob state, evidence holds, `register_document_intake()` and `resolve_cross_school_intake()`

- [ ] **Step 1: Write failing registry, race and schema-upgrade tests**

Test new content, same-school duplicate, cross-school review, missing canonical school rejection, concurrent insert race, immutable event, pre-registration rejected event with NULL document ID, same school/URL accepting two different hashes, and a canonical conflict recording `suspect` blob state that blocks future use. Assert hold policy exactly: `REGISTERED` opens one `intake`; `DUPLICATE_SAME_SCHOOL` opens none and reports the existing active workflow; `CROSS_SCHOOL_REVIEW` opens one `cross_school`; `REJECTED` opens no document hold. Test audited cross-school accept/reject, reason required, append-only decision, and idempotent retry.

```python
def test_same_school_url_can_register_new_bytes(session: Session, school: School, data_dir: Path) -> None:
    first = register_document_intake(
        session, school_id=school.id, metadata=metadata(url="https://school/doc.pdf"),
        pdf_bytes=b"%PDF-1.7\nfirst", identity=IDENTITY, data_dir=data_dir,
    )
    session.commit()
    second = register_document_intake(
        session, school_id=school.id, metadata=metadata(url="https://school/doc.pdf"),
        pdf_bytes=b"%PDF-1.7\nsecond", identity=IDENTITY, data_dir=data_dir,
    )
    assert first.document_id != second.document_id
```

- [ ] **Step 2: Verify failure**

```bash
uv run pytest tests/unit/test_document_intake.py tests/unit/test_sqlite_bootstrap.py -v
```

Expected: FAIL because the registry/event and URL schema change are absent.

- [ ] **Step 3: Add models and service**

```python
class IntakeDisposition(StrEnum):
    REGISTERED = "registered"
    DUPLICATE_SAME_SCHOOL = "duplicate_same_school"
    CROSS_SCHOOL_REVIEW = "cross_school_review"
    REJECTED = "rejected"


@dataclass(frozen=True)
class DocumentIntakeResult:
    document_id: int | None
    event_id: str
    disposition: IntakeDisposition
    sha256: str
    relative_path: str | None


def register_document_intake(
    session: Session, *, school_id: int | None, metadata: PdfIntakeMetadata,
    pdf_bytes: bytes, identity: ResolvedIdentity, data_dir: Path,
) -> DocumentIntakeResult:
    """Store/reuse content, register/reuse Document, append immutable intake event; no commit."""


def resolve_cross_school_intake(
    session: Session, *, event_id: str, outcome: CrossSchoolOutcome,
    reason: str, identity: ResolvedIdentity,
) -> CrossSchoolIntakeResolution:
    """Append an audited claim decision and transition its exact evidence hold; no commit."""
```

`DocumentIntakeEvent` stores the approved fields from the design; `document_id` is nullable only for pre-registration rejection. `SourcePdfIncident` stores quarantine metadata without secret content.
Add `SourcePdfBlobStatus` with exact values `active`, `suspect`, `cleanup_applying`, and `offhost_only`, plus a database value constraint and legal-transition tests. `SourcePdfBlobState` is keyed by full SHA-256 with nullable `document_id`, status, latest incident ID and UTC update time. Intake uses only active/suspect; Task 5 consumes the already-reserved cleanup state. `register_document_intake()` catches `SourceBlobConflictError`, appends the incident/event and marks the digest `suspect` in the same transaction; it never returns a queueable document. Tests reject unknown status and illegal transitions.

Add durable workflow liveness through `DocumentEvidenceHold(document_id, hold_type, source_key, opened_at, released_at)`. Release sets `released_at` once. The migration installs tested SQLite/PostgreSQL UPDATE triggers that reject changes to identity/opened fields, reject non-NULL -> NULL reopening, and allow only the first NULL -> UTC timestamp release, plus BEFORE DELETE triggers that always reject hold deletion. Direct-SQL adversarial tests exercise UPDATE, reopen and DELETE.

Because Linux SQLite uses `create_all()` then stamps rather than running Alembic upgrades, implement `ensure_sqlite_document_evidence_hold_triggers(engine)`. `bootstrap_sqlite()` calls it after table creation and before stamping. Test fresh bootstrap, an existing DB missing triggers, idempotent rerun, and PostgreSQL migration DDL separately. `REGISTERED` opens `intake:event:{event_id}`. A same-school duplicate reuses the existing document/workflow and opens no event hold. A cross-school claim opens `cross_school:event:{event_id}` and cannot queue; a pre-registration rejection has no document hold.

Add append-only `CrossSchoolIntakeResolution` with event FK, outcome, reason, actor/source, audit action ID and time. Reject closes only its cross-school hold. Accept keeps canonical ownership unchanged, records the claimed school from the event, opens `intake:event:{event_id}` before closing `cross_school`, and becomes an idempotently projectable queue claim. It never reassigns `Document.school_id`. Task 3 wires the served projection/reconciliation so a DB decision cannot be lost when JSON writing is interrupted.
Revision `bf2a3b4c5d6e` has `down_revision = "ae1f2a3b4c5d"`.

- [ ] **Step 4: Remove the conflicting URL uniqueness safely**

In ORM replace `UniqueConstraint("school_id", "source_url", name="uq_document_school_url")` with non-unique `Index("idx_document_school_source_url", "school_id", "source_url")`. PostgreSQL migration drops the named constraint and creates the index.

Implement the SQLite legacy upgrade as an explicit operation:

```python
def upgrade_sqlite_document_url_constraint(
    engine: Engine, *, verified_backup: VerifiedPreUpgradeSnapshot | None,
) -> None:
    """Idempotently remove only the legacy URL uniqueness; require backup before rebuild."""
```

`bootstrap_sqlite()` gains the same optional `verified_backup` argument. Bootstrap order is: inspect the existing schema; if the legacy auto-index is absent, continue; if present, require a Phase 1 `VerifiedPreUpgradeSnapshot` created and verified by the outer `eidp db-bootstrap` while that command still owns the one global data lock. It binds the live database's project-relative path, schema head and deployment SHA to an integrity-checked snapshot; snapshot SHA is not claimed to equal live SQLite bytes. Then perform one Alembic-style batch rebuild, run `PRAGMA foreign_key_check`, verify row/index counts, and continue with `Base.metadata.create_all()` and Alembic stamping. A failure preserves the verified snapshot and exits non-zero with the original live database selected.

Within its existing `_require_app_lock`, `eidp db-bootstrap --sqlite` detects the legacy constraint, calls `build_pre_upgrade_snapshot()`, verifies it, and passes the returned object directly to `bootstrap_sqlite()` without releasing/reacquiring the data lock. The Phase 1 runtime controller delegates to this one composite command; fresh databases pass no backup. Other direct callers may omit the argument but then fail closed if they encounter the legacy constraint. The fixture must contain a complete `Document`, all three existing foreign-key reference tables, data, the global `file_hash` unique index and other indexes; assert foreign keys, IDs and data survive and a second run is a no-op.

- [ ] **Step 5: Run tests and commit**

```bash
uv run pytest tests/unit/test_document_intake.py tests/unit/test_sqlite_bootstrap.py tests/unit/test_linux_runtime_controller.py -v
uv run ruff check src/eidp/pipeline/document_intake.py src/eidp/db tests/unit/test_document_intake.py
uv run mypy src/eidp/pipeline/document_intake.py src/eidp/db
git add src/eidp/db src/eidp/cli.py src/eidp/ops/runtime_controller.py src/eidp/pipeline/document_intake.py migrations/versions/bf2a3b4c5d6e_add_document_intake_registry.py tests/unit/test_document_intake.py tests/unit/test_sqlite_bootstrap.py tests/unit/test_linux_runtime_controller.py
git commit -m "feat: unify document intake and hash identity" -m "Goals: G2, G7, G10, G14"
```

### Task 3: Web, Extraction And Evidence Provenance

**Files:**
- Modify: `src/eidp/web/pages/pdf_intake.py`
- Modify: `src/eidp/web/pages/extraction_queue.py`
- Modify: `src/eidp/pipeline/pdf_intake.py`
- Modify: `src/eidp/pipeline/extraction_queue.py`
- Modify: `src/eidp/pipeline/extraction_review.py`
- Modify: `src/eidp/pipeline/review_report.py`
- Modify: `src/eidp/pipeline/review_decision.py`
- Modify: `src/eidp/pipeline/double_check_resolution.py`
- Create: `src/eidp/pipeline/source_evidence.py`
- Modify: `tests/unit/test_pdf_intake.py`
- Modify: `tests/unit/test_extraction_queue.py`
- Modify: `tests/unit/test_extraction_review.py`
- Modify: `tests/unit/test_review_decision.py`
- Modify: `tests/unit/test_double_check_resolution.py`
- Modify: `tests/unit/test_web_pdf_intake_app.py`
- Modify: `tests/unit/test_web_extraction_queue_app.py`

**Interfaces:**
- Consumes: canonical registry and Phase 2 identity
- Produces: document ID/full SHA through queue/review/report and resolvable `CellEvidence`

- [ ] **Step 1: Write failing provenance-chain tests**

Assert Web upload requires a real integer School ID, calls `register_document_intake`, same bytes do not create another blob/Document, and every extracted/reviewed row carries `document_id` plus full source SHA. Cross-school claims appear as served accept/reject work, never queue before an audited decision, and accepted claims project exactly one queue record even after restart/reconciliation. Prove `process_intake_record()` resolves from `data_dir`, verifies the canonical blob before the extractor is invoked, never joins a CAS path to `intake_root`, and refuses `suspect`, missing, off-host-only, size-mismatched or digest-mismatched evidence without invoking the extractor.

- [ ] **Step 2: Verify failure**

```bash
uv run pytest tests/unit/test_pdf_intake.py tests/unit/test_extraction_queue.py tests/unit/test_extraction_review.py tests/unit/test_web_pdf_intake_app.py -v
```

Expected: FAIL at missing canonical fields/registry wiring.

- [ ] **Step 3: Extend immutable row contracts and resolver**

Add required `document_id: int` and `source_sha256: str` to `ExtractedMetricRow`, `ExtractionReviewRecord`, and `ReviewedExtractionRow` for canonical TEXT rows. `ExtractionQueueItem.document_id` is `int | None` because URL-only/unregistered queue records can exist, but `process_intake_record()` requires a non-NULL document for the TEXT extraction lane and fails closed otherwise.

```python
@dataclass(frozen=True)
class LocalSourceEvidence:
    document_id: int
    sha256: str
    path: Path


class SourceEvidenceRestoreRequired(RuntimeError):
    """Raised when canonical bytes are unavailable locally and extraction must stop."""


def resolve_local_cell_evidence(
    session: Session, *, data_dir: Path,
    document_id: int, expected_sha256: str,
) -> LocalSourceEvidence:
    """Verify active local canonical bytes or fail closed; never trust source_pdf text."""
```

Change `process_intake_record()` to receive `session: Session`, `intake_root` (queue/result JSON only), and `data_dir`/an injectable local source resolver. Before any extractor call it loads `Document` plus `SourcePdfBlobState`, requires `active`, verifies the full digest/size through `verify_source_pdf()`, and passes the returned canonical path to extraction. Local absence raises `SourceEvidenceRestoreRequired`; off-host receipt resolution is added only in Task 5 after that model exists.

Keep page/table/row/column extraction in `CellEvidence`; attach canonical identity at persistence boundaries. Use exact row hold key `metric:{review_id}` after extraction.

JSON and SQLite cannot share a transaction, so use a conservative handoff: atomically write/fsync extracted results first; then, in one DB transaction, open every `review:metric:{review_id}` hold before closing the event-level `intake` hold. A crash after JSON but before DB commit leaves the old intake hold open and is safe to replay. `reconcile_extraction_hold_projection()` detects persisted results plus an open intake hold and idempotently completes the transition. Add fault injection at JSON-write/DB-commit boundaries and prove there is never a zero-hold window.

Review transitions open the next hold before closing the old one: accept/correct -> `diff:metric:{review_id}`; exclude -> `export:metric:{review_id}` so exclusion remains protected until a finalized Phase 4 manifest. An immutable external comparison `MATCH` snapshot automatically and atomically closes diff/opens export; a mismatch does so only after audited human resolution; `NOT_COMPARABLE` and unresolved mismatch keep diff open. Phase 4 receives the exact export-hold primary key and releases only terminal manifested rows.

When canonical document classification makes an old-year or non-target task terminal before ordinary review, create its immutable task/review projection, open `export:metric:{review_id}` or `export:task:{review_id}` first, then close the prior intake/review hold. It remains protected until Phase 4 finalizes the excluded manifest entry; no old/non-target path is allowed to remain forever in an intake/review hold.

Wire cross-school resolution into the served queue with typed identity/session injection. An accepted `CrossSchoolIntakeResolution` is the DB authority; `reconcile_intake_queue_projections()` writes/fsyncs its claimed-school queue JSON exactly once and keeps the intake hold open. Rejected claims never queue. Run both reconciliation functions on served queue load and Phase 3 startup recovery.

- [ ] **Step 4: Run tests and commit**

```bash
uv run pytest tests/unit/test_pdf_intake.py tests/unit/test_extraction_queue.py tests/unit/test_extraction_review.py tests/unit/test_review_decision.py tests/unit/test_double_check_resolution.py tests/unit/test_web_pdf_intake_app.py tests/unit/test_web_extraction_queue_app.py -v
git add src/eidp/web/pages/pdf_intake.py src/eidp/web/pages/extraction_queue.py src/eidp/pipeline src/eidp/pipeline/source_evidence.py tests/unit/test_pdf_intake.py tests/unit/test_extraction_queue.py tests/unit/test_extraction_review.py tests/unit/test_review_decision.py tests/unit/test_double_check_resolution.py tests/unit/test_web_pdf_intake_app.py tests/unit/test_web_extraction_queue_app.py
git commit -m "feat: carry canonical source evidence through review" -m "Goals: G1, G2, G3, G6"
```

### Task 4: Live References And Retention Anchor

**Files:**
- Modify: `src/eidp/db/models.py`
- Create: `src/eidp/pipeline/document_retention.py`
- Modify: `src/eidp/pipeline/document_intake.py`
- Modify: `src/eidp/pipeline/document_retention.py`
- Create: `migrations/versions/c03b4c5d6e7f_add_source_retention_state.py`
- Modify: `src/eidp/db/sqlite_bootstrap.py`
- Modify: `src/eidp/config.py`
- Modify: `src/eidp/pipeline/ingest.py`
- Modify: `src/eidp/pipeline/manual_entry.py`
- Modify: `src/eidp/pipeline/fiscal_year_override.py`
- Modify: `deploy/linux/env.example`
- Create: `tests/unit/test_document_retention.py`
- Create: `tests/unit/test_retention_writer_hooks.py`
- Modify: `tests/unit/test_fiscal_year_override.py`

**Interfaces:**
- Consumes: three existing current tables plus open `DocumentEvidenceHold` rows
- Produces: `DocumentLiveReferences`, `document_live_references()`, `refresh_retention_anchor()`

- [ ] **Step 1: Write failing liveness/anchor tests**

```python
def test_reactivation_resets_retention_clock(session: Session, document: Document) -> None:
    state = close_last_reference(session, document.id, now=dt("2026-01-01"))
    assert state.retention_anchor_at == dt("2026-01-01")
    add_current_department_reference(session, document.id)
    assert refresh_retention_anchor(session, document_id=document.id, now=dt("2026-02-01")) is None
    close_last_reference(session, document.id, now=dt("2026-03-01"))
    assert retention_state(session, document.id).retention_anchor_at == dt("2026-03-01")
```

Cover each of `DepartmentYearly`, `SchoolYearStatus`, `SupportRecipient`, open intake/review/diff/export holds, closed holds, every current-table writer, and conservative reconciliation after an intentionally stale/missing anchor.

- [ ] **Step 2: Verify failure**

```bash
uv run pytest tests/unit/test_document_retention.py -v
```

Expected: FAIL because retention state/query do not exist.

- [ ] **Step 3: Implement state and centralized query**

```python
@dataclass(frozen=True)
class DocumentLiveReferences:
    department_yearly: int
    school_year_status: int
    support_recipient: int
    open_evidence_holds: int

    @property
    def total(self) -> int:
        return sum(astuple(self))


def document_live_references(session: Session, document_id: int) -> DocumentLiveReferences:
    """Query all three current tables and every unreleased evidence hold."""


def refresh_retention_anchor(
    session: Session, *, document_id: int, now: datetime,
) -> datetime | None:
    """Clear anchor while live; set current time only on live-to-zero transition."""
```

Add `SourcePdfRetentionState` with nullable anchor plus `eligibility_blocked`, blocked reason/time, and indexes `(document_id, is_current)` on all three current tables. Add `source_pdf_retention_days: int = Field(default=365, ge=1)` to settings/env template.

Modify `ingest.py`, `manual_entry.py`, and `fiscal_year_override.py`: after their existing demote/create operations, `flush()`, collect both old and new non-NULL document IDs, deduplicate them, and call `refresh_retention_anchor()` for every ID inside the same transaction. Add `reconcile_retention_anchors()` that scans every document and recomputes from authoritative tables/holds. On any provider/query failure it clears the affected anchor, sets `eligibility_blocked=True` with a non-sensitive reason, commits that safe block, and reports failure; cleanup-manifest construction aborts. It must never preserve an expired anchor while liveness is unknown. This is the conservative repair path for a future writer that accidentally misses the hook.

Update the centralized `DocumentEvidenceHold` open/release helpers from Task 2 to call `refresh_retention_anchor()` after `flush()` in the same transaction. Callers never set `retention_anchor_at` directly.
Revision `c03b4c5d6e7f` has `down_revision = "bf2a3b4c5d6e"`.

- [ ] **Step 4: Run tests and commit**

```bash
uv run pytest tests/unit/test_document_retention.py tests/unit/test_retention_writer_hooks.py tests/unit/test_current_read_paths.py tests/unit/test_fiscal_year_override.py tests/unit/test_sqlite_bootstrap.py -v
git add src/eidp/db src/eidp/config.py src/eidp/pipeline/document_intake.py src/eidp/pipeline/document_retention.py src/eidp/pipeline/ingest.py src/eidp/pipeline/manual_entry.py src/eidp/pipeline/fiscal_year_override.py deploy/linux/env.example migrations/versions/c03b4c5d6e7f_add_source_retention_state.py tests/unit/test_document_retention.py tests/unit/test_retention_writer_hooks.py tests/unit/test_fiscal_year_override.py
git commit -m "feat: track live source evidence retention" -m "Goals: G2, G8, G9, G10"
```

### Task 5: Backup Receipts And Locked Cleanup State Machine

**Files:**
- Modify: `src/eidp/db/models.py`
- Modify: `src/eidp/pipeline/document_retention.py`
- Modify: `src/eidp/pipeline/source_evidence.py`
- Modify: `src/eidp/ops/runtime_controller.py`
- Modify: `src/eidp/web/app.py`
- Modify: `src/eidp/cli.py`
- Create: `migrations/versions/d14c5d6e7f80_add_source_cleanup_records.py`
- Create: `tests/integration/test_source_pdf_cleanup.py`
- Create: `tests/unit/test_source_evidence.py`
- Modify: `tests/unit/test_linux_runtime_controller.py`
- Modify: `tests/unit/test_web_bootstrap_app.py`
- Modify: `tests/unit/test_cli_write_lock_contract.py`
- Modify: `tests/integration/test_source_pdf_cleanup.py`

**Interfaces:**
- Consumes: finalized Phase 1 backup package, external receipt ID, retention state and full blob digest
- Produces: receipt, dry-run manifest, explicit confirmation, crash-safe cleanup, tombstone/offhost-only state

- [ ] **Step 1: Write failing eligibility and crash-window tests**

Test every six-condition gate, unknown backup package/receipt, backup-manifest digest mismatch, a receipt that omits the document digest, receipt creation by a non-authorized identity, stale confirmation hash, reactivated reference after plan, digest change, audit pending, lock busy, audit-insert failure during apply, crash after staging hardlink/before DB commit, and crash after commit/before hot/staging cleanup. Do not claim a receipt string is cryptographically authentic: v1 records an ICT-confirmed receipt through an authorized operator but has no ICT signature-verification API.

- [ ] **Step 2: Verify failure**

```bash
uv run pytest tests/integration/test_source_pdf_cleanup.py tests/unit/test_cli_write_lock_contract.py -v
```

Expected: FAIL because receipt/manifest/apply commands do not exist.

- [ ] **Step 3: Add append-only receipt/manifest/tombstone models**

Create package-level `OffHostBackupReceipt`, child `SourcePdfBackupReceipt`, `SourcePdfCleanupManifest`, `SourcePdfCleanupItem`, and `SourcePdfTombstone`. Source receipt binds document ID, full digest, package receipt/manifest digest and verified time; neither model contains external credentials.
Revision `d14c5d6e7f80` has `down_revision = "c03b4c5d6e7f"`.

```python
def build_cleanup_manifest(
    session: Session, *, now: datetime, retention_days: int,
    identity: ResolvedIdentity,
) -> SourcePdfCleanupManifest:
    """Return a non-executable dry run; include only rows passing every current gate."""


def confirm_cleanup_manifest(
    session: Session, *, manifest_id: str,
    expected_manifest_sha256: str, identity: ResolvedIdentity,
) -> None:
    """Append explicit confirmation without deleting files."""


def apply_cleanup_manifest(
    *, session_factory: sessionmaker[Session], manifest_id: str,
    expected_manifest_sha256: str, data_dir: Path,
    lock_path: Path, now: datetime, identity: ResolvedIdentity,
) -> CleanupResult:
    """Acquire one lock, recheck, hardlink-stage, commit tombstone, and reconcile."""


@dataclass(frozen=True)
class RecordedOffHostBackup:
    package_receipt: OffHostBackupReceipt
    source_receipts: tuple[SourcePdfBackupReceipt, ...]


def record_offhost_backup_receipt(
    session: Session, *, package_path: Path,
    expected_package_manifest_sha256: str,
    external_receipt_id: str, identity: ResolvedIdentity,
) -> RecordedOffHostBackup:
    """Append one package receipt and zero-or-more canonical source receipts."""
```

Create one `OffHostBackupReceipt` for every verified package even when it contains zero source PDFs; Phase 1 restore/DR reports bind this package-level row. Create zero-or-more `SourcePdfBackupReceipt` children only for canonical document/full digests actually present; cleanup uses those children. Recording validates the finalized package, exact package-manifest digest, inclusion of each derived document digest, and an authorized local-admin identity; it makes no cryptographic claim about arbitrary external receipt text. Package idempotency key is `(external_receipt_id, package_manifest_sha256)` and source idempotency adds `document_id`; existing keys must match every field or raise conflict. Insert package/source rows and one matching manual audit action in one transaction. Test the zero-source package case as successful with exactly one package receipt and no source children.

External receipt IDs use Phase 1 `eidp.ops.receipt_id` as the single validator with exact regex `^[A-Za-z0-9][A-Za-z0-9._:@+-]{0,127}$`; reject whitespace, quotes, shell metacharacters outside the allowlist and control characters in domain and CLI tests.

Do not add v2 roles. `source-backup-receipt-record PACKAGE --manifest-sha SHA --external-receipt-id ID` is a locked operator CLI exposed through `eidpctl.sh`. It derives `ResolvedIdentity(source=SYSTEM)` from the current OS account only after verifying that the effective UID owns the project root; this is the documented Venus SSH/local-operator trust boundary. Tests reject a different UID/owner, blank actor, fallback/trusted-Web identities on the CLI path, packages without the digest and conflicting retries.

After the receipt model exists, extend `source_evidence.py` with:

```python
@dataclass(frozen=True)
class OffHostSourceEvidence:
    document_id: int
    sha256: str
    receipt_id: str


def resolve_cell_evidence(
    session: Session, *, data_dir: Path,
    document_id: int, expected_sha256: str,
) -> LocalSourceEvidence | OffHostSourceEvidence:
    """Verify local bytes or return the exact verified off-host receipt reference."""
```

- [ ] **Step 4: Add locked CLI commands and recovery reconciliation**

Add `source-backup-receipt-record`, `source-cleanup-plan`, `source-cleanup-confirm`, and `source-cleanup-apply`; expose all through the Phase 1 runtime controller/wrapper.

- Plan/confirm services do not lock themselves; their CLI commands take the existing outer `_require_app_lock` exactly once.
- `apply_cleanup_manifest()` is the sole lock owner for apply. Its CLI command must not wrap `_require_app_lock`; update the AST contract to recognize this named safe service and reject any other unlocked writer. The CLI derives the same project-owner `SYSTEM` identity as receipt recording and passes it to apply. This avoids non-reentrant self-deadlock while preserving executor attribution.
- Under the lock, create a hardlink on the same filesystem at `data/source-pdfs/.cleanup-staging/{manifest_id}-{item_id}-{sha256}.pdf` while the canonical hot path still exists, and fsync the directory. First commit only `blob_status=cleanup_applying`. Then unlink/fsync the hot path. In a second transaction set `file_path=NULL`, set `offhost_only`, append the tombstone with the actual `local_deleted_at`, and insert `source_cleanup_applied` manual audit with the executing local-admin identity. Audit failure rolls that transaction back; staging restores the hot path during reconciliation. Only after the transaction commits remove/fsync staging. A tombstone never claims deletion before physical unlink succeeds.
- `reconcile_source_cleanup_staging()` uses the manifest/item ID and committed tombstone. `cleanup_applying` without a tombstone restores/revalidates the hot path from staging if needed and resets to active; a tombstone ensures the hot path is absent and removes staging. Fault-injection tests cover before/after each transaction and unlink without losing the final byte copy.

Wire recovery to real startup paths. `eidpctl start/restart` runs source-cleanup staging, accepted-claim queue projection, extraction-hold projection and retention-anchor reconciliation under the global data lock before launching Streamlit. `web/app.py` performs a check-only startup guard and refuses service if destructive staging is pending; safe claim/result projection can also complete idempotently on the relevant served page under the Web lock. Direct launcher use cannot serve an ambiguous cleanup state, and neither path silently deletes an unclassified file.

- [ ] **Step 5: Run tests and commit**

```bash
uv run pytest tests/integration/test_source_pdf_cleanup.py tests/unit/test_source_evidence.py tests/unit/test_linux_runtime_controller.py tests/unit/test_web_bootstrap_app.py tests/unit/test_cli_write_lock_contract.py tests/unit/test_document_retention.py -v
git add src/eidp/db/models.py src/eidp/pipeline/document_retention.py src/eidp/pipeline/source_evidence.py src/eidp/ops/runtime_controller.py src/eidp/web/app.py src/eidp/cli.py migrations/versions/d14c5d6e7f80_add_source_cleanup_records.py tests/integration/test_source_pdf_cleanup.py tests/unit/test_source_evidence.py tests/unit/test_linux_runtime_controller.py tests/unit/test_web_bootstrap_app.py tests/unit/test_cli_write_lock_contract.py
git commit -m "feat: clean source PDFs through verified manifests" -m "Goals: G2, G9, G10, G13"
```

### Task 6: Retire Legacy Storage And Pruning Bypasses

**Files:**
- Create: `src/eidp/pipeline/legacy_source_migration.py`
- Modify: `src/eidp/pipeline/document_intake.py`
- Modify: `src/eidp/pipeline/document_retention.py`
- Modify: `src/eidp/pdf/source_store.py`
- Modify: `src/eidp/db/models.py`
- Modify: `src/eidp/db/sqlite_bootstrap.py`
- Create: `migrations/versions/e25d6e7f8091_add_legacy_source_reconciliation.py`
- Modify: `src/eidp/cli.py`
- Modify: `src/eidp/ops/runtime_controller.py`
- Modify: `src/eidp/scraper/pdf_discovery.py`
- Modify: `scripts/prune_pdf_storage.py`
- Modify: `scripts/disk_health_check.py`
- Modify: `tests/unit/test_pdf_discovery.py`
- Modify: `tests/unit/test_prune_pdf_storage.py`
- Modify: `tests/unit/test_disk_health_check.py`
- Create: `tests/unit/test_legacy_source_migration.py`
- Create: `tests/unit/test_source_incident_resolution.py`
- Modify: `tests/unit/test_sqlite_bootstrap.py`
- Modify: `tests/unit/test_cli_write_lock_contract.py`
- Modify: `tests/integration/test_source_pdf_cleanup.py`
- Modify: `docs/runbooks/venus-init-and-acceptance.md`

**Interfaces:**
- Consumes: existing Document/file paths, unified source store/registry and cleanup service
- Produces: reconciled legacy evidence, controlled incident recovery and no second canonical write/dedup/delete path

- [ ] **Step 1: Write failing bypass tests**

Prove a dry-run inventories every existing Document/legacy 8-hex path without mutation. Apply migrates a valid full-hash/file pair into CAS, updates canonical path/blob state/audit in one locked DB transaction, preserves a tracked deprecated legacy copy, and is idempotent after interruption. NULL/invalid hash, missing file and digest mismatch become explicit `suspect/eligibility_blocked` issues and never silently pass. Absolute outside-root, `..`, file symlink and parent-directory symlink paths produce issues without reading bytes.

Prove discovery downloads into unique temporary bytes, calls `register_document_intake()` with `SYSTEM_IDENTITY`, no longer writes or re-registers 8-hex filenames, and legacy prune `--apply` either delegates to a confirmed manifest or fails closed. Disk health reports migration issues, staged/quarantine/offhost-only states without deleting them. Test incident recovery with valid/invalid replacement, outside-root/symlink refusal, preserved corrupt bytes, audit failure and `suspect -> active` only after full verification.

- [ ] **Step 2: Verify failure**

```bash
uv run pytest tests/unit/test_legacy_source_migration.py tests/unit/test_source_incident_resolution.py tests/unit/test_sqlite_bootstrap.py tests/integration/test_source_pdf_cleanup.py tests/unit/test_pdf_discovery.py tests/unit/test_prune_pdf_storage.py tests/unit/test_disk_health_check.py -v
```

Expected: FAIL while legacy paths remain.

- [ ] **Step 3: Route or disable every bypass**

Implement:

```python
def reconcile_legacy_document_storage(
    session: Session, *, data_dir: Path,
    identity: ResolvedIdentity, apply: bool = False,
) -> LegacySourceMigrationReport:
    """Dry-run by default; migrate verified legacy evidence without deleting old bytes."""


def resolve_source_blob_incident(
    session: Session, *, data_dir: Path,
    incident_id: str, verified_replacement: Path,
    identity: ResolvedIdentity,
) -> None:
    """Preserve bad bytes, verify approved replacement, audit, then reactivate."""
```

`source-legacy-reconcile` defaults to dry-run; `--apply` and `source-incident-resolve` derive the project-owner local-admin identity and take the global lock once. Before any stat/read, resolve each legacy path, require it beneath `data_dir`, reject `..`/absolute escape, reject a symlink file, and walk every existing parent to reject symlink traversal. Outside-root/symlink rows only create `LegacySourceMigrationIssue`; they are never read, copied or deleted.

For a valid legacy row, call `store_source_pdf()`, then transactionally update the Document to the full-SHA relative path, create active blob state plus `LegacySourceCopy`, and write audit. Never delete the old file before DB commit; the deprecated copy is never read as canonical. Extend cleanup manifest/apply/reconciliation to re-run the same boundary/symlink checks and bind each tracked legacy-copy path/digest as a separate item. Remove it only with the same confirmation, backup receipt, lock, audit and crash recovery as its document's canonical blob. Invalid/missing/mismatched rows create `LegacySourceMigrationIssue`, mark eligibility blocked/suspect where a digest exists, and stay on an operator manifest.

Revision `e25d6e7f8091` has `down_revision = "d14c5d6e7f80"`, creates the legacy-copy/issue tables, and extends cleanup items with `item_kind` (`canonical_blob` or `legacy_copy`), nullable `legacy_source_copy_id` FK and immutable `source_path_snapshot`. Add uniqueness so one manifest has one canonical item per document and one item per legacy-copy ID. Staging filenames, tombstones, audit payloads and reconciliation bind the cleanup item ID, not only document/digest. Test one document with canonical plus two legacy copies through independent confirmation, deletion and both crash windows. SQLite bootstrap creates/upgrades this schema idempotently. Include migration/bootstrap tests before reconciliation.

Incident resolution accepts replacement paths only below approved project-local quarantine/restore incoming roots, rejects symlinks, preserves the erroneous canonical object under the incident UUID, verifies expected digest/size, atomically republishes and re-verifies canonical bytes, and commits audit plus `suspect -> active` together. In that same transaction mark only this incident resolved, recompute all remaining migration/incident eligibility blockers, clear blocked reason/time only when none remain, and call `refresh_retention_anchor()`. Test that resolving one of two blockers leaves eligibility blocked. A crash/audit failure leaves suspect state and recoverable bytes.

Discovery downloads to a unique temporary file, reads validated bytes, and calls the unified registry once with the explicit non-human `SYSTEM_IDENTITY`; the temporary path and old 8-hex path are never treated as canonical input. Preserve discovery classification/rejection evidence. `prune_pdf_storage.py --apply` accepts only a confirmed manifest ID/hash and delegates to `apply_cleanup_manifest`; all former direct deletion paths exit non-zero.

- [ ] **Step 4: Run full gates, update truth labels and commit**

```bash
uv run ruff check .
uv run --with bandit bandit -q --severity-level high -r src/eidp scripts
uv run mypy src
uv run pytest --cov=src/eidp --cov-report=term --cov-fail-under=80
git add src/eidp/pipeline/legacy_source_migration.py src/eidp/pipeline/document_intake.py src/eidp/pipeline/document_retention.py src/eidp/pdf/source_store.py src/eidp/db/models.py src/eidp/db/sqlite_bootstrap.py src/eidp/cli.py src/eidp/ops/runtime_controller.py src/eidp/scraper/pdf_discovery.py migrations/versions/e25d6e7f8091_add_legacy_source_reconciliation.py scripts/prune_pdf_storage.py scripts/disk_health_check.py tests/unit/test_legacy_source_migration.py tests/unit/test_source_incident_resolution.py tests/unit/test_sqlite_bootstrap.py tests/unit/test_cli_write_lock_contract.py tests/integration/test_source_pdf_cleanup.py tests/unit/test_pdf_discovery.py tests/unit/test_prune_pdf_storage.py tests/unit/test_disk_health_check.py docs/runbooks/venus-init-and-acceptance.md
git commit -m "refactor: remove legacy PDF storage bypasses" -m "Goals: G2, G4, G9, G10"
```

After an adversarial review confirms no alternative overwrite/delete path remains and explicit authorization is given for both the remote branch push and GitHub PR creation:

```bash
git push -u origin feat/linux-web-v1-phase3-source-evidence
gh pr create --base main --head feat/linux-web-v1-phase3-source-evidence --title "feat: preserve canonical source evidence" --body $'Summary:\n- add full-SHA immutable source registry and provenance\n- add live-reference retention and verified cleanup\n\nVerification:\n- full local quality gates passed\n\nGoals: G2, G3, G4, G9, G10, G13'
gh pr checks feat/linux-web-v1-phase3-source-evidence --watch --interval 10
```

Require both named checks green and explicit owner merge authorization, then:

```bash
gh pr merge feat/linux-web-v1-phase3-source-evidence --merge --delete-branch
git fetch --prune origin
git switch main
git merge --ff-only origin/main
test "$(git rev-list --left-right --count origin/main...main | tr '\t' ' ')" = "0 0"
git status --short --branch
```

Expected: clean synchronized `main`. Phase 4 branches only from this merged result.

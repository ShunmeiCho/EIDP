# EIDP Linux/Web v1 On Venus — Approved Design

Date: 2026-07-12

Design status: **approved for specification; implementation pending**

Release status: **NOT_READY; PI release ratification pending**

## 1. Outcome And Scope

EIDP v1 is a shared Web application hosted on the laboratory Linux server
Venus. Business users work from their own computers through an approved
internal HTTPS URL. They do not use SSH, VNC or a remote desktop. Venus performs
PDF parsing, extraction and workbook generation and retains the minimum durable
business state needed for review, audit and recovery.

The v1 product line is:

- Streamlit browser UI;
- existing Python extraction/reconciliation core;
- SQLite with a global single-writer lock;
- user-confirmed source PDFs;
- text-PDF main lane and visible image/OCR exception lane;
- human review plus external second-opinion comparison;
- server-generated Excel/XLOOKUP-compatible output;
- ICT-owned internal reverse proxy.

React, FastAPI, PostgreSQL, real-time collaboration, role-based task assignment
and multi-writer concurrency are v2 concerns. They move forward only after real
multi-operator demand or other approved triggers exist. Windows is a frozen
historical fallback, not a development or deployment baseline.

## 2. Confirmed Baseline And Truth Labels

At design approval, the local Linux/Web mainline is not yet published to
`origin/main`; publishing it through a protected PR and green required checks is
the first deployment blocker. Venus deployment must never use unpublished local
code.

The design uses three truth labels:

| Label | Meaning |
| --- | --- |
| Existing | confirmed in the repository and covered by current evidence |
| Pending implementation | approved behavior that must be built and tested before acceptance |
| External dependency | owned by ICT, PI or another authorized party |

Key existing capabilities include the extraction core, Streamlit workflow
shell, SQLite lock, audit DB/outbox machinery, master diff, double-check report
and exact reference-fixture E2E assertions. Pending items include Web audit
write-through, trusted identity, authoritative content-addressed source storage,
complete partial-export gating, project-local process control and recovery
evidence.

## 3. Access Architecture

```text
business PC browser
        |
        | institutional HTTPS, auth and allowlist
        v
ICT reverse proxy
        |
        | loopback HTTP + WebSocket + trusted headers
        v
Streamlit 127.0.0.1:8502 on Venus
        |
        +-- extraction and comparison core
        +-- SQLite + data/.lock
        +-- source-PDF object store
        +-- audit/outbox
        +-- generated Excel bundles
```

Streamlit remains bound to `127.0.0.1`; only the ICT proxy exposes an internal
network endpoint. Loopback blocks remote direct access but does not exclude
other local Venus accounts, so it is not an identity boundary by itself.

The preferred ingress is a dedicated internal hostname serving `/`. If ICT can
only provide `/eidp/`, the proxy prefix and Streamlit `server.baseUrlPath` must
match, `/eidp` redirects to `/eidp/`, and `_stcore`/static paths retain the
prefix. Launcher support for `baseUrlPath`, the public browser address and
explicit CORS origins is pending and release blocking. The proxy must support
WebSocket upgrade, preserve the public
host/port/scheme, keep XSRF/CORS enabled, use a body limit above the application
file limit and apply an explicit health-probe policy.

The exact URL, path, allowed networks and authentication result are recorded as
deployment evidence. The detailed ICT contract is
`deploy/linux/reverse-proxy-requirements.md`.

## 4. Identity And Audit

### 4.1 Identity modes

v1 has two explicit modes:

- `trusted_proxy`: the proxy supplies a stable authenticated user ID and a
  shared secret;
- `configured_fallback`: the app ignores identity headers and records one
  configured operator for a bounded pilot.

Trusted mode validates both values, compares the secret in constant time and
never records the secret or its hash. An incomplete trusted configuration
prevents startup. Except for the dedicated liveness endpoint, a missing or
invalid identity at request time rejects the entire application request; it does
not downgrade to fallback or silently become read-only. Diagnostics show that
trusted identity has not been observed without including header or secret
values.

Fallback is an accepted v1 limitation only when ICT cannot supply a stable
identity. Because fallback ignores proxy identity headers, it explicitly assumes
that every Venus local account capable of reaching loopback is trusted not to
bypass the proxy. The limitation and operator name appear in PI acceptance
evidence; if PI does not accept that local-account trust, fallback is disabled
and trusted mode becomes mandatory.

### 4.2 Audit schema

Add nullable `identity_source` to `manual_action_log`. Existing rows are never
updated; readers coalesce NULL to `legacy_unspecified`. New values are controlled
by one `StrEnum` and centralized audit writer:

- `trusted_proxy`;
- `configured_fallback`;
- `system`;
- `legacy_unspecified`.

Fresh SQLite databases receive the field through ORM metadata. Existing SQLite
databases use additive `ALTER TABLE ADD COLUMN` during the supported bootstrap
path; other supported databases receive the additive migration. No data
backfill or table rebuild is allowed. A DB CHECK is omitted if it would rebuild
the append-only audit table. `action_id` remains the unique outbox deduplication
key.

### 4.3 Transaction and outbox contract

A business mutation and its `manual_action_log` row commit in the same SQLite
transaction. Failure to write the audit row rolls back the mutation. After
commit, the existing outbox projects the row to JSONL by `action_id`. Projection
failure does not undo the authoritative DB commit; it records the error and is
retried idempotently. A row is not export-eligible while its input/review audit
projection is outstanding; an export bundle is not finalized while its own
export audit projection is outstanding; affected source evidence is not cleaned.

Append-only fiscal-year tables retain their existing revision/demotion rules;
the Web layer must not replace them with in-place updates.

## 5. Source PDF Identity, Provenance And Retention

### 5.1 One authoritative content identity

The only content identity is the complete 64-hex-character, 256-bit SHA-256 of
the original bytes. `Document.file_hash` and its global UNIQUE index make the
registration/deduplication decision. A filename is a presentation attribute,
not a second identity rule. Legacy/exception rows may retain NULL during
migration, but every canonical uploaded source `Document` must have a validated,
non-NULL full digest.

The immutable blob path is derived only from the full digest: below
`data/source-pdfs/sha256`, the first two digest characters form a shard
directory and the filename is the complete digest plus `.pdf`.

Creation is create-if-absent and never overwrites an existing blob. If a target
exists, the app verifies digest, size and bytes before reuse; inconsistency
fails closed. The incoming bytes and incident are quarantined; an already
referenced canonical blob is never moved or overwritten, is marked suspect and
blocks extraction until verified or restored. Extraction revalidates the digest
before use.

The current Web intake hash-prefix filename/JSON mechanism and the DB hash index
are not two independent deduplication systems. Implementation must connect Web
intake to the canonical `Document` registry through an append-only authoritative
`document_intake_event` table. Each event contains its event ID, canonical
document ID, candidate SHA-256, claimed school and fiscal year, source type/URL,
original filename, actor, identity source, received time and intake disposition.
`document_id` is required for registered/duplicate/cross-school events and may
be NULL only for a pre-registration `rejected` event, which must retain its
validation reason and quarantine incident ID. JSON queue files become
projections of this state. Repeated bytes do not create another blob or
`Document`. A cross-school claim is recorded as pending manual review; its later
decision is a separate append-only audit/review record and it is never silently
reattributed.

The immutable intake dispositions are `registered`, `duplicate_same_school`,
`cross_school_review` and `rejected`. Review outcomes never rewrite the intake
event.

Blob creation precedes the DB registration transaction and is idempotent. An
unreferenced blob left by a failed transaction is handled only by a dry-run
orphan reconciliation. No cleanup path overwrites or silently deletes a blob.

The centralized live-reference query includes current `DepartmentYearly`,
`SchoolYearStatus` and `SupportRecipient` document links plus unresolved intake,
review, diff, export and other evidence references introduced by the Web
workflow. Any new table with document/current semantics must register with this
query and its contract tests. It is the only retention eligibility decision.
While the local blob exists, every extracted value's `CellEvidence` resolves
directly through the canonical document to source PDF, page, table, row and
column.

### 5.2 Retention

The pending `EIDP_SOURCE_PDF_RETENTION_DAYS` setting defaults to 365. The number
is an eligibility floor, not an automatic deletion time. Its anchor is the
latest UTC time at which the last current/live reference ceased to be live;
reactivation clears/resets the anchor.

A PDF referenced by any current/live derived record is never cleanup-eligible.
A closed or superseded PDF enters a dry-run cleanup manifest only when:

1. no current/live record references it;
2. no review, diff or export task remains open;
3. the final eligible Excel bundle has been produced;
4. its authoritative audit rows are committed and outbox projections complete;
5. a verified backup exists and has an off-host receipt;
6. the configured retention period has elapsed.

The operator reviews and explicitly confirms the manifest. The manifest is only
a proposal: immediately before deletion, the cleanup process acquires the global
write lock and rechecks every condition, current reference, off-host receipt and
blob digest. Any change aborts deletion.

Cleanup removes only the hot local copy. The off-host evidence copy remains
recoverable and the DB records a tombstone with digest, local deletion time,
cleanup manifest ID and off-host receipt; the local path is cleared rather than
left dangling. `CellEvidence` then resolves to the canonical digest and receipt,
and visual review requires a verified restore. Ultimate deletion of the
off-host evidence copy is outside v1 and requires a separate PI retention policy.

## 6. Source, Initialization And Process Control

### 6.1 Published source

`origin/main` is the only deployment source. Before Venus initialization, the
selected commit must be merged by PR, pass `Python quality gates` and
`Ship gate contract`, contain `uv.lock`, and equal the fetched
`origin/main` commit. Copying a local worktree or archive is prohibited.

### 6.2 Project boundary

All EIDP-created files, environments, caches, logs, PID files, backups and
temporary files stay below `/home/junming/EIDP`. The project may inspect host
resources but does not edit, install or configure outside the root. Python
dependencies live in `.venv`; uv/Python/browser caches and temporary paths are
redirected below the root.

Preflight records CPU, memory, disk, permissions, port use, tool availability,
`uv.lock` and soft/hard file-descriptor limits. It does not change host limits.

The deployment Unix UID and its processes are the v1 runtime trust boundary.
That UID must not be shared with untrusted workloads. This process boundary
does not make every Venus local account trusted; the broader local-account
assumption for `configured_fallback` remains separately governed by section
4.1. If the deployment UID cannot be isolated, deployment is not accepted and
a dedicated service account plus cgroup, fd-aware import or equivalent controls
require a separate approved design.

### 6.3 Configuration and controller

`project_env.sh` is sourced only from Bash wrappers. Interactive-shell sourcing
is not an operator procedure. Python may read `.env`; the current launcher does
not implicitly receive shell variables from it.

The project-local controller `deploy/linux/eidpctl.sh` must parse only
`EIDP_WEB_PORT`, `EIDP_WEB_BASE_URL_PATH`, `EIDP_INTERNAL_BASE_URL` and
`EIDP_WEB_MAX_UPLOAD_MB` from `.env` as data, validate them and never execute
`.env` as shell code. Port 8502 is the default. Bind is fixed to `127.0.0.1` and
is not a v1 configuration setting.

The controller exposes DB bootstrap, start, status, stop, restart and health. It
survives SSH disconnect, rejects a second instance, validates stale/live PIDs
against this checkout, rotates `logs/web.log` at 10 MiB with at most five
retained files, and never kills an unrelated process. An application stop/start
satisfies the restart gate. Machine-reboot autostart is an external ICT
responsibility.

`deploy/linux/eidpctl.sh` is the only operator lifecycle entrypoint. Operators
set the allowlisted `EIDP_WEB_PORT` in the project-root `.env`; they do not pass
it directly to the launcher. `deploy/linux/run_web.sh` requires the controller
to supply validated `STREAMLIT_SERVER_PORT` and is reserved for the internal CI
smoke when CI supplies that variable explicitly.

### 6.4 Deployment manifest

Each install/upgrade records a secret-free `run/deployment-manifest.json` with:

- deployed and `origin/main` commit;
- `uv.lock` SHA-256;
- schema/Alembic head;
- UTC time and operator;
- public URL, port and base path;
- matching pre-upgrade backup manifest;
- off-host backup receipt when available.

## 7. Backup, Restore And Rollback

The package builder and restore orchestration are pending implementation. They
reuse the existing WAL checkpoint plus `VACUUM INTO` operation as the consistent
SQLite snapshot and wrap it with audit/outbox data, source PDFs, exports and a
checksummed manifest under `backups/`.

The builder holds the global write lock while capturing the DB snapshot and
authoritative file inventory. It writes a staging package, verifies every
checksum, then atomically renames it and writes a finalized marker. ICT may pull
only finalized packages; an interrupted staging directory is never backup
evidence.

An ICT-owned process pulls the package to an approved off-host destination. An
outside-root copy on the same Venus disk is intermediate protection only and is
not disaster recovery.

Restore drills use an isolated disposable directory: verify hashes, run SQLite
`integrity_check`, start the matching code against the restored copy and compare
expected evidence before a controlled cutover. Live data is never deliberately
corrupted for a drill.

Every upgrade pairs code SHA, schema head and pre-upgrade backup. Rollback
restores that pair; code-only rollback across a schema change is forbidden. A
technical trial may demonstrate local restore, but internally acceptable v1
requires at least one off-host restore proof.

## 8. Business Workflow And Export Contract

```text
operator-confirmed PDF
  -> canonical SHA-256 registration
  -> TEXT or IMAGE_EXCEPTION classification
  -> extraction
  -> accept / correct / exclude review
  -> read-only master diff
  -> external second-opinion comparison
  -> human mismatch resolution
  -> partial Excel bundle
```

Text PDFs follow the main path. Image/unknown PDFs remain visible with an
actionable exception status and cannot silently enter output. External
Copilot/NotebookLM results are comparison evidence only; they never overwrite
EIDP values without an audited human decision.

v1 uses row-scoped Excel-ready gates and permits partial export:

- eligible accepted rows are included;
- a different row from the same institution may be withheld without suppressing
  the eligible row;
- the institution summary reports `included_complete`, `included_partial`,
  `withheld` or `excluded`;
- permanently excluded rows/institutions are listed with a business reason;
- unresolved rows are withheld and listed with the blocking reason and task;
- an export with zero eligible target-year rows is refused;
- a partial export is operational output, not by itself evidence that all v1
  release gates are complete.

Each bundle contains the workbook and
`output/exports/{export_id}/export-manifest.v1.json`. The JSON schema ID is
`eidp.export-manifest.v1`. Its top level records export ID, lifecycle state
(`staged` or `finalized`), fiscal year, deployed commit, UTC time, actor,
identity source, workbook filename/SHA-256 and included/withheld/excluded counts.

Each manifest row records a stable key composed from school ID, fiscal year,
department key, course name and metric; disposition (`included`, `withheld` or
`excluded`); controlled reason code/detail; blocking task ID; institution
summary state; source document SHA-256; and review identity/time. Controlled
hold reasons include `unreviewed`, `low_confidence`, `image_exception`,
`ambiguous_key`, `double_check_mismatch`, `audit_pending`, `non_target`,
`old_year` and `business_excluded`. `data/master.xlsx` remains read-only.

A row enters the workbook only when required identity/year/document checks pass,
it has an accepted value, ambiguous mappings and program changes are resolved,
external mismatches are corrected or explicitly resolved by a reasoned audited
decision, and authoritative audit evidence is complete.

Input/review audit projections must be complete before their rows are eligible.
The server builds a staged bundle under a persistent export ID, records the
export event and workbook checksum, flushes that audit projection, and only then
atomically publishes the `finalized` bundle for download. A failure leaves the
bundle unavailable for business use; restart recovers staging/finalization
idempotently by export ID.

## 9. Failure Semantics

| Failure | Required behavior |
| --- | --- |
| duplicate bytes | reuse canonical blob/document; create only provenance/audit event |
| invalid PDF or failed extraction | retain source and reason; no Excel-ready row; safe retry |
| image/unknown PDF | visible exception lane; never silent acceptance |
| SQLite lock busy | busy banner; no partial write; operator retries |
| invalid trusted identity | except liveness, reject the entire request; no read-only/fallback downgrade or sensitive log value |
| authoritative audit insert failure | roll back business transaction |
| JSONL projection failure | retain DB commit, record outbox error, retry idempotently; withhold affected row or staged bundle from finalization |
| network/browser interruption | recover committed state only; unsaved widget edits may be lost |
| process interruption | restart from committed durable state; no duplicate committed work |
| backup failure | block upgrade, cleanup and release |
| schema rollback request | restore matching code/backup/schema pair |

The v1 lock-busy interaction is expected behavior under SQLite single-writer
operation, not a defect or real-time collaboration promise.

## 10. Verification And Acceptance Evidence

### 10.1 Automated contracts

- additive `identity_source` upgrade without historical UPDATE or table rebuild;
- identity-mode startup and runtime fail-closed behavior;
- same-transaction mutation/audit and idempotent outbox retry;
- full-hash no-overwrite CAS, duplicate reuse, prefix-collision simulation,
  pre-existing corrupt blob refusal and concurrent registration;
- cross-school duplicate manual-review behavior;
- retention eligibility, reference protection and operator-confirmed dry run;
- write-lock busy path with no state change;
- partial-export filtering and complete exclusion/hold manifest;
- path sanitization and project-root boundary contracts.

### 10.2 Integration and browser contracts

The reference text PDF must retain exact expectations of 28 departments,
84 metric rows and 3 independent course nodes through intake, extraction,
accept/correct/exclude review, master diff, external comparison and export.

Tests also cover image exception routing, unresolved mismatch exclusion,
authoritative audit row plus deduplicated JSONL, zero-eligible export refusal,
Streamlit upload sanitization, lock-busy UX and the remaining workflow pages.

### 10.3 Venus and business evidence

Required evidence includes:

- published SHA and required CI checks;
- isolated install and point-in-time filesystem/socket boundary evidence;
- process start/status/stop/restart, stale PID, second-instance and bounded logs;
- loopback bind plus TLS/allowlist/authenticated WebSocket proxy path;
- near-limit upload and explicit health policy;
- real business-PC upload, review, partial export and download;
- text and image-lane behavior;
- trusted or fallback actor/source audit evidence;
- zero unresolved high-risk mismatch in the accepted scope; every permanent
  exclusion approved with a recorded reason;
- isolated local restore and off-host restore;
- PI/owner sign-off.

Screenshots and HAR files must exclude or redact cookies, tokens, identity
headers and proxy secrets. `find`, `lsof` and socket output are snapshots, not
proof of historical non-write behavior.

The release remains `NOT_READY` until every mandatory gate has fresh evidence.

## 11. Implementation Decomposition

The implementation plan must preserve this order:

1. publish the approved Linux/Web source through PR and required CI;
2. implement project-local process/configuration control and deployment manifest;
3. connect Web mutations to identity and authoritative audit;
4. unify Web intake with the canonical document hash/blob registry and retention;
5. enforce partial export and the complete exclusion/hold manifest;
6. add automated and browser coverage;
7. initialize Venus and collect loopback/restart/local-restore evidence;
8. coordinate ICT proxy and off-host backup, then run business-PC and PI acceptance.

No Venus initialization, ICT mutation or release claim is implied by approval of
this design document.

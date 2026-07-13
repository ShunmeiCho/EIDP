# Venus 初始化、运行与 v1 内部验收 Runbook

Status: **DESIGN RUNBOOK — NOT YET EXECUTABLE END TO END**

Release forecast: **NOT_READY**

This runbook applies only to `venus:/home/junming/EIDP`. It distinguishes:

- **AVAILABLE** — present in the repository today;
- **PENDING** — approved design, but implementation or evidence is still required;
- **ICT** — owned outside the repository by the institution administrator.

Do not describe a PENDING item as an existing control. Do not initialize Venus
from unpublished local commits.

## 0. Hard Preconditions

1. **PENDING — publish the source baseline first.** The deployment commit must
   be merged through a PR into `origin/main`, with `Python quality gates` and
   `Ship gate contract` green. A local `main` commit is not deployable evidence.
2. **AVAILABLE — locked dependencies.** The selected commit must contain
   `uv.lock`; installation uses `uv sync --frozen`.
3. **AVAILABLE — project-local controller.** `deploy/linux/eidpctl.sh` provides
   start/status/health/stop/restart, DB bootstrap, PID validation,
   single-instance protection and bounded stdout logging. Venus runtime evidence
   is still required before operational acceptance.
4. **ICT — approved ingress.** ICT must provide the exact internal URL, TLS,
   allowlist/authentication, WebSocket-capable reverse proxy and health-probe
   policy described in `deploy/linux/reverse-proxy-requirements.md`.
5. **ICT — off-host backup target.** A pull-based destination on a different
   host/storage failure domain must exist before v1 can be accepted as disaster
   recoverable.

## 1. Preflight And Traceable Initialization

All commands and generated artifacts must remain under `/home/junming/EIDP`.
Read-only inspection of the host is permitted; this runbook never authorizes an
install or edit outside that root.

### 1.1 Record the host preflight

Record, without changing host configuration:

- OS and architecture;
- CPU, memory and free space available to the project root;
- `git`, `uv` and Python 3.12 availability;
- the soft and hard `ulimit -n` values;
- write permission for `/home/junming/EIDP`;
- whether port 8502 is already in use.

A low file-descriptor limit or occupied port is a blocker to investigate, not
permission to change system settings.

### 1.2 Clone only the published mainline

After the PR precondition is satisfied:

```bash
git clone --branch main --single-branch https://github.com/ShunmeiCho/EIDP.git /home/junming/EIDP
cd /home/junming/EIDP
git fetch origin
git pull --ff-only origin main
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"
test -f uv.lock
```

Never copy a local worktree, archive or unpublished commit to Venus.

### 1.3 Create the isolated environment

**AVAILABLE:**

```bash
bash deploy/linux/sync_venv.sh
```

The wrapper confines `.venv`, uv/Python caches, Playwright files, temporary
files and the runtime home below the project root. The v1 main lane installs the
`pdf` and `scraper-basic` extras; OCR remains an exception lane.

### 1.4 Runtime configuration boundary

- `deploy/linux/project_env.sh` is a Bash library used by Bash wrappers. An
  operator must not source it from an arbitrary interactive shell.
- `.env` is read as data by Python; operators do not source it as shell code.
- **AVAILABLE:** the project-local controller parses only
  `EIDP_WEB_PORT`, `EIDP_WEB_BASE_URL_PATH`, `EIDP_INTERNAL_BASE_URL` and
  `EIDP_WEB_MAX_UPLOAD_MB` from `.env`, validates them and passes them to the
  launcher. It does not execute `.env` as shell code.
- **AVAILABLE:** Pydantic Settings reads `EIDP_IDENTITY_MODE`,
  `EIDP_FALLBACK_ACTOR` and `EIDP_PROXY_SHARED_SECRET` from the private `.env`;
  `run_web.sh` validates identity configuration before starting Streamlit.
  Trusted-proxy mode with an empty secret therefore fails before the server
  process starts. A real secret must come from ICT secret management and must
  never enter git, logs, evidence or the deployment manifest.
- Port defaults to 8502. `--server.address 127.0.0.1` remains hard-coded and is
  not configurable in v1. `EIDP_WEB_BIND` must not be presented as effective.
- Root hosting is preferred. If ICT requires `/eidp/`, the controller must set
  `server.baseUrlPath=eidp` and record the public URL and path in the deployment
  manifest.

### 1.5 Database and application startup

**AVAILABLE:** `deploy/linux/eidpctl.sh` is the runtime lifecycle entrypoint.
Its public operations are:

```text
deploy/linux/eidpctl.sh db-bootstrap
deploy/linux/eidpctl.sh import-excel <path>
deploy/linux/eidpctl.sh manifest --actor <operator>
deploy/linux/eidpctl.sh backup-package --backup-id <backup-id> --actor <operator>
deploy/linux/eidpctl.sh backup-verify backups/<backup-id>
deploy/linux/eidpctl.sh restore-drill backups/<backup-id> --target restore-drills/verified/<backup-id>
deploy/linux/eidpctl.sh start
deploy/linux/eidpctl.sh status
deploy/linux/eidpctl.sh stop
deploy/linux/eidpctl.sh restart
deploy/linux/eidpctl.sh health
```

The controller must source `project_env.sh` inside Bash, run `uv` with
`--frozen --no-sync` after synchronization, and keep all state below the root.
It must also:

- survive SSH disconnect with `setsid`/equivalent SIGHUP isolation;
- reject a second instance;
- detect and remove only a verified stale PID file;
- verify that a live PID belongs to this checkout before stop/restart;
- keep `run/eidp.pid.json` below the root and rotate `logs/web.log` at 10 MiB
  with no more than five retained backups plus the active log;
- preserve the 127.0.0.1 bind;
- expose a loopback health check at `/_stcore/health`.

The restart acceptance gate means application `stop -> start`. Automatic start
after a Venus machine reboot is outside the project boundary and remains an ICT
responsibility.

### 1.6 Deployment manifest

**AVAILABLE — repository/local evidence only:** `eidpctl.sh manifest` validates
the protected checkout and atomically writes `run/deployment-manifest.json`
containing at least:

- deployed commit and matching `origin/main` commit;
- SHA-256 of `uv.lock`;
- Alembic/schema head;
- UTC deployment time and operator;
- public internal URL, port and base path;
- operator-supplied pre-upgrade backup ID when available; recording the ID
  does not prove that it matches a finalized package;
- off-host backup receipt ID when available.

It must contain no secret values.

The command and its local contracts are available. A manifest captured from an
actual Venus installation remains **PENDING** and cannot be inferred from Mac
test evidence.

## 2. Runtime And Failure Semantics

The browser is the business-user interface; SSH is only for deployment and
administration. Venus provides compute plus the minimum durable source of
business truth.

- **AVAILABLE:** SQLite and the global `data/.lock` implement the v1
  single-writer boundary.
  A concurrent second write receives a busy banner and performs no partial
  write.
- **AVAILABLE — repository/local evidence only:** committed review and
  double-check decisions survive a fresh Streamlit `AppTest` session. Unsaved
  widget edits do not survive a process or browser failure and are not claimed
  as resumable.
- **PENDING — Venus process evidence:** application `stop -> start` recovery has
  not been demonstrated on Venus. A fresh `AppTest` session is not a substitute
  for this acceptance gate.
- **AVAILABLE — repository/local evidence only:** the served TEXT queue invokes
  the extraction core through its Run/Retry controls. The successful reference
  path is covered through the real page entrypoints; core contracts retain the
  source PDF and retriable failure state and prevent failed work from becoming
  Excel-ready. A real Venus failure/retry drill remains **PENDING**.
- **AVAILABLE — repository/local evidence only:** trusted-proxy mode rejects an
  invalid identity or secret without downgrading to fallback, and incomplete
  trusted configuration fails closed. Real proxy-injected headers and shared-
  secret behavior on Venus remain **PENDING**.
- **AVAILABLE — repository/local evidence only:** failure to insert the
  authoritative audit row rolls back the business transaction. A post-commit
  JSONL projection failure leaves the DB commit authoritative, records the
  outbox error and can be retried idempotently. Withholding an audit-pending row
  from a finalized export remains **PENDING** with Phase 4 export finalization.
- **PENDING:** backup failure blocks upgrades, source-PDF cleanup and v1 release.

## 3. Business Workflow And Partial Export

Target workflow (**partly PENDING**):

```text
operator-confirmed PDF
  -> SHA-256 registration and duplicate check
  -> TEXT or IMAGE_EXCEPTION
  -> extraction
  -> accept / correct / exclude review
  -> read-only master diff
  -> external second-opinion comparison
  -> human resolution
  -> server-generated Excel bundle
```

**AVAILABLE — repository/local evidence only:** the real Streamlit entrypoints
now cover intake -> TEXT extraction -> accept/correct/exclude review -> read-only
master diff -> persisted external comparison -> reasoned human resolution. The
reference fixture produces exactly 28 extraction nodes, 84 metric rows and 3
independent course nodes; committed decisions and their DB/JSONL audit evidence
survive fresh `AppTest` sessions.

**PENDING:** canonical DB-backed source registration/retention, image-lane
acceptance evidence, row-scoped partial export, final Excel generation and
download, Venus process evidence, the business-PC run and PI acceptance.

TEXT PDFs use the main lane. Image/unknown PDFs remain visible in the manual
exception lane and cannot silently enter output.

v1 permits a **row-scoped partial export**. An eligible row may enter the
workbook even when another row from the same institution is withheld. The
institution summary therefore distinguishes `included_complete`,
`included_partial`, `withheld` and `excluded`. An export with zero eligible
target-year rows is refused.

Each bundle contains the workbook and
`output/exports/{export_id}/export-manifest.v1.json`. The manifest uses schema
ID `eidp.export-manifest.v1` and records:

- export ID, lifecycle state (`staged` or `finalized`), fiscal year, deployed
  commit, UTC timestamp, actor and identity source;
- workbook filename and SHA-256;
- one stable row key composed from school ID, fiscal year, department key,
  course name and metric;
- row disposition (`included`, `withheld` or `excluded`), controlled reason
  code/detail and blocking task ID;
- institution summary state, source document SHA-256 and review identity/time;
- counts for included, withheld and excluded rows/institutions.

Controlled hold reasons include `unreviewed`, `low_confidence`,
`image_exception`, `ambiguous_key`, `double_check_mismatch`, `audit_pending`,
`non_target`, `old_year` and `business_excluded`.

No unresolved, ambiguous, mismatched, unreviewed or image-exception row may
enter the workbook. `data/master.xlsx` remains read-only. A mismatch may enter
only after correction or an explicit, reasoned and audited human resolution.
Input/review audit projections must be complete before the affected row is
eligible. The server builds a staged bundle, records the export event and
workbook checksum under the same export ID, flushes its audit projection, and
only then exposes the atomically published `finalized` bundle for download.
Interrupted staging/finalization is recovered idempotently by export ID.

## 4. Identity, Audit And Source Evidence

The following controls are **AVAILABLE — repository/local evidence only**:

- `manual_action_log.identity_source` is nullable; migration does not rewrite
  historical rows, and reads treat NULL as `legacy_unspecified`;
- one typed audit writer uses `trusted_proxy`, `configured_fallback`, `system`
  and `legacy_unspecified`;
- `action_id` remains the audit/outbox deduplication key;
- business mutation and `manual_action_log` commit in one SQLite transaction;
- trusted mode requires both trusted identity and proxy shared secret;
- startup refuses incomplete trusted configuration and, except for liveness,
  rejects the entire invalid request without logging secret material.

The served review and double-check actions use these controls in one locked
transaction and project committed audit rows to JSONL after commit. Repository
tests cover rollback, idempotent retry and a fresh-session DB/JSONL identity
match. Actual Venus proxy headers, secret injection and operational audit proof
remain **PENDING**.

Fallback explicitly trusts every Venus local account that can reach loopback not
to bypass the proxy. This must be recorded as a PI-accepted limitation; otherwise
fallback is disabled and trusted mode is mandatory.

Canonical source evidence remains **PENDING**. Web intake currently computes a
full SHA-256 but its filename uses only a
12-character prefix plus the original filename, and it is not integrated with
the DB-wide `Document.file_hash` unique contract. The target design therefore
uses one authoritative full SHA-256 document registry:

- every canonical uploaded `Document` has a validated, non-NULL full digest and
  the DB unique hash is the deduplication decision;
- stored source objects are addressed by the full hash, created without
  overwrite and immutable; an inconsistent incoming object is quarantined while
  the canonical object is left untouched and marked suspect;
- an append-only authoritative `document_intake_event` records event ID,
  document ID, candidate SHA-256, claimed school/fiscal year, source, original
  filename, actor, identity source, received time and immutable disposition;
  `document_id` may be NULL only for a pre-registration rejection carrying its
  validation reason and quarantine incident ID; JSON queue files are projections
  rather than an independent source of truth;
- multiple intake/business references point to one object;
- while a local blob exists, every `CellEvidence` resolves directly to that
  object and its page/table/row/column; after hot-storage cleanup it resolves to
  the canonical hash plus off-host receipt and requires verified restore;
- a hash collision or same-hash/different-bytes inconsistency fails closed.

Intake dispositions are `registered`, `duplicate_same_school`,
`cross_school_review` and `rejected`. Cross-school claims remain quarantined for
an append-only human decision and are never silently reattributed. The
centralized live-reference query covers current `DepartmentYearly`,
`SchoolYearStatus` and `SupportRecipient` links and all unresolved
intake/review/diff/export evidence references. New document/current tables must
register with this query and its contract tests.

**PENDING:** `EIDP_SOURCE_PDF_RETENTION_DAYS` will default to 365. Its clock
starts at the latest UTC time when the last current/live reference ceased to be
live; reactivation resets the anchor. Source PDFs remain in hot storage while
any derived record is current/live. A closed or superseded PDF becomes
cleanup-eligible only after all review/export/audit and backup prerequisites
pass and the retention window elapses. Cleanup removes only the hot local copy;
the off-host evidence copy and receipt remain. It records a tombstone containing
the digest, deletion time, cleanup manifest ID and off-host receipt, and clears
the local path rather than leaving a dangling path.

The dry-run manifest is only a proposal. Immediately before deletion, the
controller acquires the global write lock, rechecks every eligibility condition
and blob digest against current DB state, and aborts on any change. Explicit
operator confirmation is mandatory; there is no silent background delete.

## 5. Backup, Restore And Rollback (**PARTLY AVAILABLE — LOCAL EVIDENCE ONLY**)

1. **AVAILABLE — local package construction:** `eidpctl.sh backup-package`
   holds the global data lock, reuses the WAL checkpoint plus `VACUUM INTO`,
   captures the exact allowlisted DB/audit/source-PDF/export/deployment
   inventory, keeps `data/master.xlsx` owner-read-only, verifies all digests and
   atomically publishes a finalized package under `backups/`. `backup-verify`
   revalidates finalized evidence without modifying it. These controls have
   automated local evidence; they have not yet run on Venus.
2. **ICT/PENDING — off-host disaster recovery:** ICT must pull a verified
   finalized package to an approved different host/storage failure domain and
   return a receipt bound to the package-manifest digest. An outside-root copy
   on the same Venus disk is only intermediate protection and is not disaster
   recovery.
3. **AVAILABLE — isolated local restore drill:** `eidpctl.sh restore-drill`
   rematerializes a finalized package only below `restore-drills/verified/`,
   rechecks descriptor-bound package evidence and SQLite integrity/schema,
   runs and stops a temporary loopback Streamlit process against restored data,
   optionally checks export/action/audit evidence, and writes a secret-free
   restore report. Idempotent retries never overwrite or repair an existing
   conflicting target.
4. **PENDING/PARTIAL — code/backup pairing:** tested primitives can record the
   protected code SHA, `uv.lock`, schema head and an optional pre-upgrade backup
   ID. The controller does not yet create or verify a matched code/package pair
   as one upgrade transaction, so this is not rollback evidence. Code-only
   rollback across a migration remains forbidden.

**PENDING — Venus/off-host proof:** no repository test proves Venus storage,
off-host transfer, receipt custody or recovery after loss of the project root.
Internally acceptable v1 still requires at least one successful off-host restore proof
plus the Venus acceptance evidence in Section 6.

## 6. Acceptance Evidence

| Gate | Required evidence | Goal |
| --- | --- | --- |
| Published source | deployed SHA equals protected `origin/main`; required CI checks green | G14 |
| Isolated install | `.venv`, cache and runtime artifacts under project root; boundary snapshots with accurately stated limits | G9, G13 |
| Process control | start/status/stop/restart, stale-PID and second-instance tests; bounded log evidence | G9, G12 |
| Network | loopback socket, TLS/allowlist/auth, WebSocket and health probe through the approved proxy | G13 |
| Business PC | real-PC upload -> review -> partial export/download | G15 |
| Text lane | exact reference fixture counts, review, diff, double-check and Excel-ready invariants | G1, G3, G6 |
| Image lane | image PDF remains visible, excluded from workbook and has an actionable reason | G3, G11 |
| Audit | one Web decision yields one DB audit row and one deduplicated JSONL projection with actor/source | G2, G10 |
| Export integrity | mixed complete/partial institutions, zero-eligible refusal, manifest schema/checksum and staged-to-finalized audit path | G2, G10, G15 |
| READY risk closure | no unresolved high-risk mismatch remains in the accepted scope; each permanent exclusion is approved and reasoned | G3, G15 |
| Recovery | isolated local restore plus off-host restore; code/backup pair verified | G9 |
| PI acceptance | completed owner/PI release sign-off | G15 |

Screenshots must avoid sensitive data. HAR files are collected only when needed,
must be redacted of cookies, tokens and identity headers, and must never contain
the proxy shared secret. `find`, `lsof` and socket listings are point-in-time
evidence, not proof that no historical write ever occurred.

Until every mandatory gate has fresh evidence, the release remains
`NOT_READY`.

# Linux/Web v1 Phase 5 Venus Acceptance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy the fully merged Linux/Web v1 from protected GitHub main to Venus, prove the real internal browser/recovery path, and collect the evidence required for PI release acceptance.

**Architecture:** Local development and CI remain authoritative for code. SSH is used only after all implementation phases merge: first for read-only preflight, then for an origin/main clone confined to `/home/junming/EIDP`; ICT separately owns proxy/TLS/auth/off-host storage, and business users validate the complete flow from their own PCs.

**Tech Stack:** SSH, GitHub, uv, Python 3.12, Streamlit, SQLite, institutional reverse proxy, browser, Excel

## Global Constraints

- Do not start until Phases 0–4 are merged into `origin/main` and both required GitHub checks are green.
- Do not copy local code over SSH. Venus clones/pulls only protected `origin/main`.
- All project writes, dependencies, caches, evidence and restore drills stay below `/home/junming/EIDP`.
- Do not edit `/etc`, install host-wide packages, change `ulimit`, configure the proxy, or write outside the project root.
- Streamlit binds exactly `127.0.0.1`; business users never use SSH.
- SSH instability is expected: every remote step is idempotent and records completion before disconnect.
- Never print the proxy secret. HAR/screenshot evidence is redacted before retention.
- A local backup is not DR; acceptance requires a verified off-host pull and restore.
- Keep release state `NOT_READY` until every gate and PI sign-off is complete.

---

### Task 1: Final GitHub And Read-Only Venus Preflight

**Files:**
- Read: `docs/runbooks/venus-init-and-acceptance.md`
- Read: `deploy/linux/reverse-proxy-requirements.md`
- Runtime evidence root after clone: `/home/junming/EIDP/evidence/runtime/`

**Interfaces:**
- Consumes: protected green `origin/main`, empty/approved Venus root
- Produces: go/no-go evidence without host mutation

- [ ] **Step 1: Verify GitHub source and checks locally**

```bash
git fetch --prune origin
git rev-list --left-right --count origin/main...main
EXPECTED_SHA=$(git rev-parse origin/main)
REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner')
CHECKS=$(gh api "repos/$REPO/commits/$EXPECTED_SHA/check-runs?per_page=100" --jq '[.check_runs[] | select(.name == "Python quality gates" or .name == "Ship gate contract")] | group_by(.name) | map(sort_by(.completed_at // .started_at) | last)[] | [.name, .conclusion, .head_sha] | @tsv')
test "$(printf '%s\n' "$CHECKS" | wc -l | tr -d ' ')" -eq 2
printf '%s\n' "$CHECKS" | awk -v sha="$EXPECTED_SHA" '$2 != "success" || $3 != sha { exit 1 }'
```

Expected: divergence `0 0`; latest required jobs succeeded for the same `origin/main` SHA.

- [ ] **Step 2: Obtain explicit SSH/preflight authorization**

Expected: user authorizes read-only `ssh venus` checks. Without authorization, stop.

- [ ] **Step 3: Inspect host facts without changing them**

```bash
ssh venus 'set -eu; command -v git; command -v uv; command -v sha256sum; uname -a; getconf LONG_BIT; ulimit -Sn; ulimit -Hn; df -h /home/junming/EIDP; test -d /home/junming/EIDP; test -w /home/junming/EIDP; if command -v ss >/dev/null 2>&1; then ss -ltn; else netstat -an; fi'
```

Expected: git/uv available, root writable, enough resources, and port 8502 unused. A missing tool/permission/unsafe limit is reported to ICT; do not install or reconfigure it.

- [ ] **Step 4: Confirm the root is safe to initialize**

```bash
test -n "$EXPECTED_SHA"
ssh venus 'find /home/junming/EIDP -mindepth 1 -maxdepth 1 -print'
```

Expected for first initialization: no output (`EMPTY`). Pin this exact `EXPECTED_SHA` for the entire acceptance run; never recompute it after `origin/main` advances. For a resumed run, read `run/expected-deployment-sha`, re-query the two GitHub checks for that stored SHA, and accept the root only when it contains `.git`, is clean, and `HEAD` equals the stored value (`RESUMABLE`). Any other non-empty state is `CONFLICT`: stop and identify ownership; never delete automatically.

### Task 2: Traceable Origin/Main Initialization

**Files:**
- Runtime: `/home/junming/EIDP/.venv`
- Runtime: `/home/junming/EIDP/.env`
- Runtime: `/home/junming/EIDP/run/deployment-manifest.json`

**Interfaces:**
- Consumes: Task 1 go decision and ICT-provided exact runtime values
- Produces: loopback-only healthy app at the protected commit

- [ ] **Step 1: Clone protected main into the exact root**

```bash
ssh venus 'test -z "$(find /home/junming/EIDP -mindepth 1 -maxdepth 1 -print -quit)"'
ssh venus 'git clone --no-checkout --branch main --single-branch https://github.com/ShunmeiCho/EIDP.git /home/junming/EIDP'
ssh venus "cd /home/junming/EIDP && git cat-file -e '$EXPECTED_SHA^{commit}' && git checkout -B main '$EXPECTED_SHA' && mkdir -p run && printf '%s\n' '$EXPECTED_SHA' > run/.expected-deployment-sha.tmp && mv run/.expected-deployment-sha.tmp run/expected-deployment-sha"
```

Expected on `EMPTY`: one clean checkout; no local code transfer. On `RESUMABLE`, skip clone and continue with Step 2 after rechecking SHA/cleanliness. On `CONFLICT`, stop. Every later task records its completed artifact and treats an identical verified artifact as success, so an SSH disconnect is resumable.

- [ ] **Step 2: Verify checkout identity and lockfile**

```bash
ssh venus "cd /home/junming/EIDP && test \"\$(cat run/expected-deployment-sha)\" = '$EXPECTED_SHA' && test \"\$(git rev-parse HEAD)\" = '$EXPECTED_SHA' && test -f uv.lock && test -z \"\$(git status --short)\""
```

Expected: HEAD equals the one checked `EXPECTED_SHA`, even if `origin/main` later advances, and status is clean. Any mismatch stops and restarts Task 1 for a newly chosen SHA; never auto-follow remote main inside this acceptance run.

- [ ] **Step 3: Build the project-local environment**

```bash
ssh venus 'cd /home/junming/EIDP && bash deploy/linux/sync_venv.sh'
```

Expected: `.venv` and all caches below the root; no host-wide installation.

- [ ] **Step 4: Install approved runtime values securely**

ICT/operator creates `/home/junming/EIDP/.env` with mode 0600 using a secure interactive channel. It contains the exact URL/path/upload and identity-mode values. The proxy secret never appears in a shell command, transcript, Git, manifest or evidence file.

Trusted mode is preferred. If ICT cannot provide a stable user ID and PI explicitly accepts the local-account trust limitation, use `configured_fallback` plus one configured actor; otherwise stop.

- [ ] **Step 5: Install and verify the authoritative business seed**

`data/master.xlsx` is intentionally not tracked by Git. After explicit data-transfer authorization, record its local SHA-256, transfer only that data file through the approved channel to `/home/junming/EIDP/data/master.xlsx`, verify the remote digest matches, and set it read-only for the application owner. Do not transfer source code this way.

```bash
MASTER_SHA=$(shasum -a 256 data/master.xlsx | awk '{print $1}')
REMOTE_MASTER_SHA=$(ssh venus "cd /home/junming/EIDP && if test -f data/master.xlsx; then sha256sum data/master.xlsx | awk '{print \$1}'; fi")
test -z "$REMOTE_MASTER_SHA" || test "$REMOTE_MASTER_SHA" = "$MASTER_SHA"
if test -z "$REMOTE_MASTER_SHA"; then scp -p data/master.xlsx venus:/home/junming/EIDP/data/.master.xlsx.incoming; fi
if test -z "$REMOTE_MASTER_SHA"; then ssh venus "cd /home/junming/EIDP && test \"\$(sha256sum data/.master.xlsx.incoming | awk '{print \$1}')\" = '$MASTER_SHA' && mv data/.master.xlsx.incoming data/master.xlsx && chmod 0440 data/master.xlsx"; fi
ssh venus "cd /home/junming/EIDP && test \"\$(sha256sum data/master.xlsx | awk '{print \$1}')\" = '$MASTER_SHA'"
```

Expected: matching digests, same-filesystem atomic publish and read-only master. If a matching final file already exists, verify and reuse it; if a different final file exists, stop rather than overwrite. A disconnected partial upload remains only at `.master.xlsx.incoming`, never at the authoritative path. Record source/digest in runtime evidence.

- [ ] **Step 6: Bootstrap, seed, start and record deployment**

```bash
ssh venus 'cd /home/junming/EIDP && deploy/linux/eidpctl.sh db-bootstrap && deploy/linux/eidpctl.sh import-excel data/master.xlsx && deploy/linux/eidpctl.sh start && deploy/linux/eidpctl.sh status --json && deploy/linux/eidpctl.sh health && deploy/linux/eidpctl.sh write-manifest'
```

Expected: controller reads `run/expected-deployment-sha`; health is `ok`, PID identity is verified, and deployment manifest `deployed_commit == expected_deployment_commit == EXPECTED_SHA`. A temporarily newer `origin_main_commit` is recorded but blocks PI/READY at the final equality gate; it is never silently deployed or accepted. No secret appears in the manifest.

- [ ] **Step 7: Prove loopback and application restart**

```bash
ssh venus 'cd /home/junming/EIDP && deploy/linux/eidpctl.sh status --json && deploy/linux/eidpctl.sh restart && deploy/linux/eidpctl.sh status --json && deploy/linux/eidpctl.sh health'
```

Expected: controller JSON proves the configured listener address is `127.0.0.1` and reports the validated configured port; application stop/start succeeds. This is not machine-reboot autostart evidence.

### Task 3: ICT Proxy And Business-PC Network Gate

**Files:**
- ICT input: `deploy/linux/reverse-proxy-requirements.md`
- Runtime evidence: `/home/junming/EIDP/evidence/runtime/`

**Interfaces:**
- Consumes: healthy loopback app and exact ICT URL/path decision
- Produces: authenticated internal HTTPS/WebSocket access from an authorized business PC

- [ ] **Step 1: Hand the reviewed proxy contract to ICT**

ICT confirms WebSocket, Host/port/scheme, XSRF/CORS, body limits, health policy, auth/allowlist, identity capability and off-host destination. EIDP operators do not edit the proxy.

- [ ] **Step 2: Verify proxy liveness and WebSocket**

From an authorized business PC, open the exact HTTPS URL and keep an interaction alive beyond the idle timeout. Browser tools must show a successful `_stcore/stream` WebSocket and no prefix loop. Direct port 8502 is not reachable from the business network.

- [ ] **Step 3: Verify upload-size boundary**

Upload an approved near-200-MiB test PDF and an over-limit non-business payload. Expected: supported upload succeeds; oversized input fails visibly with no partial intake/blob.

- [ ] **Step 4: Capture redacted evidence**

Record URL/path, timestamp, deployment SHA, business network, WebSocket result and operator. Redact cookies, tokens, identity and proxy-secret headers; never retain an unredacted HAR.

### Task 4: Backup-Channel Rehearsal

**Files:**
- Runtime: `/home/junming/EIDP/backups/`
- Runtime: `/home/junming/EIDP/restore-drills/`
- Runtime evidence: `/home/junming/EIDP/evidence/runtime/`

**Interfaces:**
- Consumes: finalized package and ICT off-host pull/receipt
- Produces: an early verified receipt/restore rehearsal for matching code/schema; it does not close final DR acceptance

- [ ] **Step 1: Build and verify a finalized package**

```bash
test -n "$EXPECTED_SHA"
BACKUP_ID="acceptance-rehearsal-$(printf '%s' "$EXPECTED_SHA" | cut -c1-12)"
ssh venus "cd /home/junming/EIDP && deploy/linux/eidpctl.sh backup-package --backup-id '$BACKUP_ID' && deploy/linux/eidpctl.sh backup-verify 'backups/$BACKUP_ID'"
MANIFEST_SHA=$(ssh venus "cd /home/junming/EIDP && sha256sum 'backups/$BACKUP_ID/backup-manifest.v1.json' | awk '{print \$1}'")
```

Expected: finalized marker, complete checksums and SQLite integrity; no `.env`, cache, log or PID content.

- [ ] **Step 2: Have ICT pull and acknowledge the package**

ICT copies the finalized package to a different host/storage failure domain and returns a receipt bound to the package-manifest digest. Set `RECEIPT_ID` to that non-secret opaque receipt value. A project-owner SSH operator records one package-level receipt even when this pre-business package has zero source PDFs; per-document cleanup receipts are created only for source digests actually present. EIDP records receipt/audit metadata only.

```bash
[[ "$RECEIPT_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._:@+-]{0,127}$ ]]
printf '%s\n' "$RECEIPT_ID" | ssh venus "cd /home/junming/EIDP && IFS= read -r RECEIPT_ID && deploy/linux/eidpctl.sh source-backup-receipt-record 'backups/$BACKUP_ID' --manifest-sha '$MANIFEST_SHA' --external-receipt-id \"\$RECEIPT_ID\""
```

- [ ] **Step 3: Restore the off-host copy into an isolated project path**

ICT supplies the received package under `/home/junming/EIDP/restore-drills/incoming/$BACKUP_ID`.

```bash
printf '%s\n' "$RECEIPT_ID" | ssh venus "cd /home/junming/EIDP && IFS= read -r RECEIPT_ID && deploy/linux/eidpctl.sh restore-drill 'restore-drills/incoming/$BACKUP_ID' --target 'restore-drills/verified/$BACKUP_ID' --expected-manifest-sha '$MANIFEST_SHA' --off-host-receipt-id \"\$RECEIPT_ID\""
```

Expected: hashes/integrity and receipt/digest binding pass; matching code starts a temporary loopback smoke against restored data and shuts down; live data is untouched. Re-running the same backup ID verifies and returns the identical report; a conflicting non-empty target stops.

- [ ] **Step 4: Pair rollback evidence**

Verify report records deployed SHA, schema head, backup ID, manifest digest and off-host receipt. Rollback restores the pair, never code alone.

This rehearsal proves the channel before business acceptance. It is not the final recovery proof because later review/audit/export state does not yet exist.

### Task 5: Real Business Workflow And PI Acceptance

**Files:**
- Runtime evidence: `/home/junming/EIDP/evidence/runtime/`
- Update after evidence: `docs/governance/owner-release-signoff.md`
- Update after evidence: `docs/reports/current-release-status.md`

**Interfaces:**
- Consumes: authenticated proxy, canonical source, audited workflow, finalized export and recovery proof
- Produces: internal v1 acceptance packet and authorized conclusion

- [ ] **Step 1: Run the real browser workflow**

From an authorized business PC perform confirmed upload, served extraction, accept/correct/exclude, read-only master diff, external comparison, reasoned mismatch resolution, partial export and finalized download.

Expected: no SSH/VNC; no unverified/image/mismatch/audit-pending row enters workbook; manifest lists every disposition/reason.

- [ ] **Step 2: Verify audit and concurrency evidence**

Prove each decision has actor/source/action ID and exactly one JSONL projection. Upload an image PDF and prove it remains out of Excel. Hold one write lock and prove a second write shows busy and commits no business/audit state.

- [ ] **Step 3: Close the accepted-scope risk gate**

Expected: zero unresolved high-risk mismatch; every permanent exclusion has an approved reason. Partial export alone is insufficient.

- [ ] **Step 4: Build and restore the final accepted-state package**

Use the atomically generated `eidp.restore-evidence-expectation.v1` file for the accepted finalized export. Set/validate the finalized UI's `EXPORT_ID`, then derive one deterministic backup ID and restricted path; do not hand-write expectation JSON.

```bash
[[ "$EXPORT_ID" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$ ]]
EXPECTATIONS_PATH="evidence/runtime/exports/$EXPORT_ID.json"
FINAL_BACKUP_ID="acceptance-final-$EXPORT_ID"
ssh venus "cd /home/junming/EIDP && test -f '$EXPECTATIONS_PATH' && test ! -L '$EXPECTATIONS_PATH' && deploy/linux/eidpctl.sh backup-package --backup-id '$FINAL_BACKUP_ID' && deploy/linux/eidpctl.sh backup-verify 'backups/$FINAL_BACKUP_ID'"
FINAL_MANIFEST_SHA=$(ssh venus "cd /home/junming/EIDP && sha256sum 'backups/$FINAL_BACKUP_ID/backup-manifest.v1.json' | awk '{print \$1}'")
```

Have ICT pull that exact package, return it below `restore-drills/incoming/$FINAL_BACKUP_ID`, and provide `FINAL_RECEIPT_ID`. Validate/transport the receipt through stdin, record package/source receipts, and restore to the matching unique target:

```bash
[[ "$FINAL_RECEIPT_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._:@+-]{0,127}$ ]]
printf '%s\n' "$FINAL_RECEIPT_ID" | ssh venus "cd /home/junming/EIDP && IFS= read -r RECEIPT_ID && deploy/linux/eidpctl.sh source-backup-receipt-record 'backups/$FINAL_BACKUP_ID' --manifest-sha '$FINAL_MANIFEST_SHA' --external-receipt-id \"\$RECEIPT_ID\""
printf '%s\n' "$FINAL_RECEIPT_ID" | ssh venus "cd /home/junming/EIDP && IFS= read -r RECEIPT_ID && deploy/linux/eidpctl.sh restore-drill 'restore-drills/incoming/$FINAL_BACKUP_ID' --target 'restore-drills/verified/$FINAL_BACKUP_ID' --expected-manifest-sha '$FINAL_MANIFEST_SHA' --off-host-receipt-id \"\$RECEIPT_ID\" --acceptance-expectations '$EXPECTATIONS_PATH'"
```

The report must prove the restored copy contains the accepted IDs/hashes and exactly one audit projection per action.

- [ ] **Step 5: Reconfirm the accepted source has not advanced**

Immediately before signature, reload the pinned SHA and require protected main plus both checks still describe that exact commit:

```bash
EXPECTED_SHA=$(ssh venus 'cat /home/junming/EIDP/run/expected-deployment-sha')
git fetch --prune origin
test "$(git rev-parse origin/main)" = "$EXPECTED_SHA"
REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner')
CHECKS=$(gh api "repos/$REPO/commits/$EXPECTED_SHA/check-runs?per_page=100" --jq '[.check_runs[] | select(.name == "Python quality gates" or .name == "Ship gate contract")] | group_by(.name) | map(sort_by(.completed_at // .started_at) | last)[] | [.name, .conclusion, .head_sha] | @tsv')
test "$(printf '%s\n' "$CHECKS" | wc -l | tr -d ' ')" -eq 2
printf '%s\n' "$CHECKS" | awk -v sha="$EXPECTED_SHA" '$2 != "success" || $3 != sha { exit 1 }'
```

If `origin/main` advanced, retain `NOT_READY`, do not sign, and repeat the affected Venus/business/restore gates on the new checked SHA. Readiness never transfers from accepted commit A to untested commit B.

- [ ] **Step 6: Obtain PI/owner sign-off**

The authorized PI/owner signs the acceptance record. An implementation agent cannot substitute judgment or fabricate it.

### Task 6: Publish The Evidence-Based Release Conclusion

**Files:**
- Modify: `docs/governance/owner-release-signoff.md`
- Modify: `docs/reports/current-release-status.md`
- Modify: `docs/release/v1-known-limitations.md`
- Modify if evidence requires: `docs/runbooks/venus-init-and-acceptance.md`

**Interfaces:**
- Consumes: completed evidence and PI sign-off
- Produces: protected-main status update without hidden caveats

- [ ] **Step 1: Reconcile every mandatory gate and source SHA**

Fetch once more before editing. `origin/main` must still equal the signed `EXPECTED_SHA`; if it changed, stop and keep `NOT_READY`. Link each runbook gate to fresh evidence. Missing off-host restore, business-PC chain, audit evidence or signature keeps `NOT_READY`. If the evidence PR later becomes out-of-date because another code PR merges, do not update/merge it until the new code SHA is re-accepted; strict branch protection is an additional guard, not a substitute for this check.

- [ ] **Step 2: Update status honestly**

Change to `READY` only if every mandatory gate passes. Otherwise retain `NOT_READY`; record OCR/manual and fallback limitations explicitly.

- [ ] **Step 3: Run governance contracts**

```bash
uv run pytest tests/unit/test_governance_rolling_fiscal_year_contract.py tests/unit/test_linux_web_release_contract.py tests/unit/test_ci_workflow_contract.py -v
git diff --check
```

Expected: all pass.

- [ ] **Step 4: Commit and open the evidence PR**

```bash
git add docs/governance/owner-release-signoff.md docs/reports/current-release-status.md docs/release/v1-known-limitations.md docs/runbooks/venus-init-and-acceptance.md
git commit -m "docs: record Venus v1 acceptance evidence" -m "Goals: G2, G9, G13, G14, G15"
```

Open a protected-main PR, require both checks and owner review, and merge only with explicit authorization. Never commit secrets or unredacted runtime evidence.

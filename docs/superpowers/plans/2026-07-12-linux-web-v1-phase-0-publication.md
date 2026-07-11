# Linux/Web v1 Phase 0 Publication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the consolidated Linux/Web mainline through a protected GitHub PR and obtain fresh evidence from both required CI checks before any new product implementation or Venus initialization.

**Architecture:** The local `main` remains the sole product line. A short-lived remote PR branch transports the already committed history to protected `origin/main`; it is not a second product track. CI failure is treated as observed evidence and blocks merge until a failure-specific TDD fix is prepared and rerun.

**Tech Stack:** Git, GitHub CLI, GitHub Actions, uv, Python 3.12, Ruff, Bandit, mypy, pytest

## Global Constraints

- Do not push directly to `origin/main`, force-push, or initialize Venus.
- Do not copy a local worktree/archive to Venus; future deployment comes from protected `origin/main` only.
- Required GitHub check names are exactly `Python quality gates` and `Ship gate contract`.
- Keep Windows retired; do not restore Windows packaging or Stage 6 assets to make CI green.
- `main` is the sole product definition; `pr/linux-web-v1-mainline-20260712` is transport-only and deleted after merge.
- Any CI failure stops merge. Diagnose from the real run; do not assume or pre-emptively edit unrelated code.

---

### Task 1: Reproduce Both CI Jobs Locally

**Files:**
- Verify: `.github/workflows/ci.yml`
- Verify: `uv.lock`
- Verify: `tests/unit/test_linux_web_release_contract.py`
- Verify: `tests/unit/test_ci_workflow_contract.py`

**Interfaces:**
- Consumes: local `main` containing the approved design and plan documents
- Produces: a clean-tree evidence record showing all commands required by both GitHub jobs pass locally

- [ ] **Step 1: Verify source topology and cleanliness**

Run:

```bash
git fetch --prune origin
git status --short --branch
git rev-list --left-right --count origin/main...main
git merge-base --is-ancestor origin/main main
test -f uv.lock
```

Expected: porcelain is empty, the second number is positive, `origin/main` is an ancestor, and `uv.lock` exists.

- [ ] **Step 2: Reproduce the locked dependency installation**

Run:

```bash
uv sync --locked --extra dev --extra scraper-basic --extra pdf
```

Expected: exit 0 with no lockfile change.

- [ ] **Step 3: Reproduce `Python quality gates`**

Run each command separately:

```bash
uv run ruff check .
uv run --with bandit bandit -q --severity-level high -r src/eidp scripts
uv run mypy src
uv run pytest --cov=src/eidp --cov-report=term --cov-fail-under=80
```

Expected: every command exits 0 and coverage is at least 80%.

- [ ] **Step 4: Reproduce `Ship gate contract`**

Run:

```bash
uv run pytest tests/unit/test_linux_web_release_contract.py tests/unit/test_web_write_lock_contract.py tests/unit/test_app_root_paths.py tests/integration/test_linux_web_e2e_chain.py -q
```

Expected: exit 0 with the exact Linux/Web integration assertions passing.

- [ ] **Step 5: Verify no local artifact changed the tree**

Run:

```bash
git status --short
```

Expected: no output. If any tracked file changed, stop and identify the producing command before publication.

### Task 2: Publish A Transport Branch And Open The PR

**Files:**
- Read: `docs/superpowers/specs/2026-07-12-linux-web-v1-venus-design.md`
- Read: `docs/runbooks/venus-init-and-acceptance.md`
- Read: `deploy/linux/reverse-proxy-requirements.md`

**Interfaces:**
- Consumes: Task 1 green local evidence and clean `main`
- Produces: GitHub PR `pr/linux-web-v1-mainline-20260712 -> main`

- [ ] **Step 1: Confirm the remote branch does not already exist**

Run:

```bash
git ls-remote --exit-code --heads origin pr/linux-web-v1-mainline-20260712
```

Expected: exit 2 and no matching ref. If it exists, stop rather than overwrite it.

- [ ] **Step 2: Push local `main` to the transport branch**

Run only after explicit external-write authorization:

```bash
REMOTE_MAIN=$(git ls-remote origin refs/heads/main | cut -f1)
TRACKED_MAIN=$(git rev-parse origin/main)
test "$REMOTE_MAIN" = "$TRACKED_MAIN"
git push origin main:refs/heads/pr/linux-web-v1-mainline-20260712
```

Expected: remote main still equals the freshly fetched tracking SHA, then a new transport branch is created; `origin/main` remains unchanged. If the equality test fails, fetch/reconcile and stop rather than pushing stale topology.

- [ ] **Step 3: Open the protected-main PR**

Run:

```bash
gh pr create --base main --head pr/linux-web-v1-mainline-20260712 --title "feat: consolidate Linux/Web v1 mainline" --body $'Summary:\n- retire the Windows product baseline\n- publish the Streamlit/SQLite Linux-Web integration and extraction core\n- add the approved Venus deployment, proxy, and acceptance specification\n\nVerification:\n- uv run ruff check .\n- uv run --with bandit bandit -q --severity-level high -r src/eidp scripts\n- uv run mypy src\n- uv run pytest --cov=src/eidp --cov-report=term --cov-fail-under=80\n- Linux/Web ship-gate contract suite\n\nRelease status remains NOT_READY; this PR does not deploy Venus.\n\nGoals: G1, G2, G4, G6, G9, G13, G14, G15'
```

Expected: one open PR targeting `main`; no merge occurs.

### Task 3: Observe Real CI And Gate The Merge

**Files:**
- Diagnose only if needed: `.github/workflows/ci.yml`
- Diagnose only if needed: files named by the failed GitHub log

**Interfaces:**
- Consumes: open PR from Task 2
- Produces: fresh GitHub evidence for both required checks, or a concrete blocked handoff containing the failed run log

- [ ] **Step 1: Watch required checks to completion**

Run:

```bash
gh pr checks pr/linux-web-v1-mainline-20260712 --watch --interval 10
```

Expected: `Python quality gates` and `Ship gate contract` both report `pass`.

- [ ] **Step 2: If a check fails, capture the actual failed log**

Run only on failure:

```bash
FAILED_RUN_ID=$(gh run list --branch pr/linux-web-v1-mainline-20260712 --status failure --limit 1 --json databaseId --jq '.[0].databaseId')
gh run view "$FAILED_RUN_ID" --log-failed
```

Expected: a non-empty log naming the failing command/test. Stop the merge. Reproduce that exact command locally and write a failure-specific TDD plan; do not guess a fix inside this publication task.

- [ ] **Step 3: Record the two check results**

Run:

```bash
gh pr checks pr/linux-web-v1-mainline-20260712
```

Expected: both required checks are green and no required check is pending/skipped.

### Task 4: Merge With Approval And Reconcile Local Main

**Files:**
- No source edits

**Interfaces:**
- Consumes: owner-approved PR with both required checks green
- Produces: `origin/main` containing the complete Linux/Web baseline; local `main` fast-forwarded to the same commit

- [ ] **Step 1: Obtain explicit merge authorization**

Expected: owner/authorized maintainer confirms merge. Without it, stop with the PR open.

- [ ] **Step 2: Merge and delete the transport branch**

Run:

```bash
gh pr merge pr/linux-web-v1-mainline-20260712 --merge --delete-branch
```

Expected: PR state `MERGED`; protected `main` updated through GitHub.

- [ ] **Step 3: Fast-forward the local sole mainline**

Run:

```bash
git fetch --prune origin
git switch main
git merge --ff-only origin/main
git rev-list --left-right --count origin/main...main
git status --short --branch
```

Expected: divergence `0 0`, clean tree, and no long-lived product branch.

- [ ] **Step 4: Preserve the release conclusion**

Run:

```bash
rg -n "NOT_READY" docs/reports/current-release-status.md docs/runbooks/venus-init-and-acceptance.md
```

Expected: publication did not claim Venus deployment or v1 readiness.

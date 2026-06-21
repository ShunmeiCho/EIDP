# EIDP v1.0 Release Admin Checklist

Updated: 2026-06-21

This checklist is for local release administration only. It does not replace
Windows side-by-side validation, the owner real cycle, or the release-scope
decision for FY2026/R8 publication lag.

## Do Not Proceed If

- Local `main` is not synced to PR #8 merge commit
  `723a5072f63e8a874bef85cc52d869f5e6daff15` or a later verified `main`
  commit.
- The selected release candidate has not been Windows side-by-side validated
  after its last code/package change. Current package/canary candidate is v547
  at commit `86c848f68e1dbde85c9b6422cfc827149940e02a`; non-Windows gates and
  Windows side-by-side canary passed, but v547 is still below the
  strict/Excel-ready release gate.
- The selected release candidate has no valid OCR runtime proof while OCR is in
  release scope. Current v546 did not restore or validate an OCR add-on/runtime
  proof; if OCR is in scope, attach a valid OCR add-on proof before approval.
- The owner real cycle and evidence bundle are missing.
- The strict FY2026/R8 gate is below 60% and there is no explicit
  `publication_lag` release-exception approval.
- The Stage 6 return verifier has not checked the canonical owner decision
  briefs for `publication_lag` and OCR scope.
- PDF acquisition depends on broad SERP queries such as `school name + PDF`.
  v1.0 acquisition must start from high-trust official indexes and expand in
  auditable layers: prefectural confirmed-institution lists, registered
  `SchoolSite` / exact official overrides, bounded same-site disclosure pages,
  then PDF body/OCR verification. External search providers, including
  `agent-reach` wrappers, may only propose official URL/index candidates and
  must not be used as a direct PDF finder.
- The roughly 700-university scope is being claimed as complete. The current
  v533 evidence proves the MEXT T0 official source-catalog/package gate with
  769 university rows; it does not prove the university target-document
  discovery lane, extraction lane, or Excel mapping.
- The signed tag command would use an unsigned or unknown signing identity.

## Local Preflight

Run from the repository root:

```bash
git status --short --untracked-files=all
git rev-parse HEAD
gh pr view 8 --json state,mergedAt,mergeCommit,headRefOid,baseRefName,url
```

Expected:

- there are no tracked modifications;
- untracked local reference files such as `UI-example/` are not included in the
  release package;
- `HEAD` is `723a5072f63e8a874bef85cc52d869f5e6daff15` or a later verified
  `main` commit;
- PR #8 is `MERGED` with merge commit
  `723a5072f63e8a874bef85cc52d869f5e6daff15`.

Confirm the current local package/source evidence:

```bash
shasum -a 256 dist/eidp-windows-v547.zip
cat dist/eidp-windows-v547.zip.sha256
uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v547.zip --json
uv run python scripts/run_non_windows_release_gates.py \
  dist/eidp-windows-v547.zip \
  --skip-full-unit \
  --json

# Only if OCR is in the selected release scope and the add-on ZIP is present:
test -f dist/eidp-ocr-addon-windows-v497-smoke.zip
shasum -a 256 dist/eidp-ocr-addon-windows-v497-smoke.zip
cat dist/eidp-ocr-addon-windows-v497-smoke.zip.sha256
uv run python scripts/verify_windows_distribution.py \
  dist/eidp-windows-v547.zip \
  --ocr-addon dist/eidp-ocr-addon-windows-v497-smoke.zip \
  --json
```

Expected ZIP SHA256:

```text
f167e17b89f0ff96a45c817abcfd0403a2d487eddf3fb3a85a73d866b351de4b
```

Expected OCR add-on SHA256, if OCR is in v1.0 scope:

```text
3d0d03d4b49eb1bf5d8acc2030c00189702519d01ac80886bb7507a1d619450f
```

## Signing Preflight

Current repository signing is SSH-based. Verify it before creating the real
release tag:

```bash
git config --show-origin --get user.signingkey
git config --show-origin --get gpg.format
git config --show-origin --get gpg.ssh.allowedSignersFile
test -f .git/eidp_allowed_signers
```

Expected:

- `gpg.format` is `ssh`;
- `user.signingkey` points to the intended public key;
- `.git/eidp_allowed_signers` exists and contains the matching public key.

Do not create `v1.0` until the release gates below are complete.

## Local Storage Hygiene

Generated Windows ZIPs are large. Keep only the selected release candidate, its
`.sha256` sidecar, the `dist/eidp-windows.zip` latest alias, and `wheelhouse/`
unless an older package is actively needed for side-by-side evidence transfer.

After the v547 rebuild, local package gates, and Windows side-by-side canary,
superseded generated artifacts no longer needed for the current evidence lane
were pruned. Retained core package artifacts on the external SSD are v546
fallback, v547 current, the latest alias `dist/eidp-windows.zip`, and the
current owner-docs ZIP. Windows retained active v527, fallback v546, and
current v547 while v545 transfer ZIPs and the v545 side-by-side directory were
removed.
AppleDouble `._*` files created by macOS on the external volume must be removed
from `dist/` before package verification or transfer.

On the current Mac workstation, generated artifacts are stored on the external
SSD mounted at `/Volumes/M1nG-ssd`:

```text
dist -> /Volumes/M1nG-ssd/EIDP-artifacts/dist
logs -> /Volumes/M1nG-ssd/EIDP-artifacts/logs
```

Keep those symlinks in place for local builds and release gates so future ZIPs
and gate logs do not consume the internal SSD. If the external SSD is not
mounted, do not rebuild Windows ZIPs or long-running gate logs until it is
reattached.

## Owner Sign-off Boundary

Owner/operator sign-off can be short. It should confirm the selected release
ID, ZIP, SHA256, source commit, release decision (`READY`, `RC_ONLY`, or
`NOT_READY`), v1 scope, known limitations, and any approved exception.

Do not ask the owner to manually reproduce CI logs, wheelhouse counts, ZIP entry
counts, parser fixture details, or JSONL evidence checks. Those remain release
engineering evidence and must be referenced by the Release Summary, Stage 6
evidence bundle, Windows canary/real-cycle evidence, and this checklist.

`publication_lag` approval may support at most `RC_ONLY` after all required
evidence is complete. It must not allow old-year, year-unknown,
school-mismatch, low-confidence, or unresolved program-change rows into final
Excel output.

## Release Gates

Before tagging, attach or reference:

- v547 package/source and CI evidence:
  `docs/reports/2026-06-21-v547-package-gates.md`,
  `logs/eidp-windows-v547-distribution-verify-20260621.json`,
  `logs/eidp-windows-v547-release-gates-20260621.json`, and
  `dist/eidp-windows-v547.zip`. v547 package SHA256:
  `f167e17b89f0ff96a45c817abcfd0403a2d487eddf3fb3a85a73d866b351de4b`;
- v547 Windows bounded canary evidence:
  `docs/reports/2026-06-21-v547-windows-canary.md`,
  `logs/win-v547-86c848f-canary/20260621_053425-summary.json`,
  `logs/win-v547-86c848f-canary/stage6-evidence-20260621-054545.zip`,
  `logs/win-v547-86c848f-canary/stage6-evidence-verify-20260621-144556.json`,
  `logs/win-v547-86c848f-canary/stage6-evidence-verify-mac-20260621.json`,
  `logs/win-v547-86c848f-canary/win-v547-cleanup-20260621.json`, and
  `logs/win-v547-86c848f-canary/win-v547-explicit-dir-cleanup-20260621.json`;
- v546 package/source and CI evidence:
  `docs/reports/2026-06-21-v546-rca-summary-package-gates.md`,
  `logs/eidp-windows-v546-distribution-verify-20260621.json`,
  `logs/eidp-windows-v546-release-gates-20260621.json`,
  `dist/eidp-windows-v546.zip`, and CI run `27892572590` for source commit
  `6301605`. v546 package SHA256:
  `ece0bbf3c1e96f3bf5be6dd553f3a547244edf15ad65ea2bc38c61600887ecfd`;
- v546 Windows bounded canary evidence:
  `docs/reports/2026-06-21-v546-rca-summary-windows-canary.md`,
  `logs/win-v546-6301605-canary/20260621_042630-summary.json`,
  `logs/win-v546-6301605-canary/stage6-evidence-20260621-043811.zip`,
  `logs/win-v546-6301605-canary/stage6-evidence-verify-20260621-133825.json`,
  `logs/win-v546-6301605-canary/stage6-evidence-verify-mac-20260621.json`,
  and `logs/win-v546-6301605-canary/win-v546-cleanup-20260621.json`;
- v545 package/source and CI evidence:
  `docs/reports/2026-06-21-v545-disclosure-priority-windows-canary.md`,
  `logs/eidp-windows-v545-distribution-verify-20260621.json`, and CI run
  `27888117592` for packaged source commit `f3eb166`;
- v545 Windows bounded canary evidence:
  `logs/win-v545-f3eb166-canary/20260621_003033-summary.json`,
  `logs/win-v545-f3eb166-canary/stage6-evidence-20260621-004156.zip`,
  `logs/win-v545-f3eb166-canary/stage6-evidence-verify-20260621-094157.json`,
  `logs/win-v545-f3eb166-canary/stage6-evidence-verify-mac-20260621.json`,
  and `docs/reports/2026-06-21-v545-disclosure-priority-windows-canary.md`;
- v545 false-reject RCA evidence:
  `docs/reports/2026-06-21-v545-false-reject-audit-packet.md`,
  `docs/reports/2026-06-21-v545-false-reject-review-sheet.csv`, and
  `docs/reports/2026-06-21-v545-false-reject-review-validation.json`;
- v547 false-reject review guidance evidence:
  `docs/reports/2026-06-21-v547-false-reject-review-sheet.csv`,
  `docs/reports/2026-06-21-v547-false-reject-review-summary.md`,
  `docs/reports/2026-06-21-v547-false-reject-review-worklist.md`,
  `docs/reports/2026-06-21-v547-false-reject-review-validation.json`, and
  `docs/reports/2026-06-21-v547-false-reject-review-validation-summary.md`;
- previous v540 package/non-Windows gate and CI evidence:
  `docs/reports/2026-06-20-v540-owner-briefs-windows-canary.md`,
  `logs/win-v540-stage6-v540-verify-windows-distribution-20260620.json`, and
  CI run `27871865340`;
- v540 Windows bounded canary evidence:
  `logs/win-v540-fbdd0bd-canary/last_run.json`,
  `logs/win-v540-fbdd0bd-canary/20260620_131759-summary.json`,
  `logs/win-v540-fbdd0bd-canary/stage6-evidence-20260620-133325.zip`,
  `logs/win-v540-fbdd0bd-canary/stage6-evidence-verify-20260620-223357.json`,
  and `logs/win-v540-fbdd0bd-canary/stage6-evidence-verify-mac-20260620.json`;
- canonical owner decision briefs:
  `docs/release/owner-decisions/publication-lag.md` when the release path uses
  `publication_lag`, and `docs/release/owner-decisions/ocr-scope.md` for the
  selected OCR scope;
- `scripts/verify_stage6_return.py --json` output whose `inputs` include
  `publication_lag_decision_brief` for the `publication_lag` path and
  `ocr_scope_decision_brief` for the selected OCR scope, plus `owner_signoff`,
  `expected_package_sha256`, and `expected_source_commit` when the short owner
  sign-off form is used;
- v533 package/non-Windows gate JSON:
  `logs/win-v533-stage6-v533-non-windows-release-gates-20260620.json`;
- v533 MEXT authority-index package report:
  `docs/reports/2026-06-20-v533-mext-authority-index-package.md`;
- v533 Windows side-by-side smoke:
  `docs/reports/2026-06-20-v533-full-windows-side-by-side-smoke.md`;
- v533 side-by-side evidence ZIP and verifier:
  `logs/win-v533-stage6/stage6-evidence-20260619-180429.zip`,
  `logs/win-v533-stage6/stage6-evidence-verify-20260620-030444.json`;
- v533 operator-side handoff docs:
  `docs/runbooks/eidp-v533-owner-request-20260620.txt`;
- v532 package/non-Windows gate JSON:
  `logs/win-v532-main-post-merge-release-gates-20260619.json`;
- v532 Windows connectivity recheck:
  `docs/reports/2026-06-20-v532-windows-connectivity-recheck.md`;
- v532 Windows side-by-side smoke:
  `docs/reports/2026-06-20-v532-full-windows-side-by-side-smoke.md`;
- v532 side-by-side evidence ZIP and manifest:
  `logs/win-v532-stage6/win-v532-stage6-side-by-side-evidence-20260620.zip`,
  `logs/win-v532-stage6/win-v532-stage6-side-by-side-evidence-manifest-20260620.json`;
- v532 operator-side handoff docs:
  `docs/runbooks/00-READ-ME-FIRST-v532.txt`,
  `docs/runbooks/eidp-v532-owner-request-20260620.txt`, and
  `docs/runbooks/eidp-v532-owner-return-fill-sheet.md`;
- v532 Windows side-by-side validator JSON if v532 is selected for release;
- v532 active-task recovery / lock proof showing the active task still points
  to the expected active v527 lane;
- v532 Windows UI smoke notes if v532 is selected for release;
- v532 OCR runtime proof, if OCR remains in v1.0 scope;
- v532 Excel smoke proof if v532 is selected for release;
- v532 bounded weekly canary proof if v532 is selected for release;
- v532 Stage 6 evidence ZIP and evidence verifier JSON if v532 is selected
  for release;
- completed owner real-cycle template;
- evidence ZIP and evidence verification JSON;
- ManualActionLog / JSONL audit proof: audit page status, `manual_action_log`
  count, outbox count before/after flush, and action_id consistency;
- Excel preview/export proof: output workbook path or redacted workbook
  metadata, plus consistency evidence that the Excel-ready coverage in the
  owner template matches the current DB/run metrics;
- `logs/mature-year-acquisition-proof-fy2025-release-exception-v497-20260519.json`
  if the approved release path is `publication_lag`;
- if OCR is in release scope, `dist/eidp-ocr-addon-windows-v497-smoke.zip`
  SHA256 plus Windows runtime / image-write proof; otherwise a written
  release-scope decision that OCR is optional/manual fallback for v1.0;
- explicit release-scope approval if FY2026/R8 remains below the strict gate.

Current v547 package and Windows bounded canary evidence is recorded in
`docs/reports/2026-06-21-v547-package-gates.md`,
`docs/reports/2026-06-21-v547-windows-canary.md`,
`logs/eidp-windows-v547-distribution-verify-20260621.json`,
`logs/eidp-windows-v547-release-gates-20260621.json`, and
`logs/win-v547-86c848f-canary/stage6-evidence-verify-mac-20260621.json`.
The v547 package/source commit is
`86c848f68e1dbde85c9b6422cfc827149940e02a`, and the v547 package SHA256 is
`f167e17b89f0ff96a45c817abcfd0403a2d487eddf3fb3a85a73d866b351de4b`.
v547 still remains below the strict/Excel-ready release gate with
`ship_gate_status=below_gate`; it is not owner/operator real-cycle sign-off and
not v1.0 approval.

Previous v546 Windows bounded canary evidence is recorded in
`docs/reports/2026-06-21-v546-rca-summary-windows-canary.md`,
`logs/eidp-windows-v546-distribution-verify-20260621.json`, and
`logs/win-v546-6301605-canary/stage6-evidence-verify-mac-20260621.json`.
The v546 package/source commit is
`63016054f948b1f4f285c3c822197f76c25b4b7d`, and the v546 package SHA256 is
`ece0bbf3c1e96f3bf5be6dd553f3a547244edf15ad65ea2bc38c61600887ecfd`.
v546 also remains below the strict/Excel-ready release gate with
`ship_gate_status=below_gate`; it is not owner/operator real-cycle sign-off and
not v1.0 approval.

## Final Commands

Only after all release gates pass:

```bash
git fetch origin main --tags
git checkout main
git pull --ff-only origin main
git tag -s v1.0 -m "v1.0"
git tag -v v1.0
git push origin v1.0
```

If `git tag -v v1.0` fails, delete only the local failed tag and fix signing
configuration before retrying:

```bash
git tag -d v1.0
```

Do not push an unsigned replacement tag.

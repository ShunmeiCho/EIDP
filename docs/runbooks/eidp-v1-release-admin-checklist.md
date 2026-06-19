# EIDP v1.0 Release Admin Checklist

Updated: 2026-06-20

This checklist is for local release administration only. It does not replace
Windows side-by-side validation, the owner real cycle, or the release-scope
decision for FY2026/R8 publication lag.

## Do Not Proceed If

- Local `main` is not synced to PR #8 merge commit
  `723a5072f63e8a874bef85cc52d869f5e6daff15` or a later verified `main`
  commit.
- The selected release candidate has not been Windows side-by-side validated
  after its last code/package change. Current v532 has completed Windows
  side-by-side smoke, but any later code/package rebuild must repeat it.
- The selected release candidate has no valid OCR runtime proof while OCR is in
  release scope. Current v532 side-by-side OCR validation failed because the
  OCR add-on is missing; v526 remains the latest package with complete OCR
  runtime proof.
- The owner real cycle and evidence bundle are missing.
- The strict FY2026/R8 gate is below 60% and there is no explicit
  `publication_lag` release-exception approval.
- PDF acquisition depends on broad SERP queries such as `school name + PDF`.
  v1.0 acquisition must start from high-trust official indexes and expand in
  auditable layers: prefectural confirmed-institution lists, registered
  `SchoolSite` / exact official overrides, bounded same-site disclosure pages,
  then PDF body/OCR verification. External search providers, including
  `agent-reach` wrappers, may only propose official URL/index candidates and
  must not be used as a direct PDF finder.
- The roughly 700-university scope is being claimed as complete. The current
  v532 evidence proves the vocational/specialty-school lane; it does not prove
  an equivalent university official-index catalog, parser layer, target-document
  discovery lane, or Excel mapping.
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

Confirm the current package evidence:

```bash
shasum -a 256 dist/eidp-windows-v532.zip
cat dist/eidp-windows-v532.zip.sha256
uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v532.zip --json
uv run python scripts/run_non_windows_release_gates.py \
  dist/eidp-windows-v532.zip \
  --allow-docs-only-stale-package \
  --keep-going \
  --json

# Only if OCR is in the selected release scope and the add-on ZIP is present:
test -f dist/eidp-ocr-addon-windows-v497-smoke.zip
shasum -a 256 dist/eidp-ocr-addon-windows-v497-smoke.zip
cat dist/eidp-ocr-addon-windows-v497-smoke.zip.sha256
uv run python scripts/verify_windows_distribution.py \
  dist/eidp-windows-v532.zip \
  --ocr-addon dist/eidp-ocr-addon-windows-v497-smoke.zip \
  --json
```

Expected ZIP SHA256:

```text
9743cc65c21ada06b6a1d6c8b50ba67cdaffa4f3942256ccd072d4469fa0d6c7
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

After the v532 `main` rebuild, superseded generated ZIPs
`dist/eidp-windows-v527.zip` through `dist/eidp-windows-v531.zip` and their
`.sha256` sidecars were deleted. `dist/` was reduced from about 1.5 GB to about
546 MB.

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

## Release Gates

Before tagging, attach or reference:

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

Current v532 local package evidence is recorded in
`logs/win-v532-main-post-merge-release-gates-20260619.json`. Current v532
Windows side-by-side smoke evidence is summarized in
`docs/reports/2026-06-20-v532-full-windows-side-by-side-smoke.md`. The v532
owner/operator request is prepared at
`docs/runbooks/eidp-v532-owner-request-20260620.txt`; it is a handoff aid, not
release approval.

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

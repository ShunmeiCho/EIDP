# EIDP v1.0 Release Admin Checklist

Updated: 2026-05-19

This checklist is for local release administration only. It does not replace
Windows side-by-side validation, the owner real cycle, or the release-scope
decision for FY2026/R8 publication lag.

## Do Not Proceed If

- PR #2 is not clean or either required check is not green.
- v497 has not been Windows side-by-side validated.
- The owner real cycle and evidence bundle are missing.
- The strict FY2026/R8 gate is below 60% and there is no explicit
  `publication_lag` release-exception approval.
- The signed tag command would use an unsigned or unknown signing identity.

## Local Preflight

Run from the repository root:

```bash
git status --short
git rev-parse HEAD
gh pr view 2 --json state,mergeStateStatus,headRefOid,statusCheckRollup,url
```

Expected:

- working tree is clean;
- PR #2 is `OPEN` until the final merge step;
- `mergeStateStatus` is `CLEAN`;
- `Python quality gates` and `Ship gate contract` are `SUCCESS`.

Confirm the current package evidence:

```bash
shasum -a 256 dist/eidp-windows-v497.zip
cat dist/eidp-windows-v497.zip.sha256
uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v497.zip --json
```

Expected ZIP SHA256:

```text
11807eaff0b87c11c8850e2bb339294c410cb6d78d39a04254c145ebba038075
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

## Release Gates

Before merging or tagging, attach or reference:

- v497 Windows side-by-side validator JSON;
- v497 Windows UI smoke notes;
- completed owner real-cycle template;
- evidence ZIP and evidence verification JSON;
- `logs/mature-year-acquisition-proof-fy2025-release-exception-v497-20260519.json`
  if the approved release path is `publication_lag`;
- explicit release-scope approval if FY2026/R8 remains below the strict gate.

## Final Commands

Only after all release gates pass:

```bash
gh pr merge 2 --rebase
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

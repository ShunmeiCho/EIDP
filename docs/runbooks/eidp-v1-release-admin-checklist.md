# EIDP v1.0 Release Admin Checklist

Updated: 2026-06-19

This checklist is for local release administration only. It does not replace
Windows side-by-side validation, the owner real cycle, or the release-scope
decision for FY2026/R8 publication lag.

## Do Not Proceed If

- PR #8 is not clean or either required check is not green.
- The selected release candidate has not been Windows side-by-side validated
  after its last code/package change. Current local v530 is package/source
  verified on macOS, but the latest complete Windows side-by-side smoke remains
  v526. v530 must not be promoted until Windows side-by-side validation is
  repeated or the release scope explicitly stays on v526.
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
- OCR is included in the v1.0 release scope but the Windows OCR runtime proof
  or OCR add-on SHA/runtime verifier is missing for the selected candidate.
  Current v526 has fresh Windows OCR runtime proof; the local v530 preflight
  did not include an OCR add-on ZIP because `dist/eidp-ocr-addon-windows-v497-smoke.zip`
  is not present in this checkout.
- The signed tag command would use an unsigned or unknown signing identity.

## Local Preflight

Run from the repository root:

```bash
git status --short
git rev-parse HEAD
gh pr view 8 --json state,mergeStateStatus,headRefOid,statusCheckRollup,url
```

Expected:

- working tree is clean;
- PR #8 is `OPEN` until the final merge step;
- `mergeStateStatus` is `CLEAN`;
- `Python quality gates` and `Ship gate contract` are `SUCCESS`.
- remote PR head matches the source commit selected for release. If the local
  branch contains unpublished commits, PR checks do not cover that candidate
  until the branch is pushed and CI is green on the new head.

Confirm the current package evidence:

```bash
shasum -a 256 dist/eidp-windows-v530.zip
cat dist/eidp-windows-v530.zip.sha256
uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v530.zip --json
uv run python scripts/run_non_windows_release_gates.py \
  dist/eidp-windows-v530.zip \
  --allow-docs-only-stale-package \
  --keep-going \
  --json

# Only if OCR is in the selected release scope and the add-on ZIP is present:
test -f dist/eidp-ocr-addon-windows-v497-smoke.zip
shasum -a 256 dist/eidp-ocr-addon-windows-v497-smoke.zip
cat dist/eidp-ocr-addon-windows-v497-smoke.zip.sha256
uv run python scripts/verify_windows_distribution.py \
  dist/eidp-windows-v530.zip \
  --ocr-addon dist/eidp-ocr-addon-windows-v497-smoke.zip \
  --json
```

Expected ZIP SHA256:

```text
6344e6b9c2fea850cb50425410f2e0a5ad9c6626ff31fca9fee5f9f8014604a6
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

## Release Gates

Before merging or tagging, attach or reference:

- v530 package/non-Windows gate JSON:
  `logs/win-v530-stage6-v530-non-windows-release-gates-20260619.json`
  plus the docs-only stale replay
  `logs/win-v530-stage6-v530-post-docs-only-gates-20260619.json`;
- v530 Windows side-by-side validator JSON if v530 is selected for release;
- v530 active-task recovery / lock proof showing the active task still points
  to the expected v485 lane;
- v530 Windows UI smoke notes if v530 is selected for release;
- v530 OCR runtime proof, if OCR remains in v1.0 scope;
- v530 Excel smoke proof if v530 is selected for release;
- v530 bounded weekly canary proof if v530 is selected for release;
- v530 Stage 6 evidence ZIP and evidence verifier JSON if v530 is selected
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

Current v530 local package evidence is recorded in
`logs/win-v530-stage6-v530-non-windows-release-gates-20260619.json`; it is not
a Windows side-by-side smoke. Current v526 side-by-side evidence is summarized in
`docs/reports/2026-05-20-v526-extracted-confirmation-package.md`.
The v526 owner/operator request is prepared at
`docs/runbooks/eidp-v526-owner-request-20260520.txt`; it is a handoff aid, not
release approval.

## Final Commands

Only after all release gates pass:

```bash
gh pr merge 8 --rebase
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

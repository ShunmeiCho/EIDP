# EIDP v1.0 Release Admin Checklist

Updated: 2026-05-20

This checklist is for local release administration only. It does not replace
Windows side-by-side validation, the owner real cycle, or the release-scope
decision for FY2026/R8 publication lag.

## Do Not Proceed If

- PR #2 is not clean or either required check is not green.
- The selected release candidate has not been Windows side-by-side validated
  after its last code/package change. Current v499 is package/source verified
  but still needs fresh Windows evidence because it changes setup behavior.
  v498 is the latest Windows side-by-side validated package.
- The owner real cycle and evidence bundle are missing.
- The strict FY2026/R8 gate is below 60% and there is no explicit
  `publication_lag` release-exception approval.
- OCR is included in the v1.0 release scope but the Windows OCR runtime proof
  or OCR add-on SHA/runtime verifier is missing for the selected candidate.
  Current v498 has OCR runtime proof; selecting v499 requires fresh Windows
  evidence or an explicit decision that the v498 OCR proof still applies.
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
shasum -a 256 dist/eidp-windows-v499.zip
cat dist/eidp-windows-v499.zip.sha256
uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v499.zip --json
shasum -a 256 dist/eidp-ocr-addon-windows-v497-smoke.zip
cat dist/eidp-ocr-addon-windows-v497-smoke.zip.sha256
uv run python scripts/verify_windows_distribution.py \
  dist/eidp-windows-v499.zip \
  --ocr-addon dist/eidp-ocr-addon-windows-v497-smoke.zip \
  --json
```

Expected ZIP SHA256:

```text
8f8b01f4a81496a95f9f9e2c2a9760919243807b7f300e2ad12c188f2ac18f54
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

- v499 Windows side-by-side validator JSON after fresh setup:
  `<pending>`;
- v499 Task Scheduler retry-on-failure proof after fresh setup:
  `<pending>`;
- v498 historical Windows side-by-side validator JSON:
  `logs/win-v498-stage6-v498-validate-after-setup-20260519.json`;
- v498 historical Windows UI smoke notes:
  `logs/win-v498-stage6-v498-ui-smoke-20260519.json`;
- v498 historical OCR runtime proof:
  `logs/win-v498-stage6-v498-validate-ocr-runtime-20260519.json`;
- v498 historical Excel smoke proof:
  `logs/win-v498-stage6-v498-excel-summary-20260519.json`;
- v498 historical active-task recovery proof:
  `logs/win-v498-stage6-v498-recovery-expected-v485-after-restore-20260519.json`;
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

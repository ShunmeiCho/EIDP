# v546 False-Reject RCA Summary Package Gates

Date: 2026-06-21
Branch: `main`
Package: `dist/eidp-windows-v546.zip`
Package SHA256: `ece0bbf3c1e96f3bf5be6dd553f3a547244edf15ad65ea2bc38c61600887ecfd`
Source commit: `63016054f948b1f4f285c3c822197f76c25b4b7d`

Release Forecast: `NOT_READY`

## Classification

| Priority | Finding | Evidence | Action |
| --- | --- | --- | --- |
| P0 release blocker | v546 has no Windows side-by-side setup/canary evidence yet. | This report covers Mac/non-Windows package gates only. Latest Windows bounded canary remains v545. | Do not use v546 as Windows release evidence until transferred, installed, and canaried on Windows. |
| P0 release blocker | FY2026/R8 strict Excel-ready yield is still below the v1 line. | Latest Windows canary evidence remains v545 strict/Excel-ready `12/50 (24.0%)`; false-reject review worksheet remains `0/53` complete. | Keep release blocked; complete owner review and rerun Windows evidence before any release claim. |
| P1 release hardening | Current `main` false-reject RCA summary is now packaged and non-Windows-gated. | v546 packages commit `6301605`; non-Windows release gates returned `ok=true`. | Use v546 as the next Windows transfer/canary candidate. |
| P2 documentation/demo drift | v545 owner handoff docs still point at the last Windows canary lane. | v546 has no owner handoff refresh in this report. | Do not replace owner handoff docs until Windows evidence exists or owner asks for a refreshed handoff. |
| P3 roadmap/research | University production workflow, cloud, multi-user, and complex frontend remain outside v1. | No v546 evidence changes v1 scope. | Keep in roadmap. |

## Package Evidence

Commands:

```text
uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v546.zip --latest-alias
shasum -a 256 dist/eidp-windows-v546.zip dist/eidp-windows.zip
cat dist/eidp-windows-v546.zip.sha256
uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v546.zip --json > logs/eidp-windows-v546-distribution-verify-20260621.json
```

Results:

- package verifier: `ok=true`;
- `BUILD_INFO.git_commit=63016054f948b1f4f285c3c822197f76c25b4b7d`;
- `BUILD_INFO.git_dirty=false`;
- package SHA and latest alias SHA both `ece0bbf3c1e96f3bf5be6dd553f3a547244edf15ad65ea2bc38c61600887ecfd`;
- `has_runtime=true`;
- `wheel_count=84`;
- `entry_count=3118`;
- discovery gold entries `45`;
- discovery gold expected predictions `45`;
- no undemonstrated discovery pattern sources.

## Non-Windows Release Gates

Command:

```text
uv run python scripts/run_non_windows_release_gates.py \
  dist/eidp-windows-v546.zip \
  --json \
  --output logs/eidp-windows-v546-release-gates-20260621.json
```

Result: `ok=true`.

Key gate results:

- SHA sidecar check: `ok=true`;
- package/source check: `package_commit=63016054f948b1f4f285c3c822197f76c25b4b7d`, `source_commit=63016054f948b1f4f285c3c822197f76c25b4b7d`, `source_dirty=false`, `stale=false`;
- full unit suite: `2052 passed`;
- validator/distribution unit slice: `196 passed`;
- validator/distribution mypy: success;
- validator/distribution Ruff: success;
- discovery gold summary: `45` entries, `10` strict target-year successes, `18` publication-lag entries, `15` operator-review entries;
- expected prediction replay: `45` exact matches, `0` failed predictions;
- package verifier: `returncode=0`;
- package verifier with demonstrated patterns required: `returncode=0`.

## Cleanup Evidence

Command:

```text
uv run python scripts/prune_release_artifacts.py \
  --base /Volumes/M1nG-ssd/EIDP-artifacts \
  --dist-dir /Volumes/M1nG-ssd/EIDP-artifacts/dist \
  --keep-latest 2 \
  --keep-version 545 \
  --apply \
  --json > logs/eidp-v546-local-prune-20260621.json
```

Result:

- `ok=true`;
- removed superseded v544 ZIP and sidecar;
- `deleted_count=2`;
- `deleted_bytes=210931317`;
- external-SSD-backed `dist/` now retains v545 fallback, v546 current package, and latest alias.

## Release Boundary

This report is not Windows release proof. Mac/non-Windows tests and package
verification do not replace Windows setup, Task Scheduler behavior, operator UI
flows, Stage 6 Windows evidence, or owner sign-off.

v546 remains `NOT_READY` until at least:

1. v546 is transferred to Windows and SHA-verified there;
2. v546 side-by-side setup and validators pass on Windows;
3. a v546 bounded weekly canary produces Stage 6 evidence;
4. the strict/Excel-ready line is resolved or the owner approves an explicit
   `publication_lag` RC-only exception;
5. OCR scope and owner real-cycle sign-off are complete.

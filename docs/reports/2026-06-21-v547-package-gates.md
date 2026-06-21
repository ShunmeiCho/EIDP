# v547 False-Reject Guidance Package Gates

Date: 2026-06-21
Branch: `main`
Package: `dist/eidp-windows-v547.zip`
Package SHA256: `f167e17b89f0ff96a45c817abcfd0403a2d487eddf3fb3a85a73d866b351de4b`
Source commit: `86c848f68e1dbde85c9b6422cfc827149940e02a`

Release Forecast: `NOT_READY`

## Classification

| Priority | Finding | Evidence | Action |
| --- | --- | --- | --- |
| P0 release blocker | v547 has no Windows side-by-side setup/canary evidence yet. | This report covers Mac/non-Windows package gates only. Latest Windows bounded canary remains v546. | Do not use v547 as Windows release evidence until transferred, installed, and canaried on Windows. |
| P0 release blocker | FY2026/R8 strict Excel-ready yield is still below the v1 line. | Latest Windows canary evidence remains v546 strict/Excel-ready `12/50 (24.0%)`; current v546 owner worksheet still has `53` blank decisions. | Keep release blocked; complete owner review and rerun Windows evidence before any release claim. |
| P1 release hardening | Current `main` false-reject worksheet guidance is now packaged and non-Windows-gated. | v547 packages commit `86c848f`; non-Windows release gates returned `ok=true`. | Use v547 as the next Windows transfer/canary candidate. |
| P2 storage hygiene | Superseded local v545 ZIP artifacts were pruned after v547 build. | `logs/eidp-v547-local-prune-20260621.json` reports `deleted_count=2`, `deleted_bytes=210931692`. | Continue retaining only current plus one fallback package unless an older artifact is actively needed. |
| P3 roadmap/research | University production workflow, cloud, multi-user, and complex frontend remain outside v1. | No v547 evidence changes v1 scope. | Keep in roadmap. |

## Package Evidence

Commands:

```text
uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v547.zip --latest-alias
shasum -a 256 dist/eidp-windows-v547.zip
uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v547.zip --json > logs/eidp-windows-v547-distribution-verify-20260621.json
```

Results:

- package verifier: `ok=true`;
- `BUILD_INFO.git_commit=86c848f68e1dbde85c9b6422cfc827149940e02a`;
- `BUILD_INFO.git_dirty=false`;
- package SHA `f167e17b89f0ff96a45c817abcfd0403a2d487eddf3fb3a85a73d866b351de4b`;
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
  dist/eidp-windows-v547.zip \
  --output logs/eidp-windows-v547-release-gates-20260621.json
```

Result: `ok=true`.

Key gate results:

- SHA sidecar check: `ok=true`;
- package/source check: `package_commit=86c848f68e1dbde85c9b6422cfc827149940e02a`, `source_commit=86c848f68e1dbde85c9b6422cfc827149940e02a`, `source_dirty=false`, `stale=false`;
- full unit suite: `2052 passed`;
- validator/distribution unit slice: `196 passed`;
- validator/distribution mypy: success;
- validator/distribution Ruff: success;
- discovery gold summary: `45` entries, `10` strict target-year successes, `18` publication-lag entries, `15` operator-review entries;
- expected prediction replay: `45` exact matches, `0` failed predictions;
- package verifier: `returncode=0`;
- package verifier with demonstrated patterns required: `returncode=0`.

## Cleanup Evidence

Commands:

```text
uv run python scripts/prune_release_artifacts.py \
  --dist-dir dist \
  --keep-latest 2 \
  --apply \
  --json > logs/eidp-v547-local-prune-20260621.json
dot_clean -m dist
```

Result:

- `ok=true`;
- removed superseded v545 ZIP and sidecar;
- `deleted_count=2`;
- `deleted_bytes=210931692`;
- external-SSD-backed `dist/` now retains v546 fallback, v547 current package, and latest alias;
- AppleDouble `._*` files are absent from `dist/` after cleanup.

## Release Boundary

This report is not Windows release proof. Mac/non-Windows tests and package
verification do not replace Windows setup, Task Scheduler behavior, operator UI
flows, Stage 6 Windows evidence, or owner sign-off.

v547 remains `NOT_READY` until at least:

1. v547 is transferred to Windows and SHA-verified there;
2. v547 side-by-side setup and validators pass on Windows;
3. a v547 bounded weekly canary produces Stage 6 evidence;
4. the strict/Excel-ready line is resolved or the owner approves an explicit
   `publication_lag` RC-only exception;
5. OCR scope and owner real-cycle sign-off are complete.

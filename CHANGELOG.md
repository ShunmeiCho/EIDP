# Changelog

All notable EIDP changes are tracked here for release administration.

## Unreleased - 2026-07-11

### Changed

- Consolidated the Ohara extraction core and Streamlit workflow into the sole
  Linux/Web `main` product line.
- Retired desktop runtime, ZIP/batch packaging, and Stage 6 release machinery;
  the v548 baseline remains available through Git history and the
  `windows-v548-fallback` audit tag.
- Added a Venus-safe launcher contract rooted at `/home/junming/EIDP`, a
  project-local virtual environment, POSIX locking for Web writes, and
  served-app release gates.

### Release Status

- `NOT_READY` until Venus deployment, intranet browser reachability,
  backup/restore, and served-app acceptance evidence are complete.

## 1.0.0rc1 - 2026-05-20 (retired desktop baseline)

### Added

- Windows operator package flow for ZIP extraction, double-click setup, Streamlit UI launch, weekly execution, Stage 6 evidence bundling, and recovery checks.
- Strict rolling-FY PDF discovery, fiscal-year classification, extraction, Excel export, and audit-log workflows for the EIDP v1.0 release candidate.
- Release evidence gates for Windows distribution verification, owner/operator Stage 6 return verification, publication-lag exception review, and mature-year proof handling.

### Changed

- Split release readiness into code/package readiness versus business approval evidence so FY2026/R8 publication lag does not get counted as strict current-year success.
- Hardened owner-return verification to require Excel proof, audit proof, ManualActionLog/JSONL consistency, and owner/operator sign-off before release approval.

### Release Status

- This historical candidate was never promoted to GA and is no longer the
  active product definition.

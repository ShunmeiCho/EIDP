# Changelog

All notable EIDP changes are tracked here for release administration.

## 1.0.0rc1 - 2026-05-20

### Added

- Windows operator package flow for ZIP extraction, double-click setup, Streamlit UI launch, weekly execution, Stage 6 evidence bundling, and recovery checks.
- Strict rolling-FY PDF discovery, fiscal-year classification, extraction, Excel export, and audit-log workflows for the EIDP v1.0 release candidate.
- Release evidence gates for Windows distribution verification, owner/operator Stage 6 return verification, publication-lag exception review, and mature-year proof handling.

### Changed

- Split release readiness into code/package readiness versus business approval evidence so FY2026/R8 publication lag does not get counted as strict current-year success.
- Hardened owner-return verification to require Excel proof, audit proof, ManualActionLog/JSONL consistency, and owner/operator sign-off before release approval.

### Release Status

- Code and package gates are ready for owner review, but v1.0 GA remains blocked until owner real-cycle Stage 6 evidence and an approved `publication_lag` exception, or a passing strict FY2026/R8 production-scale run, are available.

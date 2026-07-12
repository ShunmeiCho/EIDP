# EIDP v1 track consolidation decision record

Date: 2026-07-11
Status: **Implemented locally; release evidence pending**
Authority note: the project directive explicitly selected Linux/Web-only
development and retirement of the Windows baseline. A separate PI signature
artifact is not recorded in this file.

## Decision

- Collapse the former Windows, Ohara, and Linux/Web tracks into `main`.
- Use Linux/Web as the only product and development definition.
- Retire Windows runtime/packaging/Stage 6 assets from `main`.
- Preserve reusable extraction, Excel, SQLite, audit, locking, and data-quality
  logic.
- Keep v548 history addressable through `windows-v548-fallback`, not an active
  branch or release lane.

## Evidence behind the decision

- Topology before consolidation was `main < feature/Ohara <
  integration/linux-web-v1`; the Linux/Web branch already contained the Ohara
  core.
- The integrated five-stage Web flow had passed its real-PDF E2E and the full
  pre-retirement suite.
- Windows FY2026 strict yield remained 12/50 (24%) for the bounded cohort and
  was dominated by publication lag/upstream discovery, while the new product
  explicitly starts from a human-confirmed PDF.

## Implemented in this consolidation

- local `main` fast-forwarded to the Linux/Web integration baseline;
- Windows launchers, runtime/ZIP builders, Stage 6 gate, dedicated tests, and
  active operator docs removed;
- CI required-check name retained while its content became the served-app gate;
- Linux launcher sets `EIDP_APP_ROOT` and runs in the project virtual env;
- launcher redirects process home, temporary files, dependency/browser caches,
  SQLite, and application data below the repository root;
- Web mutation paths use the shared SQLite writer lock;
- Ruff, Bandit, mypy, full pytest/coverage, exact 28/3 real-PDF E2E, and local
  loopback health checks pass;
- product, architecture, technical-direction, and release-gate docs reconciled.

## Still open before release

- Venus install/start/restart and filesystem-boundary proof;
- business-PC LAN accessibility and browser workflow proof;
- OCR/image-lane acceptance scope;
- Ohara reach-10 versus accepting the honest seven-school clean cohort;
- authentication/allowlist and backup/restore evidence.
- Web review decisions connected to the authoritative audit log/outbox.

The release forecast remains `NOT_READY` until those served-app gates pass.

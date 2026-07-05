# Internal LAN Browser Access Gate

Date: 2026-07-05

Status: required release gate, not yet satisfied.

## Gate Statement

Linux/Web EIDP release proof requires user-PC browser access to the selected
Linux server URL. A local developer smoke test is not enough.

The expected operation model is:

```text
user PC browser
-> internal LAN / approved intranet path
-> selected Linux server URL
-> EIDP Web MVP / approved reverse proxy
-> local server storage, extraction, review, double-check, and reports
```

Users do not operate EIDP through Linux desktop, SSH, remote screen, or local
installation on every user machine.

## Current Status

No concrete Linux deployment target has been selected yet. The meeting
confirmed Linux/Web direction and browser-based usage, but not the host,
IP/DNS, port, reverse proxy, service owner, storage root, backup plan, or
maintenance process.

Same internal IP range is a useful prerequisite, but it is not sufficient for
release. The actual user-PC browser path must be tested.

## Required Evidence

The gate is satisfied only when evidence records:

- selected Linux server name and IP/DNS;
- approved target URL, either `http://<linux-server-ip>:<port>` during an
  internal MVP proof or an internal DNS/Nginx reverse-proxy URL;
- source user PC/network used for the smoke test;
- browser can open the Web UI without SSH tunnel or remote desktop;
- PDF upload from user PC succeeds;
- ZIP upload from user PC succeeds when ZIP intake is in scope;
- external CSV/XLSX upload from user PC succeeds for double-check input;
- review report and comparison report download to user PC succeeds;
- two browser sessions do not silently overwrite each other's state;
- internal CIDR/firewall/port rule is verified;
- disallowed network behavior is recorded when applicable;
- owner/PI/ICT accept the access boundary.

## Concurrency Boundary

Until formal multi-user architecture is implemented, the LAN proof must not
claim unrestricted concurrent editing. At minimum:

- two sessions must not silently overwrite each other;
- any observed write contention must be visible and recoverable;
- SQLite/local JSON usage must remain within the documented low-concurrency
  boundary;
- formal multi-user audit still requires user identity, optimistic locking or
  explicit row locks, and audit events.

## Security Boundary

This gate does not approve public exposure.

Acceptable MVP access boundaries include:

- internal CIDR allowlist;
- campus VPN or equivalent intranet control;
- Nginx reverse proxy on an internal interface;
- temporary owner-approved internal URL for smoke testing.

Formal multi-user operation still requires authentication and user identity for
review and export audit. Streamlit remains MVP/internal console. React,
FastAPI, and PostgreSQL remain the target formal multi-user architecture.

## Release Position

This gate is open. It cannot be closed until the server is selected and the
user-PC browser smoke test runs against that selected server.

Release Forecast remains `NOT_READY`.

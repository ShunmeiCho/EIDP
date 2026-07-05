# Linux Server Selection Runbook

Date: 2026-07-05

Status: planning gate. No Linux deployment target has been selected yet.

## Scope

This runbook defines how to select the Linux server for the Linux/Web EIDP
workflow. It does not perform deployment, approve release, expose a service
publicly, or change application behavior.

The meeting direction is browser-based operation on a research-lab Linux
server, but the concrete host, IP/DNS name, filesystem paths, service owner,
reverse proxy, backup process, and maintenance boundary are still undecided.

## Required Server Facts

Owner/PI/ICT must fill the following table before deployment proof can begin.

| Item | Candidate A | Candidate B | Notes |
| --- | --- | --- | --- |
| Linux server name | TBD | TBD | Do not use a developer laptop as release proof. |
| IP / internal DNS | TBD | TBD | Must be reachable from intended user PCs. |
| OS and version | TBD | TBD | Record Ubuntu/Rocky/etc. |
| Maintenance owner | TBD | TBD | Named person or team. |
| SSH allowed for maintainer | Unconfirmed | Unconfirmed | Users do not operate through SSH. |
| Python 3.12 available | Unconfirmed | Unconfirmed | Required for current app stack. |
| venv allowed | Unconfirmed | Unconfirmed | Preferred current deployment mode. |
| systemd user/service allowed | Unconfirmed | Unconfirmed | Required for unattended service proof. |
| Nginx or approved reverse proxy allowed | Unconfirmed | Unconfirmed | Preferred LAN exposure path. |
| Internal firewall/port allowed | Unconfirmed | Unconfirmed | Must be verified from user PC. |
| Writable app directory | Unconfirmed | Unconfirmed | Example: `/srv/eidp`, if approved. |
| Writable data directory | Unconfirmed | Unconfirmed | Must hold PDFs, JSON/SQLite, reports, logs. |
| Available disk | Unconfirmed | Unconfirmed | Account for PDFs, generated reports, logs, backups. |
| Backup process | Unconfirmed | Unconfirmed | Owner, schedule, restore smoke. |
| Docker allowed | Unconfirmed | Unconfirmed | Optional only; not assumed. |
| Outbound HTTPS allowed | Unconfirmed | Unconfirmed | Needed only for dependency install/update workflows. |
| Intended user network | Unconfirmed | Unconfirmed | Same internal IP range is necessary but not sufficient. |
| Disallowed network behavior | Unconfirmed | Unconfirmed | Public exposure is not approved. |

## Selection Criteria

A candidate server is selectable only if:

- it is a Linux host approved by owner/PI/ICT for research-lab internal Web use;
- user PCs can reach the server through an approved internal network path;
- a maintainer can install Python dependencies and run a service manager;
- PDF upload, CSV/XLSX upload, and report download storage paths can be
  configured outside the repository;
- backup and restore ownership is named;
- access can be limited to an approved internal CIDR, VPN, or equivalent
  network boundary;
- security review confirms that the service is not publicly exposed.

## Not Release Proof

The following are useful development checks but are not deployment proof:

- `localhost` or `127.0.0.1` smoke from the developer machine;
- `curl` from the Linux server to itself;
- a one-user Streamlit session without upload/download evidence;
- an SSH tunnel used only by the developer;
- proof from an unselected temporary host.

## Deployment Boundary

Current MVP UI remains Streamlit/internal console. Repository guidance requires
Streamlit to bind `127.0.0.1`; LAN exposure should therefore use an approved
reverse proxy on the selected server rather than binding Streamlit directly to
all interfaces.

React, FastAPI, PostgreSQL, authentication, roles, locking, and job queues
remain the target formal multi-user architecture. They are not implemented by
this runbook.

## Decision Record

Before Goal 6-B selected-server deployment proof, record:

- selected server name and IP/DNS;
- maintenance owner;
- approved URL;
- approved CIDR/VPN/reverse-proxy boundary;
- storage root and backup owner;
- port/firewall approval;
- whether Docker is allowed or explicitly out of scope;
- owner/PI sign-off that this is the target deployment host.

Release Forecast remains `NOT_READY` until the selected-server proof and owner
sign-off are complete.

# Linux Server Requirements

Date: 2026-07-05

Status: requirements template. No concrete server is approved by this file.

## Required Baseline

- Linux server approved by owner/PI/ICT.
- Python 3.12 available.
- `uv` or an approved Python virtual environment workflow available.
- Service manager available, preferably `systemd`.
- Internal reverse proxy available or approved, preferably Nginx.
- Writable storage root outside the repository.
- Backup and restore process assigned to an owner.
- Internal firewall/CIDR boundary configurable.
- No public exposure without a separate owner-approved security review.

## Recommended Directories

The actual paths must be approved for the selected server and supplied through
environment variables.

```text
EIDP_HOME            application checkout or release directory
EIDP_DATA_DIR        persistent application data
EIDP_UPLOAD_DIR      uploaded PDFs and ZIPs
EIDP_REPORT_DIR      generated review/comparison/export reports
EIDP_LOG_DIR         service logs
EIDP_BACKUP_DIR      backup staging
```

Do not hard-code developer-machine paths or Windows paths in deployment docs,
service files, or application configuration.

## Network Shape

Current repository guidance requires Streamlit to bind `127.0.0.1`. For LAN
browser access, use an approved internal reverse proxy:

```text
user PC browser
-> internal DNS or http://<linux-server-ip>:<port>
-> Nginx/internal reverse proxy
-> 127.0.0.1:<streamlit-port>
```

The reverse proxy may bind to an internal interface or approved port. The
Streamlit process itself should remain localhost-bound for the MVP.

## Optional Docker Boundary

Docker is optional and must not be assumed:

- some research/campus servers may prohibit containers;
- the primary MVP path is Python venv + service manager + reverse proxy;
- Docker can be evaluated later as a separate deployment profile.

## Minimum Operational Checks

Before selected-server deployment proof:

- confirm `python --version` or equivalent is Python 3.12;
- confirm dependency install path;
- confirm service restart path;
- confirm storage root permissions;
- confirm backup and restore smoke plan;
- confirm internal URL and firewall/CIDR behavior;
- confirm user-PC browser upload/download smoke steps.

This file is not a deployment proof and does not change Release Forecast.

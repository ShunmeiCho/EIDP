# Linux/Web Network Smoke Test

Date: 2026-07-05

Status: smoke-test template. Not executed because the target Linux server has
not been selected.

## Purpose

This checklist distinguishes a local development smoke from release-relevant
internal LAN proof.

`localhost` success proves only that the app starts locally. Release-relevant
evidence requires a user PC browser connecting to the selected Linux server
over the approved internal network path.

## Preconditions

- Selected Linux server is recorded in
  `docs/runbooks/linux-server-selection.md`.
- Internal URL is assigned:
  - `http://<linux-server-ip>:<port>` for approved internal MVP proof, or
  - an internal DNS/Nginx reverse-proxy URL.
- Maintainer confirms service process and storage root.
- Owner/PI/ICT confirm the intended user network.
- Test user PC is on the intended internal network.
- No public exposure is enabled.

## Smoke Steps

Record the date, tester, user PC network, selected server, and URL for each run.

1. Open the EIDP Web URL from a user PC browser.
2. Confirm the user did not use Linux desktop, SSH, remote screen, or local app
   install.
3. Upload a known text PDF through the browser.
4. Confirm the PDF intake queue shows the record and SHA256.
5. Upload a ZIP containing PDFs if ZIP intake is in scope for the run.
6. Upload external CSV/XLSX double-check output from the user PC.
7. Download the review report CSV.
8. Download the double-check comparison report CSV.
9. Open a second browser session and verify it does not silently overwrite the
   first session's state.
10. Restart the service, then confirm the intake/review/report state is still
    visible.
11. If an allowlist or firewall is configured, record allowed and disallowed
    access behavior.

## Pass Criteria

The smoke passes only if:

- browser access works from the intended user PC network;
- PDF upload succeeds;
- CSV/XLSX upload succeeds;
- reports download to the user PC;
- state survives a service restart;
- two browser sessions do not silently overwrite each other;
- access boundary matches owner/PI/ICT approval.

## Fail Conditions

Any of the following keeps the gate open:

- only `localhost` or server-local `curl` evidence exists;
- access works only through SSH tunnel or remote desktop;
- upload/download fails from the user PC;
- session overwrite or data loss is observed;
- the app is reachable from an unapproved public network;
- selected server, URL, or maintainer is still TBD.

## Output Record

Create a dated evidence note under `docs/reports/` with:

- selected server and URL;
- user PC network/location;
- commands or screenshots used as evidence;
- uploaded test file names and hashes where safe;
- downloaded report names;
- observed failures and remediation;
- final pass/fail.

This template does not change Release Forecast. Until the selected-server LAN
proof passes and owner/PI sign-off exists, Release Forecast remains
`NOT_READY`.

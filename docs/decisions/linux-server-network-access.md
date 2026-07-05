# Linux Server Network Access Decision

- Status: Proposed
- Date: 2026-07-05
- Scope: network and access decision for Linux/Web v1

## Decision Summary

Linux/Web v1 requires an explicit network-access decision before release. The
meeting direction points toward a Linux-hosted browser workflow, but the server
is not release-ready until reachability, authentication, and allowed networks
are approved and tested.

This document does not approve public exposure and does not change deployment
scripts.

## Network Risk

The main risk is that the Linux server may only be reachable from limited
networks, such as education-net/STF or a lab network. If owner/PI users cannot
reach the app reliably, a Web pivot can fail even when the application itself
works.

Other risks:

- accidental public exposure;
- weak authentication for school data and review decisions;
- unclear VPN/bastion requirements;
- browser session leakage on shared machines;
- lack of audit attribution for imported external extraction outputs;
- unclear backup/restore ownership for a server-hosted SQLite file.

## Required Decisions

Owner/PI must decide:

- allowed user groups;
- allowed network paths;
- whether VPN, bastion, or reverse proxy is required;
- authentication mechanism;
- TLS certificate approach;
- audit attribution requirements;
- backup owner and restore process;
- whether off-network access is permitted.

## Minimum Pre-Release Checks

Before Linux/Web can move beyond `NOT_READY`, record evidence for:

- owner/PI reachability from intended network;
- operator reachability from intended network;
- failed access from disallowed network when applicable;
- authenticated session behavior;
- TLS or internal certificate behavior;
- server restart and recovery;
- SQLite backup and restore smoke;
- log location and retention.

## SQLite Boundary

SQLite can remain the v1 datastore only under a documented single-writer
contract:

- one write transaction at a time;
- short write transactions;
- visible lock contention behavior;
- retry/backoff limits;
- routine checkpoint/backup procedure;
- maximum concurrent operator count.

If the network plan implies multiple simultaneous reviewers editing values,
SQLite may be the wrong release datastore and the database decision must be
reopened.

## Non-Goals

This document does not:

- implement network configuration;
- change deployment scripts;
- expose the server publicly;
- approve Linux/Web release;
- replace owner/PI sign-off.

Release Forecast remains `NOT_READY` until access is approved and tested.


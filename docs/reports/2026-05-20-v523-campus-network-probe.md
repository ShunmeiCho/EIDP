# v523 Campus Network Probe

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
Scope: read-only Mac-to-Windows network probe

## Purpose

Check the current Windows remote-management path after adding the `10.x`
campus/private-subnet deployment guidance, including `10.109.*` and `10.209.*`
examples. This probe does not modify the
Windows host, the active weekly task, or any EIDP data.

## Commands

```text
ssh -o ConnectTimeout=8 -o ControlMaster=no win hostname
```

Result:

```text
junming
```

```text
ssh -o ConnectTimeout=8 -o ControlMaster=no win "powershell -NoProfile -ExecutionPolicy Bypass -Command \"Get-NetConnectionProfile | Format-List Name,InterfaceAlias,NetworkCategory,IPv4Connectivity; Get-NetIPAddress -AddressFamily IPv4 | Format-Table InterfaceAlias,IPAddress,PrefixLength; Get-NetFirewallRule -DisplayGroup 'OpenSSH Server' -ErrorAction SilentlyContinue | Format-Table DisplayName,Enabled,Direction,Action,Profile\""
```

Key output:

```text
Name             : M1nG_5G
InterfaceAlias   : Wi-Fi
NetworkCategory  : Private
IPv4Connectivity : Internet

InterfaceAlias              IPAddress       PrefixLength
--------------              ---------       ------------
Wi-Fi                       192.168.0.9               24
Loopback Pseudo-Interface 1 127.0.0.1                  8

DisplayName               Enabled Direction Action Profile
-----------               ------- --------- ------ -------
OpenSSH SSH Server (sshd)    True   Inbound  Allow     Any
```

The full adapter list also included virtual/link-local adapters. They are not
the active Wi-Fi profile used by `Host win`.

## Findings

- `ssh win hostname` is currently reachable and returns `junming`.
- The active Windows Wi-Fi profile is `Private` with IPv4 Internet
  connectivity.
- The current active Wi-Fi IPv4 observed through SSH is `192.168.0.9/24`, not a
  `10.x` campus address.
- The OpenSSH inbound firewall rule is enabled and applies to `Any` profile.
- No evidence in this probe shows that the current v523 Windows side-by-side
  lane is blocked by the campus/private-subnet issue.

## Release Boundary

This probe only confirms the current remote-management path. It is not owner
sign-off, not proof of FY2026/R8 strict-yield readiness, and not a reason to
promote v523 to the active scheduled-task lane.

If the operator PC later moves to a `10.x` university subnet such as `10.109.*`
or `10.209.*`, use `docs/runbooks/eidp-windows.md` section `14.7.1` before
counting any Mac-side timeout as Windows package failure. This probe has no live
evidence from an actual `10.209.*` campus network.

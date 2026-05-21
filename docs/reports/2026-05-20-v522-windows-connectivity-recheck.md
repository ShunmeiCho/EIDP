# v522 Windows Connectivity Recheck

Date: 2026-05-20 12:53 JST
Branch: `sprint8-handoff-finalize`
Scope: read-only Mac-side network probe

## Purpose

Confirm whether current-source Windows smoke can proceed, or whether the
Windows OpenSSH/IP blocker still prevents side-by-side validation.

## Findings

- Local `Host win` still resolves to stale `192.168.0.9`.
- Current Mac Wi-Fi address is `192.168.10.68` on `en0`.
- Current ARP candidates on `192.168.10.0/24` were only:
  - `192.168.10.12`
  - `192.168.10.72`
- `192.168.10.12`, `192.168.10.72`, and stale `192.168.0.9` all had common
  remote-management ports closed:
  - SSH `22`
  - RPC `135`
  - NetBIOS `139`
  - SMB `445`
  - RDP `3389`
  - WinRM `5985`
  - WinRM TLS `5986`
- Short Bonjour/mDNS browse for `_ssh._tcp`, `_smb._tcp`, `_rdp._tcp`, and
  `_workstation._tcp` found no usable advertised service.

## Command Evidence

```text
ssh -G win | rg '^(hostname|user|port|identityfile) '
```

Key output:

```text
user junming
hostname 192.168.0.9
port 22
identityfile ~/.ssh/id_rsa
```

```text
ipconfig getifaddr en0
```

Output:

```text
192.168.10.68
```

```text
arp -a
```

Relevant output:

```text
? (192.168.10.12) at 80:2b:f9:ec:85:f on en0 ifscope [ethernet]
? (192.168.10.72) at d2:c:5:84:b0:63 on en0 ifscope [ethernet]
```

Port probe:

```text
for host in 192.168.10.12 192.168.10.72 192.168.0.9; do
  for port in 22 135 139 445 3389 5985 5986; do
    nc -G 1 -z "$host" "$port"
  done
done
```

Result: every probed host/port returned closed.

## Release Boundary

Current-source Windows side-by-side smoke remains blocked. The next required
input is a current Windows IPv4 address or restored OpenSSH/WinRM/RDP service on
the operator PC. This probe does not modify the Windows machine or the active
v485 scheduled-task lane.

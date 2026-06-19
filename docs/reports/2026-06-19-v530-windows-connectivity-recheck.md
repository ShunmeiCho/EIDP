# v530 Windows Connectivity Recheck

Date: 2026-06-19
Branch: `test/fault-injection-pdf-discovery`
Local HEAD at check time: `8a2b57176c5e521e08d71561889ec6c540bfeda3`
Package candidate: `dist/eidp-windows-v530.zip`

## Result

`ssh win` is not currently reachable from this Mac, so v530 Windows
side-by-side validation and owner-return readback could not be run in this
session.

## Command

```bash
ssh -o BatchMode=yes -o ConnectTimeout=5 win hostname
```

## Evidence

The sandboxed first attempt was blocked by local network policy:

```text
ssh: connect to host 192.168.0.9 port 22: Operation not permitted
```

The approved non-sandbox retry reached the network path but timed out:

```text
ssh: connect to host 192.168.0.9 port 22: Operation timed out
```

## Release Impact

This does not invalidate the previously recorded v526 Windows side-by-side
evidence from 2026-05-20, but it means there is no current Windows-side proof
for v530. Before promoting v530, restore Windows SSH or use an approved
operator-side validation path, then rerun the side-by-side validator, UI smoke,
Excel smoke, OCR-scope proof if OCR is in scope, bounded canary, and
Stage 6 owner-return evidence checks.

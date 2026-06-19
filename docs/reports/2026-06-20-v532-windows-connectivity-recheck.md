# v532 Windows Connectivity Recheck

Date: 2026-06-20
Branch: `main`
Local HEAD at check time: `92ad3efa468f7984f994762523416e0f1f00ba91`
Package candidate: `dist/eidp-windows-v532.zip`
Package SHA256: `9743cc65c21ada06b6a1d6c8b50ba67cdaffa4f3942256ccd072d4469fa0d6c7`

## Result

`ssh win` is still not reachable from this Mac. v532 Windows side-by-side
validation and owner-return readback could not be run from the Mac in this
session.

## Command

```bash
ssh -o BatchMode=yes -o ConnectTimeout=5 win hostname
```

## Evidence

Approved non-sandbox retry:

```text
ssh: connect to host 192.168.0.9 port 22: Operation timed out
```

## Release Impact

This does not invalidate the previously recorded v526 Windows side-by-side
evidence from 2026-05-20, but it means there is still no Windows-side proof for
v532. Before promoting v532, either restore Windows SSH or use the prepared
operator-side validation path:

- `docs/runbooks/00-READ-ME-FIRST-v532.txt`
- `docs/runbooks/eidp-v532-owner-request-20260620.txt`
- `docs/runbooks/eidp-v532-owner-return-fill-sheet.md`

The selected path must still produce v532 setup validation, active-task safety
proof, UI smoke, Excel proof, bounded weekly canary proof, Stage 6 evidence
verification, owner/operator sign-off, and either strict FY2026/R8 success or
an approved `publication_lag` exception.

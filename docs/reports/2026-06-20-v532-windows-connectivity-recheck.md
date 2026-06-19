# v532 Windows Connectivity Recheck And Follow-Up

Date: 2026-06-20
Branch: `main`
Local HEAD at check time: `92ad3efa468f7984f994762523416e0f1f00ba91`
Package candidate: `dist/eidp-windows-v532.zip`
Package SHA256: `9743cc65c21ada06b6a1d6c8b50ba67cdaffa4f3942256ccd072d4469fa0d6c7`

## Result

The first `ssh win` recheck timed out from this Mac. After Windows SSH was
restored, v532 side-by-side validation completed from the Mac against a fresh
Windows root:

```text
C:\Users\cyo20\EIDP-v532-723a507-env0
```

The detailed runtime evidence is now recorded in:

```text
docs/reports/2026-06-20-v532-full-windows-side-by-side-smoke.md
logs/win-v532-stage6/win-v532-stage6-side-by-side-evidence-20260620.zip
logs/win-v532-stage6/win-v532-stage6-side-by-side-evidence-manifest-20260620.json
```

## Initial Failed Command

```bash
ssh -o BatchMode=yes -o ConnectTimeout=5 win hostname
```

## Initial Evidence

Approved non-sandbox retry:

```text
ssh: connect to host 192.168.0.9 port 22: Operation timed out
```

## Follow-Up Evidence

After SSH was restored, v532 completed setup validation, active-task recovery
proof, UI smoke, bounded weekly canary, Excel smoke, Stage 6 evidence bundle
creation, and Stage 6 evidence verification.

Key result:

```text
v532 strict/Excel-ready FY2026 canary yield: 12/50 (24.0%)
v532 operator-reviewable canary rate:       47/50 (94.0%)
v532 ship gate status:                      below_gate
v532 Stage 6 evidence verifier:             ok=true
v532 OCR runtime proof:                     failed, OCR add-on missing
```

## Release Impact

The connectivity blocker was cleared for side-by-side smoke. Release is still
blocked by the business gates: current FY2026/R8 strict yield below `>= 60%`,
missing owner/operator sign-off, unapproved `publication_lag` exception, and
the unresolved OCR-scope decision for v532.

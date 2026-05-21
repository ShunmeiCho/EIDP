# EIDP v423 Stage 6 Evidence Draft

Updated: 2026-05-15
Status: draft / not signed off

This document is the v423 Stage 6 evidence landing page. v423 is
Mac/non-Windows release-gate-clean, but it has not yet been transferred to the
Windows operator PC and has no v423 setup/UI/real-cycle proof.

## Mac Evidence

| Gate | Status | Evidence |
| --- | --- | --- |
| v423 package freshness | pass | `logs/release-gate-v423-retroactive.json` reports package/source commit `852d38734f03f62047c3b896b96a56857bb679c6`, `source_dirty=false`, and `stale=false`. |
| v423 package integrity | pass | `dist/eidp-windows-v423.zip.sha256` and release gate report SHA256 `ff8d09b123c4d1b70738afdec5ed85b6366a932108cd8e5d1bbe5b1773df2b75`. |
| v423 Mac/non-Windows release gate | pass | Standard full gate exited `0`: unit suite `1555 passed`, validator slice `163 passed`, validator mypy/Ruff passed, discovery-gold expected predictions matched `44/44`, and package verifiers passed. |
| v423 ZIP launcher/script consistency | pass | `unzip -l dist/eidp-windows-v423.zip` contains `EIDP-setup.bat`, `EIDP-start.bat`, `EIDP-diagnose.bat`, `EIDP-stage6-evidence.bat`, `EIDP-stage6-verify-evidence.bat`, `scripts/first_setup.bat`, `scripts/launch.bat`, `scripts/weekly_run.bat`, `scripts/validate_install.bat`, `scripts/collect_stage6_evidence.bat`, and `scripts/verify_stage6_evidence.bat`. The root Stage 6 evidence launchers call the packaged `scripts\collect_stage6_evidence.bat` and `scripts\verify_stage6_evidence.bat` wrappers. |
| v423 retroactive FY2025/R7 Excel regression | pass | Isolated app root `_temp/non-windows-retroactive-fy2025-20260515-153245` exported FY2025 and `retroactive_excel_diff_reference` returned zero missing/extra rows and zero differing fields against `_temp/v408-r7-cli-export.xlsx`. |
| v423 retroactive FY2025/R7, FY2024/R6, and FY2023/R5 matrix | pass | `logs/release-gate-v423-retroactive-matrix.json` returned `ok=true` for all three cases. `logs/release-gate-v423-retroactive-fy2025-reference.json`, `logs/release-gate-v423-retroactive-fy2024-reference.json`, and `logs/release-gate-v423-retroactive-fy2023-reference.json` each returned `ok=true` and zero business-value diffs against stable references. |
| v423 Windows transfer/setup/UI | missing | SSH-Win is disconnected; `docs/runbooks/eidp-v423-windows-transfer-checklist.md` now includes a no-SSH manual transfer path, but no v423 Windows SHA check, extraction, setup, launcher, UI health, or evidence bundle exists yet. |

## Package Record

| Field | Value |
| --- | --- |
| Package | `dist/eidp-windows-v423.zip` |
| SHA256 | `ff8d09b123c4d1b70738afdec5ed85b6366a932108cd8e5d1bbe5b1773df2b75` |
| SHA256 sidecar | `dist/eidp-windows-v423.zip.sha256` |
| Package commit | `852d38734f03f62047c3b896b96a56857bb679c6` |
| FY2025 retroactive release-gate log | `logs/release-gate-v423-retroactive.json` |
| Superseded package note | v421 was rejected by the package verifier because the packaged E2E template still contained hard-coded v420 package/SHA fields. Do not transfer v421. |
| Windows transfer checklist | `docs/runbooks/eidp-v423-windows-transfer-checklist.md` |
| Suggested Windows extract path | `C:\Users\cyo20\EIDP-v423-852d3873` |

Note: the v423 ZIP contains the reusable operator E2E template, while this
version-specific transfer checklist and evidence draft are companion documents
outside the ZIP. Carry the current repo copies of
`docs/runbooks/eidp-v423-windows-transfer-checklist.md` and this draft alongside
the ZIP and SHA sidecar during manual transfer or operator-PC execution. Fill
`docs/runbooks/eidp-operator-e2e-template.md` after execution; do not prefill the
packaged reusable template before building a ZIP.

## Stage 6 Boundary

| Requirement | Current v423 evidence | Status |
| --- | --- | --- |
| ZIP distribution -> setup -> browser UI offline operation | v423 ZIP is built and Mac-verified; v408 remains the latest Windows transfer/setup/UI proof. | Missing for v423 |
| Retroactive FY2025/R7 Excel export parity | v423 isolated Mac export matched the stable v408 R7 CLI reference with zero business-value diffs. | Mac proof only |
| Retroactive FY2024/R6 and FY2023/R5 Excel export parity | v423 isolated Mac exports matched their stable references with zero business-value diffs. | Mac proof only |
| ManualActionLog audit | Unit and v408 sandbox support exist; real v423 operator-cycle audit/outbox delta is not captured. | Missing for v423 real cycle |
| Ship line 60-70% true target PDF / <=30% manual work | No v423 current-FY production yield evidence exists. | Missing / failing |

## Next Windows Steps

When SSH-Win is available again, or when the operator can manually move the ZIP
through a USB drive or trusted internal file share, execute the v423 lane in
this order:

1. Transfer `dist/eidp-windows-v423.zip` and `dist/eidp-windows-v423.zip.sha256`
   to `C:\EIDP-staging\` using either SSH/SCP or the no-SSH manual path in
   `docs/runbooks/eidp-v423-windows-transfer-checklist.md`.
2. Verify SHA256 on Windows with `Get-FileHash` or `certutil`.
3. Extract to `C:\Users\cyo20\EIDP-v423-852d3873` unless the operator chooses
   a different staging path.
4. Run `first_setup.bat`.
5. Launch Streamlit on `127.0.0.1:8501`.
6. Run the Stage 6 retroactive FY2025 operator dry-run.
7. Build and verify the Stage 6 evidence bundle.
8. Pull or manually copy the evidence bundle back to Mac and verify it again.
9. Fill `docs/runbooks/eidp-operator-e2e-template.md` with the real v423
   operator data.

Do not sign this draft until the Windows operator-PC row exists.

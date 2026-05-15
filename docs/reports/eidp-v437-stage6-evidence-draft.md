# EIDP v437 Stage 6 Evidence Draft

Updated: 2026-05-15
Status: draft / not signed off

This document is the v437 Stage 6 evidence landing page. v437 is
Mac/non-Windows release-gate-clean and adds structured JSONL operator logging,
but it has not yet been transferred to the Windows operator PC and has no v437
setup/UI/real-cycle proof.

## Mac Evidence

| Gate | Status | Evidence |
| --- | --- | --- |
| v437 package freshness | pass | `logs/release-gate-v437-full.json` reports package/source commit `7553c7480a001a1ebec687dcb743c8bd9529d6d4`, `source_dirty=false`, and `stale=false`. |
| v437 package integrity | pass | `dist/eidp-windows-v437.zip.sha256` and release gate report SHA256 `ed0d677fd2d36f7bd9f884185412180a6764beef9632543e5e36eb3c766ed33c`. |
| v437 Mac/non-Windows release gate | pass | Standard full gate exited `0`: unit suite `1600 passed`, validator slice `164 passed`, validator mypy/Ruff passed, discovery-gold expected predictions matched `44/44`, and both package verifier modes passed. |
| v437 structured logging | pass | `src/eidp/logging_config.py` configures `structlog` plus stdlib logging through `ProcessorFormatter`, writes rotating `logs/eidp.jsonl` with `maxBytes=10MB` and `backupCount=12`, and keeps stderr JSON so `weekly_run.bat` captures structured lines. `tests/unit/test_logging_config.py` covers structlog JSONL, stdlib JSONL, idempotence, and app-root default path; `tests/unit/test_logging_entrypoints.py` covers CLI, Streamlit, and weekly-runner entrypoint wiring. |
| v437 ZIP launcher/script consistency | pass | `scripts/verify_windows_distribution.py dist/eidp-windows-v437.zip` passed inside the full gate. The verifier reported `entry_count=3080`, `wheel_count=78`, `project_wheel_count=1`, 47 prefecture seed rows, 2148 seed school rows, 44 discovery gold entries, and no undemonstrated discovery pattern sources. |
| v437 retroactive FY2025/R7, FY2024/R6, and FY2023/R5 matrix | pass | `logs/release-gate-v437-retroactive-matrix.json` returned `ok=true` for all three cases. `logs/release-gate-v437-retroactive-fy2025-reference.json`, `logs/release-gate-v437-retroactive-fy2024-reference.json`, and `logs/release-gate-v437-retroactive-fy2023-reference.json` each returned `ok=true` and zero business-value diffs against stable references. |
| v437 Windows transfer/setup/UI | missing | SSH-Win is disconnected; `docs/runbooks/eidp-v437-windows-transfer-checklist.md` provides a no-SSH manual transfer path, but no v437 Windows SHA check, extraction, setup, launcher, UI health, or evidence bundle exists yet. |

## Package Record

| Field | Value |
| --- | --- |
| Package | `dist/eidp-windows-v437.zip` |
| SHA256 | `ed0d677fd2d36f7bd9f884185412180a6764beef9632543e5e36eb3c766ed33c` |
| SHA256 sidecar | `dist/eidp-windows-v437.zip.sha256` |
| Package commit | `7553c7480a001a1ebec687dcb743c8bd9529d6d4` |
| Full release-gate log | `logs/release-gate-v437-full.json` |
| Retroactive matrix log | `logs/release-gate-v437-retroactive-matrix.json` |
| Windows transfer checklist | `docs/runbooks/eidp-v437-windows-transfer-checklist.md` |
| Suggested Windows extract path | `C:\Users\cyo20\EIDP-v437-7553c748` |

## Retroactive Matrix

| FY | Fresh isolated export | Reference | Diff result |
| --- | --- | --- | --- |
| 2025 / R7 | `_temp/non-windows-retroactive-fy2025-20260515-184145/output/retroactive-fy2025-export.xlsx` | `_temp/v408-r7-cli-export.xlsx` | `missing_rows=0`, `extra_rows=0`, `differing_fields=0` |
| 2024 / R6 | `_temp/non-windows-retroactive-fy2024-20260515-190026/output/retroactive-fy2024-export.xlsx` | `_temp/non-windows-retroactive-fy2024-20260515-125437/output/retroactive-fy2024-export.xlsx` | `missing_rows=0`, `extra_rows=0`, `differing_fields=0` |
| 2023 / R5 | `_temp/non-windows-retroactive-fy2023-20260515-190422/output/retroactive-fy2023-export.xlsx` | `_temp/non-windows-retroactive-fy2023-20260515-125526/output/retroactive-fy2023-export.xlsx` | `missing_rows=0`, `extra_rows=0`, `differing_fields=0` |

All three exports wrote `採録状況=2418`, `対象比率=10022`,
`学科別=9719`, and `在籍のみ抜粋=9719`.

## Stage 6 Boundary

| Requirement | Current v437 evidence | Status |
| --- | --- | --- |
| ZIP distribution -> setup -> browser UI offline operation | v437 ZIP is built and Mac-verified; v408 remains the latest Windows transfer/setup/UI proof. | Missing for v437 |
| Retroactive FY2025/R7 Excel export parity | v437 isolated Mac export matched the stable v408 R7 CLI reference with zero business-value diffs. | Mac proof only |
| Retroactive FY2024/R6 and FY2023/R5 Excel export parity | v437 isolated Mac exports matched their stable references with zero business-value diffs. | Mac proof only |
| ManualActionLog audit | Unit and v408 sandbox support exist; real v437 operator-cycle audit/outbox delta is not captured. | Missing for v437 real cycle |
| Ship line 60-70% true target PDF / <=30% manual work | No v437 current-FY production yield evidence exists. | Missing / failing |

## Next Windows Steps

When SSH-Win is available again, or when the operator can manually move the ZIP
through a USB drive or trusted internal file share, execute the v437 lane in
this order:

1. Transfer `dist/eidp-windows-v437.zip` and `dist/eidp-windows-v437.zip.sha256`
   to `C:\EIDP-staging\` using either SSH/SCP or the no-SSH manual path in
   `docs/runbooks/eidp-v437-windows-transfer-checklist.md`.
2. Verify SHA256 on Windows with `Get-FileHash` or `certutil`.
3. Extract to `C:\Users\cyo20\EIDP-v437-7553c748` unless the operator chooses
   a different staging path.
4. Run `first_setup.bat`.
5. Launch Streamlit on `127.0.0.1:8501`.
6. Run the Stage 6 retroactive FY2025 operator dry-run.
7. Build and verify the Stage 6 evidence bundle.
8. Pull or manually copy the evidence bundle back to Mac and verify it again.
9. Fill `docs/runbooks/eidp-operator-e2e-template.md` with the real v437
   operator data.

Do not sign this draft until the Windows operator-PC row exists.

# EIDP v459 Real-Cycle Execution Card

Updated: 2026-05-16

This card is the short operator/owner checklist for the next Stage 6 real-cycle
run on the current v459 lane. It does not replace
`docs/runbooks/eidp-operator-e2e-template.md`; use that template for the final
record.

## Current Lane

| Item | Value |
| --- | --- |
| Package | `dist/eidp-windows-v459.zip` |
| SHA256 | `1f50e574987a636b064c2a45ec870d1c6c8050ec036fc12a767caaed50e244b2` |
| Package snapshot | `50152a5f2bfc0b8f0a360ef87af5e4979b284f4a` |
| Windows root | `C:\Users\cyo20\EIDP-v459-50152a5` |
| Evidence draft | `docs/reports/eidp-v459-stage6-evidence-draft.md` |
| Full template | `docs/runbooks/eidp-operator-e2e-template.md` |
| Companion docs ZIP | `dist/eidp-v459-operator-docs-20260516.zip` |
| Windows staging docs ZIP | `C:\EIDP-staging\eidp-v459-operator-docs-20260516.zip` |

The v459 core ZIP was intentionally not rebuilt after the final documentation
updates, so the package-embedded runbook/template may be stale. Use the
companion docs ZIP above for the current real-cycle card, E2E template, release
status, and v459 evidence draft while keeping the verified core ZIP SHA256
unchanged. The companion docs ZIP was copied to Windows staging and verified
with Windows `Get-FileHash` against its sidecar.

Before this card was handed off, the real-cycle entrypoints below were verified
in both `dist/eidp-windows-v459.zip` and the extracted Windows root above:
`EIDP-start.bat`, `EIDP-setup.bat`, `EIDP-stage6-evidence.bat`,
`EIDP-stage6-verify-evidence.bat`, `EIDP-diagnose.bat`,
`scripts\weekly_run.bat`, `scripts\validate_install.bat`,
`scripts\stage6_recovery_check.bat`, and `scripts\diagnose.bat`.

## Owner / Operator Request

Please run one real Stage 6 cycle on the operator PC using the v459 lane above.
The goal is not another Codex smoke test; it is owner/operator confirmation that
the Windows ZIP can be used for the actual workflow.

Minimum record to return:

- Completed `docs/runbooks/eidp-operator-e2e-template.md` real-cycle fields.
- Latest `logs\diagnostics-*.txt`.
- Latest `logs\stage6-evidence-*.zip` plus `logs\stage6-evidence-verify-*.json`.
- `data\output\last_run.json`.
- Final KPI values: `target_pdf_auto_yield_pct`,
  `operator_reviewable_yield_pct`, `ship_gate_status`, `ship_readiness_rc`,
  pending JSONL outbox count, and owner/operator sign-off.

Do not approve v1.0 from the bounded v459 canary alone. The real-cycle row must
be filled from an owner/operator run or an explicitly approved full-cycle copy.

## Do Not Touch

- Do not delete `data\eidp.sqlite3`.
- Do not delete `data\audit\manual-actions.jsonl`.
- Do not delete `data\master.xlsx`.
- Do not run `uninstall.bat`.
- Do not persist `EIDP_TARGET_FISCAL_YEAR` into `.env`.
- Do not overwrite an existing operator data directory without a backup.

## Preflight

Run from PowerShell on the operator PC:

```powershell
Set-Location "C:\Users\cyo20\EIDP-v459-50152a5"
$zip = "C:\EIDP-staging\eidp-windows-v459.zip"
$expected = "1f50e574987a636b064c2a45ec870d1c6c8050ec036fc12a767caaed50e244b2"
$actual = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $expected) { throw "SHA256 mismatch: $actual" }

.\scripts\validate_install.bat --after-setup
.\scripts\validate_install.bat --after-setup --after-weekly
.\scripts\stage6_recovery_check.bat "C:\Users\cyo20\EIDP-v459-50152a5\scripts\weekly_run.bat"
.\scripts\diagnose.bat
```

Expected before continuing:

| Check | Expected |
| --- | --- |
| SHA256 | matches the value above |
| setup validator | exit code `0` |
| weekly validator | exit code `0` if bounded canary already ran |
| recovery check | `ok=true`, `action_matches_expected=true` |
| diagnostics | writes `logs\diagnostics-*.txt` |

## Real-Cycle Run

1. Double-click `EIDP-start.bat`.
2. Confirm the browser opens `http://127.0.0.1:8501`.
3. Confirm the UI shows `2026年度（令和8年度）`.
4. Run the normal weekly collection cycle only with owner/operator present.
5. Use the browser UI to resolve the real work queue:
   - `① 学校別タスク`
   - `② PDF確認・手入力`
   - `③ 年度判定・修正`
   - `④ Excel プレビュー`
   - `詳細 operator` -> `URL候補レビュー`
   - `詳細 operator` -> `監査ログ`
6. In `監査ログ`, run `Outbox を flush` after write actions.
7. Record the actual KPI values in `docs/runbooks/eidp-operator-e2e-template.md`.

Do not treat the existing v459 bounded canary, browser health/nav smoke,
process-scoped R7 browser Excel proof, disposable UI write/audit sandbox, or R7
retroactive support as the real-cycle sign-off.

## Evidence Bundle

After the real-cycle run:

```powershell
Set-Location "C:\Users\cyo20\EIDP-v459-50152a5"
.\EIDP-stage6-evidence.bat
.\EIDP-stage6-verify-evidence.bat
```

Copy these files back to Mac:

- `logs\stage6-evidence-*.zip`
- `logs\stage6-evidence-verify-*.json`
- `logs\diagnostics-*.txt`
- `logs\run-*.log`
- `data\output\last_run.json`
- `data\output\target-year-discovery\*-discovery-rca-batch-plan.json`

Do not put Excel exports or live SQLite files into the shared evidence ZIP.

## Sign-Off Gate

The v1.0 line is still blocked until the owner/operator record contains:

| Gate | Required result |
| --- | --- |
| Operator PC one-cycle | completed |
| `ship_readiness_rc` | `0` or approved release exception |
| strict target PDF auto-yield | production R8 evidence, target 60-70% |
| estimated manual workload | 30% or lower |
| audit/outbox | no pending JSONL rows after flush |
| evidence verification | `ok=true` |
| owner sign-off | present |
| operator sign-off | present |

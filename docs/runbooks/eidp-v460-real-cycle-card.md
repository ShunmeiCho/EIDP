# EIDP v460 Real-Cycle Execution Card

Updated: 2026-05-17

This card is the short operator/owner checklist for the next Stage 6 real-cycle
run on the v460 lane. It does not replace
`docs/runbooks/eidp-operator-e2e-template.md`; use that template for the final
record.

## Current Lane

| Item | Value |
| --- | --- |
| Package | `dist/eidp-windows-v460.zip` |
| SHA256 | `ce5fa49b8c30900a33b31fd317c6846ffe5839053f2bdd1ffdeb8cca2113129c` |
| Package snapshot | `01e44279238aaef9127ed9b578e29dc8e0070499` |
| Windows root | `C:\Users\cyo20\EIDP-v460-01e4427` |
| Evidence draft | `docs/reports/eidp-v460-stage6-evidence-draft.md` |
| Full template | `docs/runbooks/eidp-operator-e2e-template.md` |
| Top-level README source | `docs/runbooks/00-READ-ME-FIRST-v460.txt` |
| Top-level README SHA256 | `047ae62bce4c8b419630dff777973a0cd5c285ecd01d2d4b69601f0d6fa9e8b7` |
| Owner request source | `docs/runbooks/eidp-v460-owner-request-20260516.txt` |
| Owner request SHA256 | `66989897067ba2443804200c88c4484d571e67611caa1af2825714f2f1afe08e` |
| Companion docs ZIP | `dist/eidp-v460-operator-docs-20260517.zip` |
| Windows staging docs ZIP | `C:\EIDP-staging\eidp-v460-operator-docs-20260517.zip` |

The v460 core ZIP includes the current version-neutral E2E template. Use the
companion docs ZIP for this version-specific real-cycle card, release-status
snapshot, and v460 evidence draft.

The 20260517 companion docs refresh supersedes the 20260516 companion docs for
operator reading only. It does not change the v460 core package, Windows app
root, scheduled task, or release approval gate. After transfer, verify the ZIP
with Windows `Get-FileHash` and expand it to
`C:\EIDP-staging\v460-operator-docs-20260517`.
The top-level staging readme is `C:\EIDP-staging\00-READ-ME-FIRST-v460.txt`;
its tracked source is `docs/runbooks/00-READ-ME-FIRST-v460.txt`, and its SHA256
matches the handoff manifest value above.

Before this card was handed off, v460 passed the Mac/non-Windows release gate,
Windows setup staging, and a read-only browser navigation smoke. The scheduled
task now points at:
`C:\Users\cyo20\EIDP-v460-01e4427\scripts\weekly_run.bat`.

## Owner / Operator Request

Please run one real Stage 6 cycle on the operator PC using the v460 lane above.
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

Do not approve v1.0 from the v460 setup/staging proof alone. The real-cycle row
must be filled from an owner/operator run or an explicitly approved full-cycle
copy.

A pre-owner diagnostic evidence ZIP was intentionally rejected by
`EIDP-stage6-verify-evidence.bat` because `last_run` was missing. Treat that as
a guardrail proof, not as release evidence.

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
Set-Location "C:\Users\cyo20\EIDP-v460-01e4427"
$zip = "C:\EIDP-staging\eidp-windows-v460.zip"
$expected = "ce5fa49b8c30900a33b31fd317c6846ffe5839053f2bdd1ffdeb8cca2113129c"
$actual = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $expected) { throw "SHA256 mismatch: $actual" }

.\scripts\validate_install.bat --after-setup
.\scripts\stage6_recovery_check.bat "C:\Users\cyo20\EIDP-v460-01e4427\scripts\weekly_run.bat"
.\scripts\diagnose.bat
```

Expected before continuing:

| Check | Expected |
| --- | --- |
| SHA256 | matches the value above |
| setup validator | exit code `0` |
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
retroactive support as the v460 real-cycle sign-off.

## Evidence Bundle

After the real-cycle run:

```powershell
Set-Location "C:\Users\cyo20\EIDP-v460-01e4427"
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

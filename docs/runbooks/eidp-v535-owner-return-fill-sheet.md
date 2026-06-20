# EIDP v535 Owner Return Fill Sheet

Date: 2026-06-20
Scope: v535 owner/operator return evidence only

This sheet is a fill aid for `docs/runbooks/eidp-operator-e2e-template.md`.
It is not release approval and does not replace the signed template,
`publication_lag` exception record, or `scripts/verify_stage6_return.py`.

## Use This Only After The Owner Chooses Route A

Route A means:

1. the owner explicitly approves the `publication_lag` exception;
2. the operator runs one real Stage 6 cycle on the v535 side-by-side lane; and
3. the completed template, logs, Excel proof, audit proof, and sign-offs are
   returned for verification.

If the owner chooses Route B, do not run the owner sign-off cycle yet. Keep
v1.0 on hold until enough FY2026/R8 target-form PDFs are public.

## Fixed Values To Copy Into The E2E Template

| E2E field | Value |
| --- | --- |
| EIDP package commit | `d742327570a08a8f9d6ade7adfc81da8940294b4` |
| core ZIP ファイル名 | `eidp-windows-v535.zip` |
| core ZIP sha256 | `72ef94f35a2cd482eb9650d1a466cb8441f7d96a660a8901710d96603e7d8e9f` |
| transferred ZIP | `C:\EIDP-staging\eidp-windows-v535.zip` |
| Windows extract path | `%USERPROFILE%\EIDP-v535-d742327-env0` |
| current active root to preserve | `%USERPROFILE%\EIDP-v527-69fe81f-env0` |
| non-Windows release gate | `logs/win-v535-stage6-v535-non-windows-release-gates-20260620.json` -> `ok=true` |
| GitHub main CI | re-check current `main` before release approval; do not copy stale run IDs |
| Windows validation evidence | `docs/reports/2026-06-20-v535-full-windows-side-by-side-smoke.md` |
| OCR runtime evidence | v535 OCR runtime validation is not complete; required if OCR remains in v1.0 scope |
| UI smoke evidence | `win-v535-stage6-v535-ui-smoke-20260620.json` in `logs/win-v535-stage6/` |
| Excel smoke evidence | `win-v535-stage6-v535-excel-summary-clean-20260620.json` in `logs/win-v535-stage6/` |
| bounded canary evidence | strict/Excel-ready `12/50 (24.0%)`, operator-reviewable `47/50 (94.0%)`, `ship_gate_status=below_gate` |
| Stage 6 evidence verify | `stage6-evidence-verify-20260620-143033.json` -> `ok=true` |
| release exception reason | `publication_lag` if Route A is chosen |
| mature-year proof JSON | `logs/mature-year-acquisition-proof-fy2025-release-exception-v497-20260519.json` |
| mature-year proof years | `2025` |

The v535 bounded canary is side-by-side smoke evidence only. It is not owner
real-cycle sign-off evidence.

## Fields The Owner/Operator Must Fill From The Real Cycle

Do not copy bounded-canary values into these fields. Fill them from the owner
real cycle and returned diagnostics.

| Required E2E row | Fill from |
| --- | --- |
| `ship_readiness_rc` | latest owner-cycle `diagnostics-*.txt` / `last_run.json` |
| `strict target PDF 自動取得率` | owner-cycle diagnostics / `last_run.json` |
| `推定手作業率` | owner-cycle diagnostics / `last_run.json` |
| `Excel ready 率` | owner-cycle diagnostics and Excel proof |
| `Excel 整合性` | output workbook metadata or redacted workbook proof |
| `監査ログページ表示` | operator UI audit page proof |
| `manual_action_log 件数` | DB / diagnostics / audit page count |
| `JSONL outbox 未送信件数` | before/after flush proof |
| `audit-flush 実行` | `pass` or `not needed`, with reason |
| `JSONL action_id 重複` | `none` |
| `業務員 PC 1 サイクル完了` | `pass`, with returned log paths |
| `KPI owner 承認` | `pass`, with owner name/date |
| `残 P0/P1 bug` | `none`, or list blocker IDs |
| Owner sign-off | name, date, decision |
| 業務員 sign-off | name, date, decision |

## Files To Return

- completed `eidp-operator-e2e-template.md`
- approved `docs/reports/2026-05-19-publication-lag-release-exception-record.md`
- `data\output\last_run.json`
- latest `logs\run-*.log`
- latest `logs\diagnostics-*.txt`
- latest `logs\stage6-evidence-*.zip`
- latest `logs\stage6-evidence-verify-*.json`
- v535 setup validation JSON
- v535 active-task recovery JSON
- v535 UI smoke evidence
- Excel output proof or redacted workbook metadata
- ManualActionLog / JSONL outbox proof

## Developer Verification After Return

After copying the owner return files back to the repo, run:

```bash
uv run python scripts/verify_stage6_return.py \
  --e2e-template <filled-owner-e2e-template.md> \
  --last-run <returned-data-output-last_run.json> \
  --evidence-verify-json <returned-stage6-evidence-verify.json> \
  --release-exception-reason publication_lag \
  --mature-year-proof-json logs/mature-year-acquisition-proof-fy2025-release-exception-v497-20260519.json \
  --release-exception-record docs/reports/2026-05-19-publication-lag-release-exception-record.md \
  --json
```

Release remains blocked unless this command returns `ok=true` and the approval
record plus sign-off fields are complete.

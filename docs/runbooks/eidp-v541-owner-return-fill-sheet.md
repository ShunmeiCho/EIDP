# EIDP v541 Owner Return Fill Sheet

Date: 2026-06-21
Scope: v541 owner/operator return evidence only

This sheet is a fill aid for `docs/runbooks/eidp-operator-e2e-template.md`.
It is not release approval and does not replace the signed template,
`publication_lag` exception record, OCR scope decision, or
`scripts/verify_stage6_return.py`.

## Use This Only After The Owner Chooses Route A

Route A means:

1. the owner explicitly approves the `publication_lag` exception;
2. the owner explicitly selects OCR scope; and
3. the operator runs one real Stage 6 cycle on the v541 side-by-side lane; and
4. the completed template, logs, Excel proof, audit proof, and sign-offs are
   returned for verification.

If the owner chooses Route B, do not run the owner sign-off cycle yet. Keep
v1.0 on hold until enough FY2026/R8 target-form PDFs are public.

## Fixed Values To Copy Into The E2E Template

| E2E field | Value |
| --- | --- |
| EIDP package commit | `e62d074081e60428957a2f405c3a917bbceb31a0` |
| core ZIP ファイル名 | `eidp-windows-v541.zip` |
| core ZIP sha256 | `2ffb25884e15b9e2937f43bab7a8f5866d9434bc9f29f8067dbc1760397fa46f` |
| transferred ZIP | `C:\EIDP-staging\eidp-windows-v541.zip` |
| Windows extract path | `%USERPROFILE%\EIDP-v541-e62d074-env0` |
| current active root to preserve | `%USERPROFILE%\EIDP-v527-69fe81f-env0` |
| non-Windows release gate | `logs/win-v541-owner-signoff-release-path-gates-20260621.json` -> `ok=true` |
| GitHub main CI | packaged source commit e62d074: CI `27874800210` -> success; v541 evidence-docs commit 9981397: CI `27876116316` -> success; re-check current `main` before release approval |
| Windows validation evidence | `docs/reports/2026-06-21-v541-owner-signoff-verifier-windows-canary.md` |
| OCR runtime evidence | v541 OCR runtime validation is not complete; required if OCR remains in v1.0 scope |
| setup validation evidence | `docs/reports/2026-06-21-v541-owner-signoff-verifier-windows-canary.md` records after-setup validator `ok=true` |
| after-weekly validation evidence | `docs/reports/2026-06-21-v541-owner-signoff-verifier-windows-canary.md` records after-weekly validator `ok=true` |
| bounded canary evidence | strict/Excel-ready `12/50 (24.0%)`, operator-reviewable `47/50 (94.0%)`, `ship_gate_status=below_gate` |
| Stage 6 evidence verify | `logs/win-v541-e62d074-canary/stage6-evidence-verify-20260621-003707.json` -> `ok=true` |
| release exception reason | `publication_lag` if Route A is chosen |
| mature-year proof JSON | `logs/mature-year-acquisition-proof-fy2025-release-exception-v497-20260519.json` |
| mature-year proof years | `2025` |

The v541 bounded canary is side-by-side smoke evidence only. It is not owner
real-cycle sign-off evidence.

## Short Owner Decision Form

Use `docs/runbooks/eidp-v541-release-summary.md` as the owner-facing one-page
summary and `docs/runbooks/eidp-v541-owner-signoff.md` as the short owner
decision form. Do not ask the owner to manually fill or reproduce the
engineering checklist.

For v541, current evidence supports `NOT_READY` only. `publication_lag`
approval can support at most `RC_ONLY` after all required return evidence is
complete. It must not allow unconfirmed rows into final Excel output.

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
| OCR scope 決定 | `core_non_ocr_only` or `ocr_addon_verified` |
| Owner sign-off | name, date, decision |
| 業務員 sign-off | name, date, decision |

## Files To Return

- completed `eidp-operator-e2e-template.md`
- approved `docs/reports/2026-05-19-publication-lag-release-exception-record.md`
- selected OCR scope decision
- `data\output\last_run.json`
- latest `logs\run-*.log`
- latest `logs\diagnostics-*.txt`
- latest `logs\stage6-evidence-*.zip`
- latest `logs\stage6-evidence-verify-*.json`
- v541 setup validation evidence
- v541 active-task recovery JSON
- Excel output proof or redacted workbook metadata
- ManualActionLog / JSONL outbox proof
- completed false-reject review worksheet if claiming a discovery/classifier/year
  evidence false reject:
  `docs/reports/2026-06-21-v541-false-reject-review-sheet.csv`

## False-Reject RCA Worksheet

Use this only to support or reject the claim that the below-gate FY2026/R8
yield is caused by material discovery/classifier/year-evidence false rejects.
It does not relax the Excel-ready gate and does not allow rejected rows into the
final Excel output.

Worksheet to fill:

```text
docs/reports/2026-06-21-v541-false-reject-review-sheet.csv
```

Fill only these columns:

| Column | Required value |
| --- | --- |
| `decision` | `false_reject`, `correct_reject`, or `needs_operator_review` |
| `reviewer` | owner/operator reviewer name or stable reviewer ID |
| `reviewed_at` | ISO timestamp, for example `2026-06-21T09:30:00+09:00` |
| `notes` | required for `false_reject` and `needs_operator_review`; recommended for any difficult row |

Do not edit `audit_row_id`, `bucket`, school/document fields, URLs, anchor
text, review questions, or false-reject signals. Those columns are immutable
row context; if they change, developer validation must reject the worksheet.

Decision meanings:

- `false_reject`: official FY2026/R8 evidence proves the row should have been
  accepted or routed differently.
- `correct_reject`: the row is old-year, non-target, unknown-year, mismatched,
  unsupported, or otherwise correctly blocked.
- `needs_operator_review`: there is plausible official evidence, but it needs a
  human decision before it can affect any workflow or Excel output.

Developer validation is run from current `main` after the returned CSV is copied
back to the repo. The v541 Windows package itself is not enough evidence for
this post-v541 worksheet validation.

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
  --publication-lag-decision-brief docs/release/owner-decisions/publication-lag.md \
  --ocr-scope-decision-brief docs/release/owner-decisions/ocr-scope.md \
  --owner-signoff docs/runbooks/eidp-v541-owner-signoff.md \
  --expected-package-sha256 2ffb25884e15b9e2937f43bab7a8f5866d9434bc9f29f8067dbc1760397fa46f \
  --expected-source-commit e62d074081e60428957a2f405c3a917bbceb31a0 \
  --false-reject-evidence-zip logs/win-v541-e62d074-canary/stage6-evidence-20260620-153655.zip \
  --false-reject-review-csv docs/reports/2026-06-21-v541-false-reject-review-sheet.csv \
  --false-reject-sample-size 12 \
  --json
```

Release remains blocked unless this command returns `ok=true` and the approval
record, OCR scope, E2E sign-off fields, and short owner sign-off are complete.

If a completed false-reject review worksheet is returned outside the owner
return verifier, the same check can be run directly for debugging:

```bash
uv run python scripts/build_false_reject_audit.py \
  logs/win-v541-e62d074-canary/stage6-evidence-20260620-153655.zip \
  --sample-size 12 \
  --validate-review-csv docs/reports/2026-06-21-v541-false-reject-review-sheet.csv \
  --require-decisions
```

This command must return `ok=true`, `review_status=complete`, and
`context_mismatch_count=0` before the worksheet can be used as RCA evidence.

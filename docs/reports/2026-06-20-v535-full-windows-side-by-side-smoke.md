# v535 Full Windows Side-By-Side Smoke

Date: 2026-06-20
Package: `dist/eidp-windows-v535.zip`
Package SHA256: `72ef94f35a2cd482eb9650d1a466cb8441f7d96a660a8901710d96603e7d8e9f`
Package/source commit: `d742327570a08a8f9d6ade7adfc81da8940294b4`
Windows root: `C:\Users\cyo20\EIDP-v535-d742327-env0`

## Scope

This report records the v535 Windows side-by-side validation run after SSH to
the Windows operator machine was restored. It supersedes v533 as the latest
complete non-OCR Windows side-by-side smoke evidence, but it does not approve
v1.0 release.

The release boundary remains:

- FY2026/Reiwa 8 strict current-year acquisition is below the release gate.
- Owner/operator real-cycle sign-off is still missing.
- The `publication_lag` release exception remains `NOT_APPROVED`.
- OCR scope remains unresolved because the latest complete OCR runtime proof
  is not from v535.

## Evidence Location

Pulled evidence is stored on the external SSD through the repository `logs`
symlink:

```text
logs/win-v535-stage6/
```

The directory contains the consolidated summary, setup/recovery/UI/weekly/
Excel JSON evidence, and the Stage 6 evidence ZIP:

```text
logs/win-v535-stage6/win-v535-stage6-v535-side-by-side-summary-20260620.json
logs/win-v535-stage6/stage6-evidence-20260620-053032.zip
logs/win-v535-stage6/stage6-evidence-verify-20260620-143033.json
```

Mac-side verifier also accepted the pulled Stage 6 ZIP:

```text
ok: true
entry_count: 7
present_labels: build_info, diagnostics, discovery_evidence, discovery_rca, last_run, weekly_run_logs
missing_required_labels: []
errors: []
warnings: []
unsafe_entries: []
forbidden_entries: []
```

Non-required missing patterns were `bootstrap_logs`, `bootstrap_progress`,
`stage6_recovery`, and `stage6_residual_cleanup`.

## Windows Side-By-Side Evidence

| Check | Evidence |
| --- | --- |
| Package transfer / SHA | Windows `Get-FileHash` matched `72ef94f35a2cd482eb9650d1a466cb8441f7d96a660a8901710d96603e7d8e9f`; package size was `210,911,567` bytes. |
| Setup | `EIDP-setup.bat` ran in `C:\Users\cyo20\EIDP-v535-d742327-env0` with `EIDP_REGISTER_WEEKLY_TASK=0` and returned rc `0`; the active scheduled task stayed on v527. |
| Setup validator | `win-v535-stage6-v535-env0-validate-after-setup-20260620.json` -> `ok=true`, `school_count=2418`, `school_fiscal_year_status_count=2418`, SQLite integrity `ok`, wheel count `84`, build commit `d742327570a08a8f9d6ade7adfc81da8940294b4`. |
| Active-task safety | `win-v535-stage6-v535-recovery-expected-v527-lock-20260620.json` -> `ok=true`; active `EIDP Weekly Run` still points to `C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat`; lock probe `ok=true`, held `false`; historical v384 residual paths absent. |
| UI smoke | `win-v535-stage6-v535-ui-smoke-20260620.json` -> `ok=true`, bound to `127.0.0.1:8535`, health `200/ok`, root `200`, process stopped, and no listener remained after stop. |
| Weekly limit-50 canary | `win-v535-stage6-v535-side-by-side-summary-20260620.json` and `last_run.json` -> weekly rc `0`, `status=success`, `current_fy=2026`, `selection_mode=target_missing`, strict/Excel-ready `12/50 (24.0%)`, operator-reviewable `47/50 (94.0%)`, `ship_gate_status=below_gate`. |
| Discovery / ingest | v535 canary crawled `59` site rows, found `50` candidates, downloaded `15`, failed `1`, and processed `15` documents into `122` new departments and `129` yearly upserts. RCA rejects include `pre_filtered_non_target_hint=432`, `fiscal_year_mismatch=206`, `classified_non_target=103`, `target_fiscal_year_not_detected=6`, `no_candidates_found=9`, `http_error_httpstatuserror=1`, and `pdf_school_mismatch=2`. |
| Validate after weekly | `win-v535-stage6-v535-validate-after-weekly-canary-20260620.json` -> `ok=true`; the consolidated summary records validate rc `0`. |
| Excel smoke | `win-v535-stage6-v535-excel-summary-clean-20260620.json` -> `ok=true`; master workbook length `3,746,064`, competition workbook length `121,897`, competition gap CSV length `48,116`; competition export recorded `matched=6`, `unmatched=373`, `cells_written=12`, `target_yearly_rows=129`, `excel_ready_schools=12`. |
| Stage 6 bundle | `stage6-evidence-20260620-053032.zip` created with collector rc `0`. |
| Stage 6 verifier | `stage6-evidence-verify-20260620-143033.json` -> `ok=true`; Mac-side re-verification also returned `ok=true`, with no required labels missing and no unsafe or forbidden entries. |

## Release Boundary

v535 now replaces v533 as the latest package with current Windows side-by-side
smoke evidence for setup, active-task safety, UI, bounded weekly canary, Excel
export, Stage 6 bundle creation, and Stage 6 evidence verification.

It still cannot be promoted to v1.0 because the current FY2026/Reiwa 8 strict
target-document and Excel-ready yield is `12/50 (24.0%)`, below the `>= 60%`
release line. The operator-reviewable rate is `47/50 (94.0%)`, which is useful
for HITL triage but still implies manual workload above the release threshold.

If OCR remains in v1.0 scope, an approved OCR add-on must be restored and
validated for v535 or a later candidate. If OCR is moved out of v1.0 scope,
that must be a written release-scope decision rather than an implicit omission.

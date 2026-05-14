# EIDP Current Objective Evidence Checklist

Updated: 2026-05-14
Source HEAD: `3a59c08d3cd93baafb8c941e0555e2bc8ccbbfdc`
Status: **NOT COMPLETE**

This checklist maps the long-term EIDP objective to concrete artifacts and gates.
It is intentionally separate from ZIP packaging: no new ZIP has been built for
`3a59c08`, and the active operator-PC Stage 6 lane remains the existing v399
extraction.

## Objective Restatement

EIDP must let one Windows operator process 1,700+ Japanese vocational schools
each rolling fiscal year by discovering official school pages, finding true
target-FY institution-requirement confirmation PDFs in strict mode, extracting
only sufficiently confident rows, writing append-only database records, exporting
the Excel template, auditing all operator actions, and running offline from a ZIP
with double-click setup and browser UI.

Release success is not full automation. The shipping line is true target-form PDF
auto-acquisition of 60-70% and estimated operator manual work at 30% or lower.

## Prompt-To-Artifact Checklist

| Requirement | Current artifacts / evidence | Status |
| --- | --- | --- |
| 47 prefecture official lists seed school URLs | `scripts/verify_windows_distribution.py` verifier contract; `docs/reports/current-release-status.md` records 47 prefecture seeds and official-index bounded smokes | Partially proven; current source not packaged after `3a59c08` |
| Strict target-FY PDF discovery excludes stale fallback from success | `src/eidp/scraper/pdf_discovery.py`; `tests/unit/test_pdf_discovery.py`; v375 heading/update-date tests pass; source HEAD also guards romanized-only renewal-form hints; current evidence records strict FY2026 auto-yield still `0.0` on bounded Windows smokes | Mechanically guarded; yield gate failing |
| PDF extraction uses pdfplumber / PyMuPDF / Tesseract and writes only confidence >= 0.70 | OCR/package verifier contracts; v384 OCR image/write smoke; unit coverage for confidence propagation | Mechanically proven for smokes; no current strict target-form OCR workload evidence |
| DepartmentYearly / SupportRecipient append-only writes | Unit coverage plus v384 copied-DB UI/manual-entry, fiscal override, and SupportRecipient ingest smokes | Proven on sandboxed/copy DB paths; not yet v399 one-cycle proof |
| Excel template export | v384 R7 retroactive Excel preview/download proof; FY2026 export remains disabled with `Excel出力可 0/2418` on current setup evidence | R7 rehearsal proven; FY2026 target-year output not ready |
| ManualActionLog audits every operator action | v384 manual-entry, fiscal override, URL-candidate reject, and audit outbox browser smokes; source HEAD dedups audit outbox archives by matching filename stem for both default and custom outbox paths | Proven on older sandboxed paths; v399 write-cycle still missing |
| ZIP distribution, double-click setup, browser UI offline operation | v399 transfer, SHA match, setup completion, SQLite integrity, CLI smoke, and manual Streamlit health; v397 browser read-only navigation | Setup/service proven on v399; browser-click write-cycle missing |
| Stage 6 one operator-PC cycle | `docs/runbooks/eidp-operator-e2e-template.md`; `docs/reports/current-release-status.md` Stage 6 boundary | Missing |
| Ship gate: true target-form auto-acquisition 60-70% | Latest recorded strict target PDF auto-yield remains `0.0%`; `ship_readiness_rc=1` in current Windows evidence | Failing |
| Ship gate: estimated manual work <= 30% | Current evidence records operator-reviewable yield far below release threshold and manual workload effectively above target | Failing |

## Current Release Boundary

- Active Windows transfer/setup proof: v399, commit
  `12719c0dc929d3b8727f6e8486931239e29a7145`, SHA256
  `bd4846796bdae16977d0aedfee6afcd56a7cee3abcaa2c9cfac5e9fabc6c6f97`.
- Current source HEAD: `3a59c08`, with Stage 6 safety fixes for recovery check,
  evidence bundle Excel exclusion, residual cleanup symlink/junction safety,
  clarified ship-readiness criteria semantics, audit outbox custom-archive
  dedup, and stricter romanized renewal-form hint handling.
- The source safety and discovery fixes are not present in the existing v399 ZIP.
- Do not mark the goal complete until v399 or a future approved package completes
  operator-PC browser write-cycle evidence and the rolling FY yield gate.

## Current Local Verification

Latest local checks performed against source HEAD `3a59c08`:

- `uv run pytest tests/unit/test_pdf_discovery.py -q -k "renewal or koushin or english_renewal or target_form or pre_download"`
  -> `38 passed, 124 deselected, 5 warnings`.
- `uv run ruff check src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py`
  -> `All checks passed`.
- `uv run mypy src/eidp/scraper/pdf_discovery.py`
  -> `Success: no issues found in 1 source file`.
- `uv run pytest tests/unit/test_audit_outbox.py tests/unit/test_windows_distribution_verifier.py::test_verify_core_zip_requires_manual_action_audit_contract tests/unit/test_discovery_gold_set_seed.py tests/unit/test_cli_pdf_discovery_strict.py::test_import_excel_surfaces_invalid_year_warning tests/unit/test_importer_idempotency.py::test_taisho_hiritu_skips_unrealistic_future_fiscal_year tests/unit/test_importer_idempotency.py::test_parse_fiscal_year_rejects_unrealistic_future_era_label -q`
  -> `24 passed`.
- `uv run ruff check src/eidp/db/audit_outbox.py scripts/verify_windows_distribution.py tests/unit/test_audit_outbox.py tests/unit/test_windows_distribution_verifier.py`
  -> `All checks passed`.
- `uv run mypy src/eidp/db/audit_outbox.py scripts/verify_windows_distribution.py`
  -> `Success: no issues found in 2 source files`.
- `uv run pytest tests/unit/test_reports.py tests/unit/test_cli_reports.py tests/unit/test_ship_gate_contract.py tests/unit/test_bootstrap_pdf_pipeline.py::test_bootstrap_target_pdf_yield_metrics_marks_gate_status tests/unit/test_run_weekly_target_year_discovery.py::test_weekly_yield_metrics_count_review_candidate_statuses_as_operator_reviewable -q`
  -> `40 passed`.
- `uv run ruff check scripts/ship_gate_contract.py src/eidp/reports/ship_readiness.py tests/unit/test_reports.py tests/unit/test_cli_reports.py tests/unit/test_ship_gate_contract.py`
  -> `All checks passed`.
- `uv run mypy src/eidp/reports/ship_readiness.py`
  -> `Success: no issues found in 1 source file`.
- `uv run pytest tests/unit/test_stage6_recovery_check.py tests/unit/test_stage6_residual_cleanup.py tests/unit/test_stage6_evidence_bundle.py tests/unit/test_windows_packaging_spike.py tests/unit/test_windows_distribution_verifier.py -q`
  -> `197 passed`.
- `uv run mypy scripts/collect_stage6_evidence.py scripts/verify_stage6_evidence.py scripts/stage6_residual_cleanup.py scripts/stage6_recovery_check.py scripts/verify_windows_distribution.py`
  -> `Success: no issues found in 5 source files`.
- `uv run ruff check scripts/collect_stage6_evidence.py scripts/verify_stage6_evidence.py scripts/stage6_residual_cleanup.py scripts/stage6_recovery_check.py scripts/verify_windows_distribution.py tests/unit/test_stage6_evidence_bundle.py tests/unit/test_stage6_residual_cleanup.py tests/unit/test_stage6_recovery_check.py tests/unit/test_windows_packaging_spike.py`
  -> `All checks passed`.
- `uv run pytest tests/unit/test_pdf_discovery.py -q -k "heading_year or intervening_non_year_block or update_date or publication_date or western_year_anchor or reiwa_year_anchor"`
  -> `9 passed, 152 deselected, 5 warnings`.

## Next Concrete Gate

When Windows/SSH access is restored, continue the frozen v399 lane without
building a new ZIP:

```bash
ssh -N -o ClearAllForwardings=no -o ExitOnForwardFailure=yes -L 127.0.0.1:18501:127.0.0.1:8501 win
```

Then verify the UI at `http://127.0.0.1:18501/` and complete the Stage 6
click-through: manual PDF entry write, fiscal-year override write, R7 Excel
preview/download, audit log/outbox flush, diagnostics capture, evidence verify,
and sign-off fields.

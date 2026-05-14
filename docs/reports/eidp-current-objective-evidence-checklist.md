# EIDP Current Objective Evidence Checklist

Updated: 2026-05-14
Code evidence HEAD: `b3285895427c8e2c9df473eb34f84f28daae9f35`
Status: **NOT COMPLETE**

This checklist maps the long-term EIDP objective to concrete artifacts and gates.
It is intentionally separate from ZIP packaging: no new ZIP has been built for
the code evidence base `b328589`, and the active operator-PC Stage 6 lane
remains the existing v399 extraction. Later documentation-only commits may
extend this checklist without changing that source-code evidence base.

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
| 47 prefecture official lists seed school URLs | `scripts/verify_windows_distribution.py` verifier contract; `docs/reports/current-release-status.md` records 47 prefecture seeds and official-index bounded smokes | Partially proven; code evidence base not packaged after `b328589` |
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
- Current source-code evidence base: `b328589`, with Stage 6 safety fixes for recovery check,
  evidence bundle Excel exclusion, residual cleanup symlink/junction safety,
  clarified ship-readiness criteria semantics, audit outbox custom-archive
  dedup, stricter romanized renewal-form hint handling, and typed fiscal-year
  override / PDF ingest / PDF OCR / Excel exporter / Excel import stats /
  manual audit / operator UI paths, plus typed bootstrap URL crawl mode.
- The source safety and discovery fixes are not present in the existing v399 ZIP.
- Do not mark the goal complete until v399 or a future approved package completes
  operator-PC browser write-cycle evidence and the rolling FY yield gate.

## Current Local Verification

Latest local checks performed against source-code evidence base `b328589`:

- `uv run pytest tests/unit -q`
  -> `1437 passed, 5 warnings in 38.72s`.
- `uv run mypy src/eidp/scraper/url_discovery.py src/eidp/scraper/school_url_pipeline.py src/eidp/scraper/school_url_persistence.py src/eidp/scraper/pdf_discovery.py scripts/bootstrap_pdf_pipeline.py scripts/run_weekly_target_year_discovery.py src/eidp/cli.py`
  -> `Success: no issues found in 7 source files`.
- `uv run ruff check src/eidp/scraper/url_discovery.py src/eidp/scraper/school_url_pipeline.py src/eidp/scraper/school_url_persistence.py src/eidp/scraper/pdf_discovery.py scripts/bootstrap_pdf_pipeline.py scripts/run_weekly_target_year_discovery.py src/eidp/cli.py tests/unit/test_url_discovery.py tests/unit/test_school_url_pipeline.py tests/unit/test_school_url_persistence.py tests/unit/test_cli_crawl_school_urls.py tests/unit/test_pdf_discovery.py tests/unit/test_cli_pdf_discovery_strict.py tests/unit/test_bootstrap_pdf_pipeline.py tests/unit/test_run_weekly_target_year_discovery.py`
  -> `All checks passed`.
- `uv run pytest tests/unit/test_url_discovery.py tests/unit/test_school_url_pipeline.py tests/unit/test_school_url_persistence.py tests/unit/test_cli_crawl_school_urls.py tests/unit/test_pdf_discovery.py tests/unit/test_cli_pdf_discovery_strict.py tests/unit/test_bootstrap_pdf_pipeline.py tests/unit/test_run_weekly_target_year_discovery.py -q`
  -> `264 passed, 5 warnings in 15.45s`.
- `uv run mypy src/eidp/review/app.py src/eidp/review/operator_pages.py src/eidp/review/school_scope.py src/eidp/review/target_year_status.py src/eidp/review/confidence_panels.py src/eidp/review/_pages/school_year_tasks.py src/eidp/review/_pages/url_candidate_review.py src/eidp/review/_pages/settings_page.py src/eidp/review/_pages/prefecture_remarks.py`
  -> `Success: no issues found in 9 source files`.
- `uv run ruff check src/eidp/review/app.py src/eidp/review/operator_pages.py src/eidp/review/school_scope.py src/eidp/review/target_year_status.py src/eidp/review/confidence_panels.py src/eidp/review/_pages/school_year_tasks.py src/eidp/review/_pages/url_candidate_review.py src/eidp/review/_pages/settings_page.py src/eidp/review/_pages/prefecture_remarks.py tests/unit/test_review_app.py tests/unit/test_review_school_scope.py tests/unit/test_review_school_year_tasks.py tests/unit/test_review_url_candidate_review.py tests/unit/test_review_confidence_panels.py tests/unit/test_review_prefecture_remarks.py`
  -> `All checks passed`.
- `uv run pytest tests/unit/test_review_app.py tests/unit/test_review_school_scope.py tests/unit/test_review_school_year_tasks.py tests/unit/test_review_url_candidate_review.py tests/unit/test_review_confidence_panels.py tests/unit/test_review_prefecture_remarks.py -q`
  -> `104 passed in 2.12s`.
- `uv run mypy scripts/validate_windows_install.py scripts/verify_windows_distribution.py scripts/run_non_windows_release_gates.py`
  -> `Success: no issues found in 3 source files`.
- `uv run ruff check scripts/validate_windows_install.py scripts/verify_windows_distribution.py scripts/run_non_windows_release_gates.py tests/unit/test_windows_install_validator.py tests/unit/test_windows_distribution_verifier.py tests/unit/test_non_windows_release_gates.py`
  -> `All checks passed`.
- `uv run pytest tests/unit/test_windows_install_validator.py tests/unit/test_non_windows_release_gates.py -q`
  -> `52 passed in 1.16s`.
- `uv run pytest tests/unit/test_windows_distribution_verifier.py tests/unit/test_windows_packaging_spike.py -q`
  -> `180 passed in 3.99s`.
- `uv run mypy src/eidp/scraper/prefecture_aggregator.py src/eidp/scraper/discovery_gold_set.py scripts/verify_windows_distribution.py`
  -> `Success: no issues found in 3 source files`.
- `uv run ruff check src/eidp/scraper/prefecture_aggregator.py src/eidp/scraper/discovery_gold_set.py scripts/verify_windows_distribution.py tests/unit/test_discovery_gold_set_seed.py tests/unit/test_windows_distribution_verifier.py`
  -> `All checks passed`.
- `uv run pytest tests/unit/test_discovery_gold_set_seed.py tests/unit/test_windows_distribution_verifier.py -q`
  -> `111 passed in 4.56s`.
- `uv run mypy src/eidp/scraper/prefecture_aggregator.py scripts/download_prefecture_artifacts.py`
  -> `Success: no issues found in 2 source files`.
- `uv run ruff check src/eidp/scraper/prefecture_aggregator.py scripts/download_prefecture_artifacts.py tests/unit/test_prefecture_aggregator.py tests/unit/test_prefecture_artifact_bootstrap.py tests/unit/test_cli_prefecture_aggregate_safety.py tests/unit/test_review_prefecture_remarks.py`
  -> `All checks passed`.
- `uv run pytest tests/unit/test_prefecture_aggregator.py tests/unit/test_prefecture_artifact_bootstrap.py tests/unit/test_cli_prefecture_aggregate_safety.py tests/unit/test_review_prefecture_remarks.py -q`
  -> `47 passed, 5 warnings in 1.44s`.
- `uv run mypy src/eidp/pdf/extractor.py src/eidp/pdf/ocr.py src/eidp/pdf/schema.py src/eidp/pipeline/ingest.py`
  -> `Success: no issues found in 4 source files`.
- `uv run ruff check src/eidp/pdf/extractor.py src/eidp/pdf/ocr.py src/eidp/pdf/schema.py src/eidp/pipeline/ingest.py tests/unit/test_pdf_parser_regression.py tests/unit/test_pdf_ocr_tesseract_provider.py tests/unit/test_ingest_confidence_gating.py`
  -> `All checks passed`.
- `uv run pytest tests/unit/test_pdf_parser_regression.py tests/unit/test_pdf_ocr_tesseract_provider.py tests/unit/test_ingest_confidence_gating.py -q`
  -> `37 passed in 6.16s`.
- `uv run mypy src/eidp/excel/importer.py src/eidp/cli.py`
  -> `Success: no issues found in 2 source files`.
- `uv run ruff check src/eidp/excel/importer.py src/eidp/cli.py tests/unit/test_cli_pdf_discovery_strict.py tests/unit/test_importer_idempotency.py`
  -> `All checks passed`.
- `uv run pytest tests/unit/test_cli_pdf_discovery_strict.py::test_import_excel_surfaces_invalid_year_warning tests/unit/test_importer_idempotency.py::test_taisho_hiritu_skips_unrealistic_future_fiscal_year tests/unit/test_importer_idempotency.py::test_parse_fiscal_year_rejects_unrealistic_future_era_label -q`
  -> `3 passed in 0.57s`.
- `uv run pytest tests/unit/test_importer_idempotency.py tests/unit/test_cli_pdf_discovery_strict.py -q`
  -> `13 passed in 0.78s`.
- `uv run mypy src/eidp/review/_pages/pdf_manual_entry.py src/eidp/review/_pages/excel_preview.py src/eidp/review/_pages/fiscal_year_override.py`
  -> `Success: no issues found in 3 source files`.
- `uv run ruff check src/eidp/review/_pages/pdf_manual_entry.py src/eidp/review/_pages/excel_preview.py src/eidp/review/_pages/fiscal_year_override.py tests/unit/test_review_pdf_manual_entry.py tests/unit/test_review_excel_preview.py tests/unit/test_review_fiscal_year_override.py`
  -> `All checks passed`.
- `uv run pytest tests/unit/test_review_pdf_manual_entry.py tests/unit/test_review_excel_preview.py tests/unit/test_review_fiscal_year_override.py -q`
  -> `63 passed, 5 warnings in 2.40s`.
- `uv run mypy src/eidp/pipeline/manual_entry.py src/eidp/review/_pages/audit_log.py`
  -> `Success: no issues found in 2 source files`.
- `uv run ruff check src/eidp/pipeline/manual_entry.py src/eidp/review/_pages/audit_log.py tests/unit/test_manual_entry_contract.py tests/unit/test_review_pdf_manual_entry.py tests/unit/test_review_audit_log.py tests/unit/test_review_audit_log_dashboard.py`
  -> `All checks passed`.
- `uv run pytest tests/unit/test_manual_entry_contract.py tests/unit/test_review_pdf_manual_entry.py tests/unit/test_review_audit_log.py tests/unit/test_review_audit_log_dashboard.py -q`
  -> `78 passed, 5 warnings in 2.67s`.
- `uv run ruff check src/eidp/excel/exporter.py tests/unit/test_excel_exporter.py tests/unit/test_review_excel_preview.py`
  -> `All checks passed`.
- `uv run mypy src/eidp/excel/exporter.py`
  -> `Success: no issues found in 1 source file`.
- `uv run pytest tests/unit/test_excel_exporter.py tests/unit/test_review_excel_preview.py -q`
  -> `14 passed in 1.07s`.
- `uv run ruff check src/eidp/pipeline/ingest.py tests/unit/test_ingest_confidence_gating.py tests/unit/test_ingest_alias_consultation.py tests/unit/test_normal_ingest_appendonly.py`
  -> `All checks passed`.
- `uv run mypy src/eidp/pipeline/ingest.py`
  -> `Success: no issues found in 1 source file`.
- `uv run pytest tests/unit/test_ingest_confidence_gating.py tests/unit/test_ingest_alias_consultation.py tests/unit/test_normal_ingest_appendonly.py -q`
  -> `36 passed in 1.76s`.
- `uv run pytest tests/unit/test_ingest_confidence_gating.py -q`
  -> `27 passed in 0.96s`; confirms low-confidence DepartmentYearly /
  SupportRecipient revisions are append-only but parked out of current Excel
  surfaces until operator review.
- `uv run pytest tests/unit/test_manual_entry_contract.py tests/unit/test_review_pdf_manual_entry.py tests/unit/test_fiscal_year_override.py tests/unit/test_review_audit_log.py tests/unit/test_review_audit_log_dashboard.py tests/unit/test_excel_exporter.py tests/unit/test_review_excel_preview.py -q`
  -> `101 passed, 5 warnings in 3.32s`; covers manual-entry append-only writes,
  fiscal-year override audit rows, audit-log/outbox helpers, and Excel export /
  preview surfaces at unit level.
- `uv run ruff check src/eidp/pipeline/fiscal_year_override.py tests/unit/test_fiscal_year_override.py tests/unit/test_review_fiscal_year_override.py`
  -> `All checks passed`.
- `uv run mypy src/eidp/pipeline/fiscal_year_override.py`
  -> `Success: no issues found in 1 source file`.
- `uv run pytest tests/unit/test_fiscal_year_override.py tests/unit/test_review_fiscal_year_override.py -q`
  -> `20 passed in 0.95s`.
- `uv run eidp discovery-gold-set --json`
  -> `44` entries, `10` strict target-year successes, `17` publication-lag
  entries, and `undemonstrated_pattern_sources=[]`.
- `uv run eidp eval-discovery-gold --predictions data/discovery-gold-set/expected-predictions.jsonl --fail-on-regression --json`
  -> `44` exact matches, `0` failed predictions, `0` missing entries, and `0`
  unexpected predictions.
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
  -> `40 passed in 0.92s`.
- `uv run ruff check scripts/ship_gate_contract.py src/eidp/reports/ship_readiness.py src/eidp/cli_reports.py tests/unit/test_reports.py tests/unit/test_cli_reports.py tests/unit/test_ship_gate_contract.py`
  -> `All checks passed`.
- `uv run mypy scripts/ship_gate_contract.py src/eidp/reports/ship_readiness.py src/eidp/cli_reports.py`
  -> `Success: no issues found in 3 source files`.
- `uv run pytest tests/unit/test_stage6_recovery_check.py tests/unit/test_stage6_residual_cleanup.py tests/unit/test_stage6_evidence_bundle.py tests/unit/test_windows_packaging_spike.py tests/unit/test_windows_distribution_verifier.py -q`
  -> `197 passed`.
- `uv run mypy scripts/collect_stage6_evidence.py scripts/verify_stage6_evidence.py scripts/stage6_residual_cleanup.py scripts/stage6_recovery_check.py scripts/verify_windows_distribution.py`
  -> `Success: no issues found in 5 source files`.
- `uv run ruff check scripts/collect_stage6_evidence.py scripts/verify_stage6_evidence.py scripts/stage6_residual_cleanup.py scripts/stage6_recovery_check.py scripts/verify_windows_distribution.py tests/unit/test_stage6_evidence_bundle.py tests/unit/test_stage6_residual_cleanup.py tests/unit/test_stage6_recovery_check.py tests/unit/test_windows_packaging_spike.py`
  -> `All checks passed`.
- `uv run pytest tests/unit/test_pdf_discovery.py -q -k "heading_year or intervening_non_year_block or update_date or publication_date or western_year_anchor or reiwa_year_anchor"`
  -> `9 passed, 152 deselected, 5 warnings`.

Known non-goal-wide lint boundary:

- `uv run ruff check .` currently scans untracked `_temp/` extractions and
  historical one-off scripts; it reported existing lint debt and is not a
  reliable current-source release gate. Goal-relevant changed surfaces above
  were checked with targeted Ruff/Mypy commands.
- `uv run mypy src` currently reports existing project-wide type debt across
  21 files, including optional OCR/openpyxl stubs and historical UI/scraper
  modules. The target-year override path has been cleaned and verified with
  targeted Ruff/Mypy/tests above.

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

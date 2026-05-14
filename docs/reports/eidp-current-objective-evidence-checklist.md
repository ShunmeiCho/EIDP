# EIDP Current Objective Evidence Checklist

Updated: 2026-05-14
Latest code-affecting source evidence base: `cd07c2136438f282895ccc37beaa3a5df28ed816`
Status: **NOT COMPLETE**

This checklist maps the long-term EIDP objective to concrete artifacts and gates.
It is intentionally separate from ZIP packaging: no new ZIP has been built for
the code evidence base `cd07c213`, and the active operator-PC Stage 6 lane
remains the existing v399 extraction. Later documentation-only commits may
refresh this checklist without changing that code evidence base.

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
| 47 prefecture official lists seed school URLs | `scripts/verify_windows_distribution.py` verifier contract; `docs/reports/current-release-status.md` records 47 prefecture seeds and official-index bounded smokes; source HEAD preserves semantic trailing slashes for gold-set disclosure seed entrypoints while keeping normalized idempotency | Partially proven; code evidence base not packaged after `cd07c213` |
| Strict target-FY PDF discovery excludes stale fallback from success | `src/eidp/scraper/pdf_discovery.py`; `src/eidp/scraper/discovery_evidence_summary.py`; `tests/unit/test_pdf_discovery.py`; v375 heading/update-date tests pass; source HEAD also guards romanized-only renewal-form hints in both strong application and weak form-shape detection, prioritizes yearless target-form evidence over older-year target evidence in RCA triage, and inherits same-section support-system headings for year-only target-form links so they enter the download budget before generic `様式4` PDFs | Mechanically guarded; yield gate failing |
| PDF extraction uses pdfplumber / PyMuPDF / Tesseract and writes only confidence >= 0.70 | OCR/package verifier contracts; v384 OCR image/write smoke; unit coverage for confidence propagation; source HEAD names the default `0.70` review threshold via `DEFAULT_CONFIDENCE_REVIEW` and keeps Excel/exporter env-threshold tests green | Mechanically proven for smokes; no current strict target-form OCR workload evidence |
| DepartmentYearly / SupportRecipient append-only writes | Unit coverage plus v384 copied-DB UI/manual-entry, fiscal override, and SupportRecipient ingest smokes | Proven on sandboxed/copy DB paths; not yet v399 one-cycle proof |
| Excel template export | v384 R7 retroactive Excel preview/download proof; FY2026 export remains disabled with `Excel出力可 0/2418` on current setup evidence | R7 rehearsal proven; FY2026 target-year output not ready |
| ManualActionLog audits every operator action | v384 manual-entry, fiscal override, URL-candidate reject, and audit outbox browser smokes; source HEAD dedups audit outbox archives by matching filename stem for both default and custom outbox paths and ignores archive symlinks | Proven on older sandboxed paths; v399 write-cycle still missing |
| ZIP distribution, double-click setup, browser UI offline operation | v399 transfer, SHA match, setup completion, SQLite integrity, CLI smoke, and manual Streamlit health; v397 browser read-only navigation | Setup/service proven on v399; browser-click write-cycle missing |
| Stage 6 one operator-PC cycle | `docs/runbooks/eidp-operator-e2e-template.md`; `docs/reports/current-release-status.md` Stage 6 boundary | Missing |
| Ship gate: true target-form auto-acquisition 60-70% | Latest recorded strict target PDF auto-yield remains `0.0%`; `ship_readiness_rc=1` in current Windows evidence | Failing |
| Ship gate: estimated manual work <= 30% | Current evidence records operator-reviewable yield far below release threshold and manual workload effectively above target | Failing |

## Current Release Boundary

- Active Windows transfer/setup proof: v399, commit
  `12719c0dc929d3b8727f6e8486931239e29a7145`, SHA256
  `bd4846796bdae16977d0aedfee6afcd56a7cee3abcaa2c9cfac5e9fabc6c6f97`.
- Current source-code evidence base: `cd07c213`, with Stage 6 safety fixes for recovery check,
  evidence bundle Excel exclusion, residual cleanup symlink/junction safety,
  clarified ship-readiness criteria semantics, audit outbox custom-archive
  dedup, stricter romanized renewal-form hint handling across strong and weak
  target-form hint paths, and typed fiscal-year
  override / PDF ingest / PDF OCR / Excel exporter / Excel import stats /
  manual audit / operator UI / bootstrap URL crawl / append-only audit-helper
  paths, plus unit-test isolation for Streamlit AppTest's fake `__main__`
  module before multiprocessing spawn tests, restored source-wide `mypy src`
  coverage for all 83 source files, and a non-Windows release-gate guard that
  rejects ZIPs whose packaged `BUILD_INFO.json` commit differs from the current
  source HEAD, or whose current source tree has uncommitted tracked changes,
  unless `--allow-stale-package` is explicitly used for historical checks.
  The Windows package and install validators also reject packaged
  `BUILD_INFO.json` values where `git_dirty` is not `false`, and
  `scripts/build_windows_zip.py` now refuses to produce a Windows ZIP from
  uncommitted tracked source unless `--allow-dirty` is explicitly used for a
  diagnostic build. Discovery RCA triage now prioritizes explicit
  `target_fiscal_year_not_detected` target-form evidence over older-year target
  evidence for the same school so operator review queues do not bury
  yearless current candidates behind publication-lag labels. Gold-set seeding
  now preserves semantic directory trailing slashes for disclosure entrypoints,
  PDF discovery now attaches same-section support-system headings to year-only
  target-form links before candidate prioritization, audit-outbox archive
  dedup ignores symlinks, and the extraction-confidence default thresholds are
  named constants used by `ConfidenceThresholds`. The packaged ZIP verifier now
  requires default Stage 6 tunnel guidance for `18501 -> 8501` in both the
  operator runbook and E2E evidence template. The non-Windows release gate also
  keeps `--allow-stale-package` dirty-safe: it can bypass a historical package
  commit mismatch, but still rejects uncommitted tracked source. The Windows
  install validator also rejects `last_run.json status=lock_busy` as weekly
  ship-gate evidence even if the payload claims `ship_gate_status=pass`. For
  bootstrap release-gate checks, progress-count mismatches against SQLite are
  fatal under `--require-ship-gate` while remaining warnings for structure-only
  validation.
- These source-code fixes are not present in the existing v399/v401 ZIPs.
  The latest recorded read-only rerun of the non-Windows package gate against
  v401 with the current verifier failed before downstream gates because
  `package_source_check` detected that packaged commit
  `2d9c9f690c6f955330ea49276ef1a87157ceb6cd` did not match the then-current
  source HEAD. The same stale-package boundary still applies to code evidence
  base `cd07c2136438f282895ccc37beaa3a5df28ed816`, because v401 packages
  commit `2d9c9f690c6f955330ea49276ef1a87157ceb6cd`.
- Do not mark the goal complete until v399 or a future approved package completes
  operator-PC browser write-cycle evidence and the rolling FY yield gate.

## Current Local Verification

Latest local checks performed against source-code evidence base `cd07c213`:

- `uv run mypy src`
  -> `Success: no issues found in 83 source files`.
- `uv run ruff check src`
  -> `All checks passed`.
- `uv run pytest tests/unit -q`
  -> `1459 passed, 5 warnings in 49.48s`.
- `uv run pytest tests/unit/test_pdf_discovery.py::test_pre_download_does_not_treat_romanized_renewal_form_alone_as_target -q`
  -> first run reproduced the weak-hint bug with `1 failed`; after the fix,
  the focused nearby renewal/priority set returned `4 passed in 1.37s`.
- `uv run pytest tests/unit/test_pdf_discovery.py -q`
  -> `163 passed, 5 warnings in 11.00s`.
- `uv run ruff check src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py && uv run mypy src/eidp/scraper/pdf_discovery.py`
  -> `All checks passed`; `Success: no issues found in 1 source file`.
- `uv run pytest tests/unit/test_discovery_evidence_summary.py -q`
  -> `14 passed in 0.36s`.
- `uv run pytest tests/unit/test_discovery_evidence_summary.py tests/unit/test_school_fiscal_year_status.py::test_rebuild_marks_publication_lag_evidence_as_review_state tests/unit/test_school_fiscal_year_status.py::test_rebuild_marks_target_form_without_year_evidence_as_review_state -q`
  -> `16 passed in 0.43s`.
- `uv run pytest tests/unit/test_cli_discovery_rca_packet.py -q`
  -> `24 passed in 0.60s`.
- `uv run pytest tests/unit/test_pdf_discovery.py tests/unit/test_cli_pdf_discovery_strict.py tests/unit/test_discovery_gold_set_seed.py tests/unit/test_url_normalization.py -q`
  -> `183 passed, 5 warnings in 12.42s`.
- `uv run pytest tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_summary.py tests/unit/test_cli_discovery_gold_set.py tests/unit/test_cli_eval_discovery_gold.py tests/unit/test_discovery_gold_set_eval.py tests/unit/test_discovery_gold_set_seed.py -q`
  -> `49 passed in 1.84s`.
- `uv run ruff check src/eidp/scraper/pdf_discovery.py src/eidp/scraper/discovery_gold_set.py tests/unit/test_pdf_discovery.py tests/unit/test_discovery_gold_set_seed.py tests/unit/test_url_normalization.py`
  -> `All checks passed`.
- `uv run mypy src/eidp/scraper/pdf_discovery.py src/eidp/scraper/discovery_gold_set.py`
  -> `Success: no issues found in 2 source files`.
- `uv run ruff check src/eidp/scraper/discovery_evidence_summary.py tests/unit/test_discovery_evidence_summary.py`
  -> `All checks passed`.
- `uv run mypy src/eidp/scraper/discovery_evidence_summary.py`
  -> `Success: no issues found in 1 source file`.
- Isolated live strict-discovery sample using temporary app root
  `_temp/live-discovery-ae835a1c-20260514-163155`:
  `uv run eidp db-bootstrap --sqlite`; `uv run eidp seed-discovery-gold-sites --gold-set-dir data/discovery-gold-set --apply`;
  `uv run eidp discover-pdfs --storage-dir "$run_dir/pdfs" --batch-size 10 --rate-limit 0.2 --request-timeout 12 --discovery-method discovery_gold_set --school-id 318 --school-id 1361 --school-id 758 --school-id 3205 --school-id 18 --school-id 74 --school-id 554 --school-id 757 --school-id 1532 --school-id 1533 --evidence-log "$run_dir/output/live-discovery-rejections.jsonl"`
  -> `crawled=10`, `found=10`, `downloaded=0`, `failed=1`, `skipped=185`,
  `rejection_reason_fiscal_year_mismatch=28`, and
  `rejection_reason_target_fiscal_year_not_detected=11`.
  Follow-up scoped summary after the RCA triage fix reported
  `publication_lag_or_old_target_pdf=6`, `target_form_without_year_evidence=3`,
  `non_target_candidates_only=1`, `no_evidence=34` across the 44 seeded
  gold-set sites; rebuild + ship-readiness on the same isolated DB reported
  `operator_reviewable_schools=9/44`, `operator_reviewable_rate=0.2045`,
  `strict_target_pdf_rate=0.0`, `excel_ready_schools=0`, and
  `ok_operator_review=false`.
- Isolated central-animal follow-up after the entrypoint/context fix using
  temporary app root `_temp/live-discovery-chuo-target-context-a17702f8-20260514-170031`:
  `uv run eidp db-bootstrap --sqlite`; `uv run eidp seed-discovery-gold-sites --gold-set-dir data/discovery-gold-set --apply`;
  `uv run eidp discover-pdfs --storage-dir "$run_dir/pdfs" --batch-size 1 --rate-limit 0.2 --request-timeout 12 --discovery-method discovery_gold_set --school-id 3205 --evidence-log "$run_dir/output/discovery.jsonl"`
  -> `crawled=1`, `found=1`, `downloaded=0`, `failed=0`,
  `rejection_reason_fiscal_year_mismatch=1`, and
  `rejection_reason_classified_non_target=10`. The first evidence row is
  `confirmation_2.pdf` with anchor text
  `2025年度 高等教育の修学支援新制度 申請書様式第2号`, score `7.5`, reason
  `fiscal_year_mismatch:2025`, and `pdf_type=target`; scoped summary reports
  `publication_lag_or_old_target_pdf=1` and `no_evidence=43`.
- `uv run ruff check scripts/build_windows_zip.py tests/unit/test_windows_packaging_spike.py`
  -> `All checks passed`.
- `uv run mypy scripts/build_windows_zip.py`
  -> `Success: no issues found in 1 source file`.
- `uv run pytest tests/unit/test_windows_packaging_spike.py -q`
  -> `78 passed in 0.55s`.
- `uv run pytest tests/unit/test_non_windows_release_gates.py tests/unit/test_windows_distribution_verifier.py tests/unit/test_windows_install_validator.py -q`
  -> `165 passed in 9.35s`.
- `uv run ruff check scripts/run_non_windows_release_gates.py tests/unit/test_non_windows_release_gates.py`
  -> `All checks passed`.
- `uv run mypy scripts/run_non_windows_release_gates.py`
  -> `Success: no issues found in 1 source file`.
- `uv run pytest tests/unit/test_non_windows_release_gates.py -q`
  -> `15 passed in 0.06s`.
- `uv run ruff check scripts/verify_windows_distribution.py scripts/validate_windows_install.py tests/unit/test_windows_distribution_verifier.py tests/unit/test_windows_install_validator.py`
  -> `All checks passed`.
- `uv run mypy scripts/verify_windows_distribution.py scripts/validate_windows_install.py`
  -> `Success: no issues found in 2 source files`.
- `uv run pytest tests/unit/test_windows_distribution_verifier.py tests/unit/test_windows_install_validator.py -q`
  -> `150 passed in 6.83s`.
- `uv run pytest tests/unit/test_windows_distribution_verifier.py::test_verify_core_zip_requires_current_operator_runbook_guidance tests/unit/test_windows_distribution_verifier.py::test_verify_core_zip_requires_retroactive_fy_e2e_template_fields tests/unit/test_windows_distribution_verifier.py::test_verify_core_zip_requires_stage6_recovery_e2e_template_fields tests/unit/test_windows_distribution_verifier.py::test_verify_core_zip_requires_default_stage6_tunnel_guidance -q`
  -> `4 passed`.
- `uv run ruff check scripts/verify_windows_distribution.py tests/unit/test_windows_distribution_verifier.py`
  -> `All checks passed`.
- `uv run mypy scripts/verify_windows_distribution.py`
  -> `Success: no issues found in 1 source file`.
- `uv run ruff check src/eidp/extraction_confidence.py tests/unit/test_extraction_confidence.py tests/unit/test_ingest_confidence_gating.py tests/unit/test_ocr_tesseract_wrapper.py tests/unit/test_review_confidence_panels.py`
  -> `All checks passed`.
- `uv run mypy src/eidp/extraction_confidence.py src/eidp/pipeline/ingest.py src/eidp/review/confidence_panels.py src/eidp/pdf/ocr.py`
  -> `Success: no issues found in 4 source files`.
- `uv run pytest tests/unit/test_extraction_confidence.py tests/unit/test_ingest_confidence_gating.py tests/unit/test_ocr_tesseract_wrapper.py tests/unit/test_review_confidence_panels.py -q`
  -> `127 passed in 5.79s`.
- `uv run ruff check src/eidp/ocr/tesseract.py tests/unit/test_ocr_tesseract_wrapper.py`
  -> `All checks passed`.
- `uv run mypy src/eidp/ocr/tesseract.py src/eidp/pdf/ocr.py`
  -> `Success: no issues found in 2 source files`.
- `uv run pytest tests/unit/test_ocr_tesseract_wrapper.py tests/unit/test_pdf_ocr_tesseract_provider.py -q`
  -> `21 passed in 0.69s`.
- `uv run ruff check src/eidp/pdf/eval_harness.py src/eidp/db/session.py src/eidp/scraper/discovery_rca_packet.py src/eidp/scraper/firecrawl_discovery.py src/eidp/matcher/reconciler.py tests/unit/test_eval_harness.py tests/unit/test_cli_discovery_rca_packet.py tests/unit/test_cli_write_lock_contract.py`
  -> `All checks passed`.
- `uv run mypy src/eidp/pdf/eval_harness.py src/eidp/db/session.py src/eidp/scraper/discovery_rca_packet.py src/eidp/scraper/firecrawl_discovery.py src/eidp/matcher/reconciler.py`
  -> `Success: no issues found in 5 source files`.
- `uv run pytest tests/unit/test_eval_harness.py tests/unit/test_cli_discovery_rca_packet.py tests/unit/test_cli_write_lock_contract.py -q`
  -> `54 passed in 1.94s`.
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v401.zip --skip-full-unit --json --output _temp/v401-non-windows-release-gates-stale-current-0e7e66d.json`
  -> `ok=false`; SHA256 sidecar matched
  `ff54f3a4c6a498ab9af89890e1ee614b31e57a87066277f1323f8f37d6f1bcf5`;
  `package_source_check` failed before downstream gates with packaged commit
  `2d9c9f690c6f955330ea49276ef1a87157ceb6cd`, source commit
  `0e7e66d25a9e77193962c4385e06e9744ab9f09f`, `source_dirty=false`,
  `stale=true`, and `results=[]`.
  This current rerun confirms v401 is not a current package; it is not evidence
  that the latest code-affecting source base `cd07c213` has been packaged.
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v401.zip --skip-full-unit --allow-stale-package --json --output _temp/v401-non-windows-release-gates-allow-stale-current-bb621daa.json`
  -> `ok=false`; SHA256 sidecar matched; `package_source_check` was allowed
  through with `stale=true`, but package verification then failed because v401
  lacks the current verifier's Stage 6 recovery, evidence Excel opt-in,
  residual cleanup symlink/junction safety, operator-coverage ship gate,
  audit-outbox archive matching, and default `18501 -> 8501` tunnel guidance
  tokens.
- `uv run pytest tests/unit/test_non_windows_release_gates.py::test_verify_package_source_commit_allow_stale_still_rejects_dirty_source tests/unit/test_non_windows_release_gates.py::test_verify_package_source_commit_can_allow_stale_zip_for_history tests/unit/test_non_windows_release_gates.py::test_verify_package_source_commit_rejects_dirty_tracked_source tests/unit/test_non_windows_release_gates.py::test_main_allows_stale_package_when_explicitly_requested -q`
  -> first run reproduced the bug with `1 failed, 3 passed`; after the fix,
  the same focused set returned `4 passed in 0.12s`.
- `uv run pytest tests/unit/test_non_windows_release_gates.py -q`
  -> `16 passed in 0.07s`.
- `uv run ruff check scripts/run_non_windows_release_gates.py tests/unit/test_non_windows_release_gates.py`
  -> `All checks passed`.
- `uv run mypy scripts/run_non_windows_release_gates.py`
  -> `Success: no issues found in 1 source file`.
- `uv run pytest tests/unit/test_windows_install_validator.py::test_validate_after_weekly_release_gate_rejects_lock_busy_even_if_payload_says_pass -q`
  -> first run reproduced the bug with `1 failed`; after the fix, the focused
  weekly ship-gate set returned `4 passed in 0.13s`.
- `uv run pytest tests/unit/test_windows_install_validator.py -q`
  -> `46 passed in 1.43s`.
- `uv run ruff check scripts/validate_windows_install.py tests/unit/test_windows_install_validator.py`
  -> `All checks passed`.
- `uv run mypy scripts/validate_windows_install.py`
  -> `Success: no issues found in 1 source file`.
- `uv run pytest tests/unit/test_windows_install_validator.py::test_validate_after_bootstrap_release_gate_rejects_progress_count_mismatch_even_when_sqlite_passes -q`
  -> first run reproduced the bug with `1 failed`; after the fix, the focused
  bootstrap ship-gate set returned `4 passed in 0.09s`.
- `uv run pytest tests/unit/test_windows_install_validator.py -q`
  -> `47 passed in 0.74s`.
- `uv run ruff check scripts/validate_windows_install.py tests/unit/test_windows_install_validator.py`
  -> `All checks passed`.
- `uv run mypy scripts/validate_windows_install.py`
  -> `Success: no issues found in 1 source file`.
- `uv run mypy src/eidp/db/audit.py src/eidp/db/audit_outbox.py src/eidp/db/current_helpers.py src/eidp/db/locking.py src/eidp/pipeline/manual_entry.py src/eidp/pipeline/ingest.py src/eidp/pipeline/ingest_evidence.py src/eidp/review/_pages/audit_log.py src/eidp/review/_pages/pdf_manual_entry.py`
  -> `Success: no issues found in 9 source files`.
- `uv run ruff check src/eidp/db/audit.py src/eidp/db/audit_outbox.py src/eidp/db/current_helpers.py src/eidp/db/locking.py src/eidp/pipeline/manual_entry.py src/eidp/pipeline/ingest.py src/eidp/pipeline/ingest_evidence.py src/eidp/review/_pages/audit_log.py src/eidp/review/_pages/pdf_manual_entry.py tests/unit/conftest.py tests/unit/test_manual_entry_contract.py tests/unit/test_review_pdf_manual_entry.py tests/unit/test_review_pdf_manual_entry_confidence.py tests/unit/test_review_audit_log.py tests/unit/test_review_audit_log_dashboard.py tests/unit/test_audit_outbox.py tests/unit/test_locking.py tests/unit/test_ingest_confidence_gating.py tests/unit/test_normal_ingest_appendonly.py tests/unit/test_ingest_evidence.py tests/unit/test_cli_ingest.py`
  -> `All checks passed`.
- `uv run pytest tests/unit/test_manual_entry_contract.py tests/unit/test_review_pdf_manual_entry.py tests/unit/test_review_pdf_manual_entry_confidence.py tests/unit/test_review_audit_log.py tests/unit/test_review_audit_log_dashboard.py tests/unit/test_audit_outbox.py tests/unit/test_locking.py tests/unit/test_ingest_confidence_gating.py tests/unit/test_normal_ingest_appendonly.py tests/unit/test_ingest_evidence.py tests/unit/test_cli_ingest.py -q`
  -> `143 passed, 5 warnings in 11.15s`.
- `uv run ruff check tests/unit/conftest.py tests/unit/test_locking.py`
  -> `All checks passed`.
- `uv run pytest tests/unit/test_review_pdf_manual_entry.py tests/unit/test_locking.py -q`
  -> `48 passed, 5 warnings in 7.77s`; confirms the PDF manual-entry AppTest
  no longer leaks a fake `__main__` module into subsequent multiprocessing
  spawn-based lock tests.
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
- `uv run pytest tests/unit/test_audit_outbox.py -q`
  -> `14 passed`.
- `uv run pytest tests/unit/test_extraction_confidence.py tests/unit/test_ingest_confidence_gating.py::test_env_override_promotes_borderline_row_to_current tests/unit/test_excel_exporter.py::test_excel_exporter_confidence_thresholds_follow_central_env -q`
  -> `59 passed`.
- `uv run pytest tests/unit/test_discovery_gold_set_seed.py::test_seed_discovery_gold_sites_rejects_unsafe_site_url_before_writing tests/unit/test_discovery_gold_set_seed.py::test_seed_discovery_gold_sites_fails_fast_on_semantically_invalid_entry tests/unit/test_discovery_gold_set_seed.py::test_seed_discovery_gold_sites_checks_normalized_site_url -q`
  -> `3 passed`.
- `uv run pytest tests/unit/test_review_pdf_manual_entry.py::test_manual_queue_summary_and_table_explain_next_actions tests/unit/test_review_pdf_manual_entry.py::test_discovery_trace_summary_explains_pdf_route_to_operator tests/unit/test_review_pdf_manual_entry.py::test_fiscal_year_evidence_summary_distinguishes_pdf_text_and_link_hints -q`
  -> `3 passed`.
- `uv run pytest tests/unit/test_pdf_discovery.py::test_pre_download_does_not_treat_romanized_renewal_form_alone_as_target tests/unit/test_pdf_discovery.py::test_pre_download_does_not_treat_english_renewal_form_alone_as_target tests/unit/test_pdf_discovery.py::test_pre_download_does_not_treat_english_renewal_form_with_english_support_hint_as_target -q`
  -> `3 passed`.
- `uv run ruff check src/eidp/extraction_confidence.py tests/unit/test_extraction_confidence.py src/eidp/db/audit_outbox.py tests/unit/test_audit_outbox.py`
  -> `All checks passed`.
- `uv run mypy src/eidp/extraction_confidence.py src/eidp/db/audit_outbox.py`
  -> `Success: no issues found in 2 source files`.

Known non-goal-wide lint boundary:

- `uv run ruff check .` currently scans untracked `_temp/` extractions and
  historical one-off scripts; it reported existing lint debt and is not a
  reliable current-source release gate.
- `git ls-files -z '*.py' | xargs -0 uv run ruff check` also currently reports
  historical lint debt outside `src/`, mainly Alembic revision style, old
  one-off analysis scripts, and Japanese test function names. Tracked source
  package linting is clean via `uv run ruff check src`; goal-relevant changed
  surfaces above were checked with targeted Ruff/Mypy/tests.
- `uv run mypy src` is now a usable source-wide gate for the tracked source
  tree and passes across 83 source files. This is still Mac-side evidence only;
  it does not prove the Windows operator-PC Stage 6 browser write-cycle or the
  rolling FY yield gate.

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

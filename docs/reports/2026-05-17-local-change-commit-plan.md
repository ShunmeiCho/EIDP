# Local Change Commit Plan - EIDP v466 Candidate Source

Date: 2026-05-17
Branch: `sprint8-handoff-finalize`
Status: planning only; no commit, push, release, or Windows active-lane switch

## Purpose

The current working tree contains release-critical CI/package fixes, runtime
operator improvements, diagnostic additions, and evidence updates. This plan
keeps the review surface small enough that a later commit/push step can turn
GitHub CI green without mixing unrelated proof/docs changes into one opaque
change.

## Recommended Order

| Commit | Scope | Files | Verification |
| --- | --- | --- | --- |
| 1 | CI unblock and workflow contract | `.github/workflows/ci.yml`, `pyproject.toml`, `uv.lock`, `tests/unit/test_ci_workflow_contract.py` | `uv lock --check`; `uv run python -m pip --version`; `uv run pytest tests/unit/test_ci_workflow_contract.py -q`; `uv run python scripts/build_windows_zip.py --allow-dirty --out-zip dist/eidp-windows-ci-diagnostic.zip`; CI Ruff/mypy/Bandit allowlist commands after push |
| 2 | Windows package and receiver verifier hardening | `scripts/build_windows_zip.py`, `scripts/verify_windows_distribution.py`, `tests/unit/test_windows_packaging_spike.py`, `tests/unit/test_windows_distribution_verifier.py` | `uv run pytest tests/unit/test_windows_packaging_spike.py -k "collect_zip_members_includes_alembic_and_weekly_runner" -q`; `uv run pytest tests/unit/test_windows_distribution_verifier.py -k "historical_runbooks or local_user_path_in_packaged_operator_docs" -q`; `uv run ruff check scripts/verify_windows_distribution.py tests/unit/test_windows_distribution_verifier.py tests/unit/test_windows_packaging_spike.py`; `uv run mypy scripts/verify_windows_distribution.py` |
| 3 | Target-FY override correctness | `scripts/bootstrap_pdf_pipeline.py`, `src/eidp/cli.py`, `tests/unit/test_bootstrap_pdf_pipeline.py`, `tests/unit/test_cli_ingest.py`, relevant ingest/confidence tests | `uv run pytest tests/unit/test_ingest_confidence_gating.py tests/unit/test_cli_ingest.py tests/unit/test_bootstrap_pdf_pipeline.py -q` |
| 4 | Shared-origin discovery performance guard | `src/eidp/scraper/pdf_discovery.py`, `tests/unit/test_pdf_discovery.py` | `uv run pytest tests/unit/test_pdf_discovery.py -k "reuses_rejected_candidate or shared_origin_cache_scales or shared_origin_robots_sitemap or repeated_http_gets" -q` |
| 5 | Weekly progress and duplicate-launch guard | `scripts/run_weekly_target_year_discovery.py`, `src/eidp/review/_pages/school_year_tasks.py`, `tests/unit/test_run_weekly_target_year_discovery.py`, `tests/unit/test_review_school_year_tasks.py` | `uv run pytest tests/unit/test_review_school_year_tasks.py tests/unit/test_run_weekly_target_year_discovery.py -q`; `uv run ruff check src/eidp/review/_pages/school_year_tasks.py tests/unit/test_review_school_year_tasks.py`; `uv run mypy src/eidp/review/_pages/school_year_tasks.py` |
| 6 | Local bug-report bundle UI | `scripts/collect_bug_report.py`, `scripts/collect_bug_report.bat`, `src/eidp/bug_signals/*`, `src/eidp/review/_pages/bug_report.py`, `src/eidp/review/app.py`, `tests/unit/test_bug_signals.py`, `tests/unit/test_review_bug_report.py` | `uv run pytest tests/unit/test_bug_signals.py tests/unit/test_review_bug_report.py -q`; CLI end-to-end scrub smoke with `C:/Users/...`, email, and school-name tokens must return `leak_count=0`; `uv run ruff check src/eidp/bug_signals tests/unit/test_bug_signals.py tests/unit/test_review_bug_report.py`; `uv run mypy src/eidp/bug_signals src/eidp/review/_pages/bug_report.py scripts/collect_bug_report.py` |
| 7 | Ship-gate publication-lag exception contract | `scripts/ship_gate_contract.py`, `scripts/verify_stage6_return.py`, `scripts/build_mature_year_acquisition_proof.py`, `tests/unit/test_ship_gate_contract.py`, `tests/unit/test_stage6_return_verifier.py`, `tests/unit/test_mature_year_acquisition_proof.py`, `docs/runbooks/eidp-operator-e2e-template.md` | `uv run pytest tests/unit/test_mature_year_acquisition_proof.py tests/unit/test_stage6_return_verifier.py tests/unit/test_ship_gate_contract.py -q`; reject Excel-only proof and denominator `<1000` small-sample proof as publication-lag mature-year acquisition proof; generate proof JSON from mature-year weekly `last_run.json` |
| 8 | Portability/privacy guard docs and tests | `tests/unit/test_portability_contract.py`, `docs/runbooks/eidp-windows.md`, `docs/runbooks/eidp-operator-e2e-template.md`, `docs/runbooks/eidp-v465-active-promotion.md` | `uv run pytest tests/unit/test_ci_workflow_contract.py tests/unit/test_portability_contract.py -q`; `git diff --check` |
| 9 | Evidence reports and release status | `docs/reports/2026-05-17-active-goal-completion-audit.md`, `docs/reports/2026-05-17-local-change-readiness.md`, `docs/reports/2026-05-17-local-change-commit-plan.md`, `docs/reports/2026-05-17-objective-completion-audit.md`, `docs/reports/2026-05-17-v466-diagnostic-package.md`, `docs/reports/2026-05-17-current-source-retroactive-matrix.md`, `docs/reports/2026-05-17-mature-year-acquisition-proof-audit.md`, `docs/reports/current-release-status.md` | `git diff --check`; no release approval implied |
| 10 | Ancillary script portability updates | `scripts/analyze_reference_urls.py`, `scripts/analyze_target_institutions.py`, `scripts/generate_briefing_pdf.py`, `scripts/generate_report.py`, `scripts/investigate_unmatched.py`, `scripts/match_schools.py`, `scripts/md_to_pdf.py`, `scripts/stage6_recovery_check.py`, `tests/unit/test_prune_release_artifacts.py`, related recovery tests | `uv run pytest tests/unit/test_prune_release_artifacts.py -q`; `uv run ruff check` on touched scripts; targeted tests already listed in readiness before full CI |

## Overlap Notes

Some files span multiple concerns and should be split with patch selection if
the final commit history needs strict topical boundaries:

- `scripts/verify_windows_distribution.py`: package contract, publication-lag
  tokens, local-user path rejection, and historical-runbook rejection.
- `tests/unit/test_windows_distribution_verifier.py`: verifier contract and
  privacy guard tests.
- `docs/runbooks/eidp-operator-e2e-template.md`: release-exception fields and
  portability placeholders.
- `docs/reports/2026-05-17-active-goal-completion-audit.md`: evidence for all
  groups; keep it near the final evidence commit if patch-splitting is costly.

## Coverage Check

A local status-to-plan coverage check mapped the current `53` dirty entries to
the file groups above with `missing_count=0`. This is a coarse path-pattern
check, not a substitute for reviewing individual hunks before committing.

## Untracked Files To Include

`git ls-files --others --exclude-standard` currently reports these untracked
candidate files. They must be added deliberately if the corresponding commit
group is approved:

```text
docs/reports/2026-05-17-current-source-retroactive-matrix.md
docs/reports/2026-05-17-local-change-commit-plan.md
docs/reports/2026-05-17-local-change-readiness.md
docs/reports/2026-05-17-mature-year-acquisition-proof-audit.md
docs/reports/2026-05-17-objective-completion-audit.md
docs/reports/2026-05-17-v466-diagnostic-package.md
docs/runbooks/eidp-v465-active-promotion.md
scripts/build_mature_year_acquisition_proof.py
scripts/collect_bug_report.bat
scripts/collect_bug_report.py
src/eidp/bug_signals/__init__.py
src/eidp/bug_signals/bundle.py
src/eidp/bug_signals/detector.py
src/eidp/review/_pages/bug_report.py
tests/unit/test_bug_signals.py
tests/unit/test_mature_year_acquisition_proof.py
tests/unit/test_portability_contract.py
tests/unit/test_review_bug_report.py
```

## Recommended Push Gate

After the local commits are prepared and before asking owner/operator to use a
new package, run:

```bash
uv run pytest --cov=src/eidp --cov-report=term --cov-fail-under=80
uv run ruff check src scripts/build_windows_zip.py scripts/validate_windows_install.py scripts/verify_windows_distribution.py scripts/run_non_windows_release_gates.py scripts/run_retroactive_excel_matrix.py scripts/build_mature_year_acquisition_proof.py scripts/bootstrap_pdf_pipeline.py scripts/collect_stage6_evidence.py scripts/collect_bug_report.py scripts/verify_stage6_evidence.py scripts/verify_stage6_return.py scripts/stage6_recovery_check.py scripts/stage6_residual_cleanup.py scripts/ship_gate_contract.py tests/unit/test_current_read_paths.py tests/unit/test_db_session.py tests/unit/test_fiscal_year_evidence.py tests/unit/test_package_init.py tests/unit/test_retroactive_excel_matrix.py tests/unit/test_mature_year_acquisition_proof.py tests/unit/test_windows_install_validator.py tests/unit/test_non_windows_release_gates.py tests/unit/test_bootstrap_pdf_pipeline.py tests/unit/test_bug_signals.py tests/unit/test_review_bug_report.py tests/unit/test_stage6_evidence_bundle.py tests/unit/test_stage6_return_verifier.py tests/unit/test_ship_gate_contract.py tests/unit/test_portability_contract.py tests/unit/test_windows_distribution_verifier.py tests/unit/test_stage6_recovery_check.py tests/unit/test_stage6_residual_cleanup.py tests/unit/test_ci_workflow_contract.py
uv run mypy src scripts/run_retroactive_excel_matrix.py scripts/build_mature_year_acquisition_proof.py scripts/bootstrap_pdf_pipeline.py scripts/collect_bug_report.py scripts/verify_stage6_return.py scripts/ship_gate_contract.py
uv run --with bandit bandit -q --severity-level high -r src/eidp scripts/build_windows_zip.py scripts/validate_windows_install.py scripts/verify_windows_distribution.py scripts/run_non_windows_release_gates.py scripts/run_retroactive_excel_matrix.py scripts/build_mature_year_acquisition_proof.py scripts/bootstrap_pdf_pipeline.py scripts/collect_stage6_evidence.py scripts/collect_bug_report.py scripts/verify_stage6_evidence.py scripts/verify_stage6_return.py
gitleaks detect --redact --source . --config .gitleaks.toml
```

Then push and require a fresh GitHub CI run to pass. The old red CI runs on
commit `364f25a4fd95e1b7c85ace76e635c7a77954d583` do not validate the local
candidate source. PR #2 is currently `mergeStateStatus=UNSTABLE` with two
remote `Python quality gates` failures on that old head, so the push gate is
not satisfied until GitHub checks the new commit.

## Explicit Non-Goals

- Do not switch `EIDP Weekly Run` or any Windows Scheduled Task as part of
  these commits.
- Do not tag v1.0 or merge to main from local evidence alone.
- Do not call the active goal complete until owner/operator real-cycle evidence
  supplies measured KPI values, final Stage 6 bundle, audit/outbox delta, and
  sign-off.

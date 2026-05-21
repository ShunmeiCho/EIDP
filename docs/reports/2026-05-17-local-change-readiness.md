# Local Change Readiness - EIDP v466 Candidate Source

Date: 2026-05-17
Branch: `sprint8-handoff-finalize`
Status: local working tree only, not committed, not pushed

## Purpose

This report groups the current local changes so the next commit/review step can
separate release-critical fixes from evidence updates. It does not approve a
release, switch the Windows active lane, or mark the active goal complete.

## Remote CI Status

The latest checked GitHub CI failures on branch `sprint8-handoff-finalize`
were attached to remote commit `364f25a4fd95e1b7c85ace76e635c7a77954d583`, not
to the current local dirty working tree. Run `25976458918` passed the pytest
coverage gate (`1673 passed`, total coverage `80.65%`) and then failed in the
Windows ZIP build step because `.venv/bin/python3 -m pip download` could not
import `pip`.

The local candidate source fixes that CI failure by adding `pip>=24.0` to the
dev environment and preserving the CI packaging path that calls
`python -m pip download`. GitHub will continue to show the old red commit until
these local changes are committed and pushed, then a fresh CI run must be
checked before treating the branch as green.

A fresh local reproduction of the failed path now passes on the dirty candidate
source: `uv run python -m pip --version` reports `pip 26.1.1`, and
`uv run python scripts/build_windows_zip.py --allow-dirty --out-zip
dist/eidp-windows-ci-diagnostic.zip` successfully executed
`.venv/bin/python3 -m pip download`, produced `84` accepted wheels, and wrote
`dist/eidp-windows-ci-diagnostic.zip` with SHA256
`f0284e1999a30b4b5aec47d6b1a0fe889495ba90f2d18e90f7b077092183880d`. The
distribution verifier rejected that diagnostic ZIP only because
`BUILD_INFO.json git_dirty` is `true`, which is the expected protection for
uncommitted source packages.

Current PR state also confirms the distinction: PR #2
(`sprint8-handoff-finalize` -> `main`) still has remote head
`364f25a4fd95e1b7c85ace76e635c7a77954d583`, `mergeStateStatus=UNSTABLE`, and
two completed `Python quality gates` checks with `conclusion=FAILURE`. The
local verification below does not make the remote PR green until a new commit
is pushed and GitHub reruns CI.

## Historical Runbook Visibility

Some older source-tree handoff cards still contain historical tester paths such
as `C:\Users\<operator>\...`. They are not runtime inputs and they are not packaged
operator instructions. The current package boundary is guarded in three places:

- `build_windows_zip.py` only collects the current operator runbook, current
  E2E template, and top-level README.
- `tests/unit/test_windows_packaging_spike.py` asserts a fake
  `docs/runbooks/eidp-v460-real-cycle-card.md` with a `C:\Users\<operator>\...`
  path does not enter the ZIP manifest.
- `verify_windows_distribution.py` rejects any `docs/runbooks/eidp-v*`
  historical handoff card if one appears in a ZIP assembled outside the normal
  packaging path.

Therefore these historical paths are a public-source/documentation hygiene
issue if the repository is published, but not an operator/tester runtime bug in
the Windows ZIP.

The current release-status report has been sanitized separately:
`docs/reports/current-release-status.md` now uses `C:\Users\<operator>\...`
placeholders instead of the historical Windows username.
A follow-up candidate-file grep for local usernames now finds only boundary
documentation and deliberate test fixtures that prove historical paths do not
enter the operator ZIP. A matching grep for developer-user paths records a
`0`-offender scan, and a candidate-file grep for `/Users/` finds only
placeholders, regex/scrubber code, and test fixtures.

## Change Groups

| Group | Files | Reason |
| --- | --- | --- |
| CI unblock / hardening | `.github/workflows/ci.yml`, `pyproject.toml`, `uv.lock`, `tests/unit/test_ci_workflow_contract.py` | Fix the clean CI Windows ZIP path by ensuring `pip` is installed in the dev environment; move GitHub actions to `checkout@v6` / `setup-python@v6`; keep release-critical scripts/tests in CI quality gates. |
| Windows package / return verifier contract | `scripts/build_windows_zip.py`, `scripts/verify_windows_distribution.py`, `scripts/verify_stage6_return.py`, `scripts/build_mature_year_acquisition_proof.py`, `scripts/ship_gate_contract.py`, related verifier tests | Prevent dirty release-looking ZIP names, require publication-lag / mature-year contract tokens, support explicit publication-lag exception while still rejecting null KPI values, missing sign-off, Excel-only mature-year proof, and small-sample mature-year proof; generate machine-readable mature-year acquisition proof from weekly `last_run.json`. |
| Shared-origin discovery perf guard | `src/eidp/scraper/pdf_discovery.py`, `tests/unit/test_pdf_discovery.py` | Cap same-origin path-derived fallback probes after the first three schools and keep shared robots/sitemap/disclosure pages cached once per origin. |
| Weekly progress UI | `scripts/run_weekly_target_year_discovery.py`, `src/eidp/review/_pages/school_year_tasks.py`, related tests | Write and render `logs/weekly-rediscovery-*.json` so the operator can see weekly rediscovery progress instead of treating the batch as a black box; block duplicate launches while a recent running progress file is still credible. |
| Local bug-report bundle | `scripts/collect_bug_report.py`, `scripts/collect_bug_report.bat`, `src/eidp/bug_signals/*`, `src/eidp/review/_pages/bug_report.py`, related tests | Add local-only P0/P1 signal detection and sanitized bundle generation; scrub path/email/school/operator fields and secret assignments; no upload path. |
| Target-FY override correctness | `scripts/bootstrap_pdf_pipeline.py`, `src/eidp/cli.py`, related tests | Carry explicit `--target-fiscal-year` through bootstrap and direct ingestion paths for retroactive proof runs. |
| Promotion / evidence docs | `docs/runbooks/eidp-v465-active-promotion.md`, `docs/reports/2026-05-17-v466-diagnostic-package.md`, `docs/reports/2026-05-17-current-source-retroactive-matrix.md`, `docs/reports/2026-05-17-mature-year-acquisition-proof-audit.md`, `docs/reports/2026-05-17-active-goal-completion-audit.md`, `docs/reports/2026-05-17-objective-completion-audit.md`, `docs/reports/current-release-status.md` | Record the v460 deadlock, v465 promotion approval boundary, diagnostic v466 package proof, clean CI simulation, objective coverage audit, mature-year proof gap, and remaining owner-cycle blockers. |
| Commit split plan | `docs/reports/2026-05-17-local-change-commit-plan.md` | Keep the current large dirty working tree reviewable before any approved commit/push step. |
| Portability/privacy guard | `scripts/verify_windows_distribution.py`, `tests/unit/test_portability_contract.py`, `tests/unit/test_windows_packaging_spike.py`, `tests/unit/test_windows_distribution_verifier.py`, operator docs/runbook path updates | Prevent current-machine username/path leakage in runtime, tests, CI, packaged operator docs, and the v465 promotion runbook; keep historical handoff runbooks out of the operator ZIP and reject them in the receiver-side verifier. |

## Working Tree Size

`git status --porcelain` currently reports `53` dirty entries: `37` modified
tracked files and `16` untracked files/directories. `git diff --stat` currently
reports `37 files changed, 2426 insertions(+), 230 deletions(-)` for tracked
changes. This is why `docs/reports/2026-05-17-local-change-commit-plan.md`
exists before any approved commit/push step. A local status-to-plan coverage
check mapped all `53` dirty entries to that plan with `missing_count=0`.
`git ls-files --others --exclude-standard` expands the untracked side to `18`
candidate files, now listed explicitly in the commit plan.

## Secret Scan Boundary

A full-worktree `gitleaks detect --no-git --redact` scan reported `7` findings,
but all were outside the candidate commit surface: local `.env`, downloaded
prefecture artifact HTML under `data/prefecture-aggregators/artifacts/`, and
`.venv` dependency files. `git check-ignore -v` confirms those paths are
ignored, and `git ls-files` showed none of those files are tracked. The `.env`
finding should still be treated as a real local secret and rotated if it was
ever shared outside this workstation.

The repository-facing scan passed:

```bash
gitleaks detect --redact --source . --config .gitleaks.toml
```

It scanned `1364` commits, about `15.77 MB`, and reported `no leaks found`.
This was rerun after adding fake secret-assignment scrub fixtures such as
`OPENAI_API_KEY=...` and `GITHUB_TOKEN:...`; the scanner still reported no
leaks. No secret values were printed into this report.

## Fresh Verification

| Command | Result |
| --- | --- |
| `uv run pytest --cov=src/eidp --cov-report=term --cov-fail-under=80` | `1750 passed`, total coverage `80.87%` |
| CI Ruff allowlist command after current-source refresh | pass |
| CI mypy command after current-source refresh | pass, `Success: no issues found in 93 source files` |
| High-severity Bandit scan after current-source refresh | pass, exit `0` with no findings printed |
| `gitleaks detect --redact --source . --config .gitleaks.toml` | pass, scanned `1364` commits and reported `no leaks found` |
| `uv run python -m pip --version` | pass, `pip 26.1.1` from the project `.venv` |
| `git ls-remote --tags https://github.com/actions/checkout.git refs/tags/v6` | tag exists: `de0fac2e4500dabe0009e67214ff5f5447ce83dd` |
| `git ls-remote --tags https://github.com/actions/setup-python.git refs/tags/v6` | tag exists: `a309ff8b426b58ec0e2a45f0f869d46889d02405` |
| `uv lock --check` | pass, `Resolved 151 packages in 0.86ms` |
| `uv run pytest tests/unit/test_ci_workflow_contract.py tests/unit/test_portability_contract.py -q` | `9 passed` |
| `uv run pytest tests/unit/test_ci_workflow_contract.py tests/unit/test_portability_contract.py tests/unit/test_windows_distribution_verifier.py -q` | `133 passed` |
| `uv run python scripts/build_windows_zip.py --allow-dirty --out-zip dist/eidp-windows-ci-diagnostic.zip` | pass, covered the CI `python -m pip download` path; wrote SHA256 `f0284e1999a30b4b5aec47d6b1a0fe889495ba90f2d18e90f7b077092183880d` |
| `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-ci-diagnostic.zip --json` | expected fail only: `BUILD_INFO.json git_dirty must be false`; verifier metadata showed `wheel_count=84`, `entry_count=3099`, `project_wheel_count=1` |
| `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v465.zip --json` | expected stale-package fail: v465 `BUILD_INFO.git_dirty=false`, but package misses current bug-report files, publication-lag/ship-gate tokens, weekly progress tokens, target-FY override tokens, and packaged-doc local-user path guards |
| `uv run python scripts/verify_stage6_return.py ... --release-exception-reason publication_lag --mature-year-proof-json logs/release-gate-current-source-retroactive-matrix-20260517.json --json` after proof-basis tightening | expected fail, `rc=1`; rejected Excel business-diff proof because its basis is `current_source_retroactive_excel_business_value_diff` and its cases do not contain mature-year target-PDF/operator-reviewable KPI metrics |
| Negative `verify_stage6_return.py` publication-lag CLI probe with null KPI / `ship_gate_status=not_measured` | expected fail, `rc=1`; rejected unmeasured `target_pdf_auto_yield_pct`, `operator_reviewable_yield_pct`, and `ship_gate_status` |
| `uv run pytest tests/unit/test_windows_packaging_spike.py -k "collect_zip_members_includes_alembic_and_weekly_runner" -q` | `1 passed`, `85 deselected` |
| `uv run pytest tests/unit/test_windows_distribution_verifier.py -k "local_user_path or eidp_operator or historical_runbooks" -q` | `3 passed`, `121 deselected` |
| `uv run pytest tests/unit/test_windows_distribution_verifier.py -q` | `124 passed` |
| `uv run pytest tests/unit/test_ingest_confidence_gating.py tests/unit/test_cli_ingest.py tests/unit/test_bootstrap_pdf_pipeline.py -q` | `63 passed` |
| `uv run pytest tests/unit/test_review_school_year_tasks.py -q` | `62 passed` |
| `uv run pytest tests/unit/test_bug_signals.py tests/unit/test_review_bug_report.py -q` | `13 passed` |
| `scripts/collect_bug_report.py` end-to-end scrub smoke with `C:/Users/forward/...`, email, and school name in log/note | generated 6-member local ZIP; `leak_count=0` |
| `uv run pytest tests/unit/test_prune_release_artifacts.py -q` | `4 passed` |
| `uv run ruff check src/eidp/review/_pages/school_year_tasks.py tests/unit/test_review_school_year_tasks.py` | pass |
| `uv run mypy src/eidp/review/_pages/school_year_tasks.py` | pass |
| `uv run ruff check src/eidp/bug_signals tests/unit/test_bug_signals.py tests/unit/test_review_bug_report.py` | pass |
| `uv run mypy src/eidp/bug_signals src/eidp/review/_pages/bug_report.py scripts/collect_bug_report.py` | pass |
| `ruby -e 'require "yaml"; YAML.load_file(".github/workflows/ci.yml")'` after CI/action refresh | `workflow yaml ok` |
| `git diff --check` | pass |
| `scripts/verify_windows_distribution.py dist/eidp-windows-v466-diagnostic.zip` | expected fail only: `BUILD_INFO.json git_dirty must be false` |
| Diagnostic ZIP docs/runbooks members after historical-runbook guard | only `docs/runbooks/eidp-windows.md` and `docs/runbooks/eidp-operator-e2e-template.md` |
| Current-source clean CI simulation in `/tmp` after forward-slash Windows path scrub | `ok=true`, clean package SHA256 `cdcd9832e64d182b06287fa9ef42af43b99eb63b6574734759833d7d61521cf0`; temporary commit `54df409531d758adeef47d3edb6eb1cabbafaa21`; `git_dirty=false`; `wheel_count=84`; `entry_count=3096` |
| Current-source clean CI ZIP real-local-username scan | `1321` text members scanned, `real_local_username_offenders=0` |
| Current-source retroactive Excel matrix | FY2025/FY2024/FY2023 `ok=true`, zero missing rows, extra rows, or differing fields |
| `uv run pytest tests/unit/test_mature_year_acquisition_proof.py tests/unit/test_stage6_return_verifier.py tests/unit/test_ship_gate_contract.py -q` after proof-basis/denominator tightening | `21 passed`; includes proof-builder coverage, rejection of Excel-only proof, and rejection of mature-year proof with denominator below `1000` |
| Existing FY2025 bounded proof attempt: `build_mature_year_acquisition_proof.py --case 2025=logs/win-v454-stage6/last_run.json` | expected fail, `ok=false`; rejected `target_pdf_auto_yield_pct=40.0 < 60.0` and denominator `5 < 1000` |
| Copied URL-rich DB FY2025 dry-run | `target_missing_school_count=1625`, `dry_run=true`, correctly not proof |
| Copied URL-rich DB FY2025 limit-20 execution smoke | completed; `crawled=20`, `downloaded=7`, `processed=7`, `target_pdf_auto_yield_pct=25.0`, `operator_reviewable_yield_pct=65.0`, `discovery_rejections.jsonl=130` lines / `56 KB`; proof builder correctly rejected it because yield, denominator, and manual workload missed release thresholds |

## Not Release Complete

The final objective is still incomplete. Missing gates:

- Owner/operator real-cycle click-through on the approved active lane.
- Final `data\output\last_run.json` from that real cycle.
- Verifier-accepted Stage 6 evidence ZIP.
- Measured FY2026/R8 KPI values.
- Audit/outbox delta from the real cycle.
- Owner and operator sign-off.
- Explicit approval before any Windows Scheduled Task active-lane switch.

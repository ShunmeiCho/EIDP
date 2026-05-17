# Active Goal Completion Audit - EIDP Rolling Automation

Date: 2026-05-17
Branch: `sprint8-handoff-finalize`
Verdict: **NOT COMPLETE**

This audit checks the active long-term objective against current artifacts. It
does not approve release, tag, merge, or mark the goal complete.

## Objective Restated

EIDP must let one Windows operator process 1,700+ Japanese vocational schools
each rolling fiscal year by:

1. Seeding school URLs from all 47 prefecture official lists.
2. Finding and downloading true target-FY institution-requirement confirmation
   PDFs in strict mode, excluding stale-year fallback from success.
3. Extracting rows with pdfplumber, PyMuPDF, and Tesseract OCR, writing only
   confidence >= 0.70 records into append-only `DepartmentYearly` and
   `SupportRecipient` paths.
4. Exporting the Excel template.
5. Auditing all operator actions in `ManualActionLog` and JSONL outbox.
6. Running from a Windows ZIP via double-click setup and browser UI.

The stated shipping line is strict target-form auto-acquisition of 60-70% and
operator manual workload of 30% or lower. Full automation is not required.

## Prompt-To-Artifact Checklist

| Requirement | Current strongest evidence | Audit result |
| --- | --- | --- |
| 47 prefecture official lists seed school URLs | `docs/reports/current-release-status.md` records all 47 seed artifacts in prior bounded/proof lanes; v459 URL-only bootstrap imported `48` seed URLs, inferred `296` corporation URLs, and later v460 bootstrap reached `school_site_count=1838`, `schools_with_url=1805`, `schools_with_verified_url=1312` | Partially proven. Packaged/proof evidence exists, but v460 owner-cycle KPI still unmeasured |
| Strict target-FY PDF discovery excludes stale fallback from success | Unit/gold-set coverage plus v463/v464 package lane; v459 bounded R7 weekly downloaded `2` target PDFs from `5` target-missing schools; v460 FY2026 Plan A selected no crawlable schools and second URL-rich FY2026 probe stopped without `last_run`; fresh source check `uv run pytest tests/unit/test_pdf_discovery.py -k "reuses_rejected_candidate or shared_origin_cache_scales or shared_origin_robots_sitemap or repeated_http_gets" -q` returned `4 passed`, covering repeated stale-PDF rejection reuse, exact shared-root HTTP cache, same-origin robots/sitemap/disclosure-page cache, and a `150`-school shared-corporation stress regression that keeps shared robots/sitemap/disclosure GETs to one request each. For large same-origin groups, path-derived fallback probes are now capped per origin: the first `3` school sites keep those probes and later same-origin school sites skip them, with `shared_origin_derived_fallback_skipped=147` asserted in the stress regression | Mechanically guarded, but current FY2026/R8 production yield not proven |
| Extract confidence >= 0.70 rows only | OCR/package verifier contracts, confidence tests, v384 OCR copied-DB write proof, and historical v408/v384 append-only write proofs | Mechanically and sandbox-proven. No current strict R8 workload extraction proof |
| Append-only `DepartmentYearly` / `SupportRecipient` writes | Unit coverage plus v384/v407/v408 copied-DB manual-entry and fiscal-year override browser proofs | Sandbox-proven. No real v460 operator write cycle yet |
| Excel template export | v464 side-by-side FY2025/R7 browser Excel proof: `output/playwright/v464-r7-excel-smoke/summary.json ok=true`, workbook SHA256 `aff3dea57af4c6d96d8859e52748f8cecefb4e593f5da74b4f68646175937685`, sheet data rows `2418/10022/9719/9719`; v463 Mac retroactive matrix passed FY2025/FY2024/FY2023; current-source refresh `docs/reports/2026-05-17-current-source-retroactive-matrix.md` records FY2025/FY2024/FY2023 `ok=true` with zero missing rows, extra rows, and differing fields | R7 historical/browser export, multi-year package regression, and current-source algorithm regression proven. FY2026/R8 production workbook still pending |
| ManualActionLog audits every operator action | v459 URL-candidate reject plus outbox flush sandbox, v408/v384 broader manual-entry/fiscal-year override/audit outbox browser proofs | Sandbox-proven. Real v460 operator-cycle audit delta still missing |
| ZIP distribution, double-click setup, offline browser UI | Active v460 root `C:\Users\<operator>\EIDP-v460-01e4427`; v460 setup, validation, recovery, read-only UI nav, docs staging, and Plan A evidence bundle all recorded. v464 side-by-side setup/UI/R7 Excel/evidence guard/return verifier/disk health also recorded. A current-source clean CI-package simulation built `dist/eidp-windows-ci.zip` with `BUILD_INFO.git_dirty=false`, verifier `ok=true`, SHA256 `cdcd9832e64d182b06287fa9ef42af43b99eb63b6574734759833d7d61521cf0`, and a `1321`-text-member scan found `real_local_username_offenders=0`. Scheduled task still points to v460 | Windows setup and support lanes proven, and current package contents are username-portable in clean simulation. Real operator one-cycle still missing |
| Stage 6 evidence bundle verifier | v460 diagnostic bundle correctly rejected without `last_run`; v460 Plan A bundle verified `ok=true` after CLI weekly wrote `last_run`; v464 evidence guard correctly rejected setup/UI-only bundle; v464 return verifier rejected unfilled Plan A return; fresh source check `uv run pytest tests/unit/test_mature_year_acquisition_proof.py tests/unit/test_stage6_return_verifier.py tests/unit/test_ship_gate_contract.py -q` returned `21 passed`, including explicit `publication_lag` exception coverage that still rejects null KPI values, rejects `ship_gate_status` values inconsistent with `operator_reviewable_yield_pct`, rejects Excel-only proof as a mature-year publication-lag proof, rejects small-sample mature-year proof with denominator below `1000`, and generates mature-year acquisition proof JSON from weekly `last_run.json`; a direct CLI dry verification using `--release-exception-reason publication_lag` and `logs/release-gate-current-source-retroactive-matrix-20260517.json` now returns `rc=1` because that JSON is an Excel business-diff proof without mature-year target-PDF/operator-reviewable KPI metrics; full current-source CI coverage refresh `uv run pytest --cov=src/eidp --cov-report=term --cov-fail-under=80` returned `1750 passed` with total coverage `80.87%`; local bug-signal coverage includes the P1 `weekly_run_timeout_no_last_run` detector, stable aging-signal IDs, the primary `scan_bug_signals` API, and the `scan_p0_bug_signals` compatibility wrapper; manual weekly rediscovery progress is guarded through `--progress-file` / `--progress-log-path`, duplicate-launch protection, and UI progress rendering tests; local-user path portability is now mechanically guarded in tests and the package verifier | Verifier behavior proven and proof basis/production-scale denominator tightened. Final real-cycle return and real mature-year acquisition proof still missing |
| Strict target-form auto-acquisition 60-70% | v459 bounded R7 canary recorded `target_pdf_auto_yield_pct=40.0`; v460 Plan A recorded `target_pdf_auto_yield_pct=null`; second v460 URL-rich probe did not complete; current-source copied-DB FY2025 limit-20 execution completed but recorded only `target_pdf_auto_yield_pct=25.0` and proof-builder rejection | **Failing / unproven** |
| Operator workload <=30% | v459 bounded R7 canary recorded `operator_reviewable_yield_pct=100.0` but denominator was `5`; v460 Plan A diagnostics reported `estimated_manual_workload_rate=1.0`; current-source copied-DB FY2025 limit-20 execution recorded `operator_reviewable_yield_pct=65.0`, equivalent to manual workload `35.0`; no owner timing/sign-off | **Failing / unproven** |
| Owner/operator sign-off | `docs/runbooks/eidp-v460-real-cycle-card.md` and `docs/runbooks/eidp-operator-e2e-template.md` define the return path | Missing |

## Current Lane Boundaries

- Active owner-cycle lane remains v460:
  `C:\Users\<operator>\EIDP-v460-01e4427`.
- `EIDP Weekly Run` still executes
  `C:\Users\<operator>\EIDP-v460-01e4427\scripts\weekly_run.bat`.
- Latest non-active future candidate is v465:
  `dist/eidp-windows-v465.zip`, package/source commit
  `be32eb29212f71f72e6ab7e6d2a4f013ccb66e42`, SHA256
  `b8b6157261aae4986cab0050fa980265ddd6075660577157fe5a3360a04af041`.
  It is staged on Windows but is not the active owner-cycle lane.
- Previous side-by-side support package v464 remains the last broader
  Windows support lane with setup/UI/R7 Excel/evidence guard/return verifier
  proof:
  `dist/eidp-windows-v464.zip`, package commit
  `9a94226b243fba691936db46c1fc11ef7c9debbd`, SHA256
  `6b95d9f3e06d70a0018119b2665070cf3af735e01b61920f6492234e174bd378`.
- Latest operator companion docs ZIP is
  `dist/eidp-v460-operator-docs-20260517.zip`; verify the generated artifact
  with its sidecar. It is expanded on Windows under
  `C:\EIDP-staging\v460-operator-docs-20260517`.
- No tag, no main merge, and no release approval has been made from these
  support proofs.
- GitHub PR #2 is green at current head `844f093`: latest push CI run
  `25990552563` and latest pull-request CI run `25990553361` both completed
  with `conclusion=success` after Ruff, Bandit, mypy, full pytest coverage,
  Windows ZIP build, and non-Windows release gate.

## Fresh Return Verification

Read-only Windows refresh at 2026-05-17 09:01 JST still found no Streamlit
listener on 8501/8508/8509/18508/18509, and `data\output\last_run.json`
remained the 2026-05-16 Plan A stub with `target_pdf_auto_yield_pct=null`,
`operator_reviewable_yield_pct=null`, `ship_gate_status=not_measured`, and
`ship_readiness_rc=null`.

The current return verifier was rerun with:

```bash
uv run python scripts/verify_stage6_return.py \
  --e2e-template docs/runbooks/eidp-operator-e2e-template.md \
  --last-run logs/win-v460-plan-a/last_run.json \
  --evidence-verify-json logs/win-v460-plan-a/stage6-evidence-verify-20260516-184433.json \
  --target-fy 2026 \
  --json
```

It exited `1` with `ok=false` because final KPI values are not measured and
the E2E template KPI, release, owner sign-off, and operator sign-off rows are
still blank or placeholders.

A follow-up run with `--release-exception-reason publication_lag` and
`--mature-year-proof-json logs/release-gate-current-source-retroactive-matrix-20260517.json`
also exited `1`. The verifier now rejects that JSON as a ship-exception proof:
its basis is `current_source_retroactive_excel_business_value_diff`, and the
cases do not include mature-year `target_pdf_auto_yield_pct`,
`operator_reviewable_yield_pct`, or consistent `ship_gate_status` metrics. This
keeps the Excel regression matrix as Excel evidence only, not as target-PDF
acquisition proof.

## Deadlock / Non-Owner Blockers

The current state should not be treated as simple `HOLD waiting owner`. Four
blockers are not solved by owner presence alone:

- v460 has an active-lane performance deadlock risk: the URL-rich FY2026 weekly
  probe ran about 9h41m, wrote no new `last_run.json`, and repeatedly recrawled
  shared corporation-domain pages.
- v465 is the next active-lane candidate with the shared-corporation HTTP cache
  source fix, but it is still non-active and the Scheduled Task still points to
  v460.
- FY2026/R8 mid-May publication lag can make strict target-PDF yield and manual
  workload thresholds physically misleading even when the workflow is operating
  correctly.
- The release verifier must separate measured publication-lag misses from
  unmeasured evidence. The current source now allows only the explicit
  `publication_lag` exception path; null KPI values and `not_measured` still
  fail.

Current-source Excel proof was refreshed on 2026-05-17 and recorded in
`docs/reports/2026-05-17-current-source-retroactive-matrix.md`: FY2025/FY2024
/FY2023 each returned `ok=true`, and each business-value diff reported
`missing_rows=0`, `extra_rows=0`, and `differing_fields=0`. This is Excel
business-value evidence for the current source tree, not mature-year
target-PDF acquisition proof and not a v465 package freshness gate: the current
working tree has tracked source/docs changes, so
`dist/eidp-windows-v465.zip` should not be counted as a fresh release-package
matrix until those changes are committed/rebuilt or deliberately excluded.

The current distribution verifier also rejects `dist/eidp-windows-v465.zip`
under the updated contract: the ZIP SHA is valid and its `BUILD_INFO.json`
matches commit `be32eb29212f71f72e6ab7e6d2a4f013ccb66e42`, but it is missing
the source-side `release_exception_reason`, `SHIP_GATE_EXCEPTION_REASONS`,
`MATURE_YEAR_SHIP_GATE_METRIC_BASIS`, and `publication_lag` contract tokens.
Therefore v465 remains a perf/cache-fix candidate, not a current-contract
release-candidate package.

Current-source validation after these changes:
the exact CI coverage command
`uv run pytest --cov=src/eidp --cov-report=term --cov-fail-under=80` returned
`1750 passed, 5 warnings` with total coverage `80.87%`; the warnings were
import-time SWIG deprecation warnings. Focused package/verifier checks also
passed: direct `ingest-pdfs --target-fiscal-year` plus the distribution
verifier returned `117 passed`, the CI/workflow, packaging, and bootstrap slice
returned `121 passed`, the dedicated CI workflow contract test returned
`7 passed` after the GitHub Actions Node 24 action-version update, the
bug-report/UI/distribution slice returned
`137 passed`, the focused portability/runbook contract file returned
`2 passed`, the refreshed CI/portability/distribution verifier slice returned
`133 passed`,
the refreshed bug-signal API slice returned `25 passed`, the prune release
artifacts slice returned `4 passed`, the weekly progress slice returned
`83 passed`, and the broad push-gate ruff/mypy/Bandit/Gitleaks checks passed
for the current source tree. A CLI end-to-end bug-report scrub smoke generated
a 6-member local ZIP from a synthetic log/note containing `C:/Users/forward`,
email, and school name tokens with `leak_count=0`.
`tests/unit/test_bug_signals.py` covered local-only P0 detection, the P1
`weekly_run_timeout_no_last_run` detector, `scan_bug_signals` plus the
`scan_p0_bug_signals` compatibility wrapper, PII and secret-assignment
scrubbing, bundle generation, SQLite integrity checking, and ZIP manifest
validity.
`scripts/run_weekly_target_year_discovery.py` now supports `--progress-file`
and `--progress-log-path`, and the school-year task UI writes and renders
`logs/weekly-rediscovery-*.json` for manual weekly rediscovery.
`tests/unit/test_portability_contract.py` now scans runtime/test/CI files and
the two packaged operator docs for current-machine and optional
`EIDP_FORBIDDEN_LOCAL_USERS` tokens without hardcoding private usernames in
public source, and the CI workflow contract requires that test file to stay in
the Ruff allowlist. `scripts/verify_windows_distribution.py` now also rejects
real `C:\Users\<name>` and `/Users/<name>` path forms inside the packaged
runbook and E2E template while allowing documented placeholders.
The latest focused refresh of the full distribution verifier returned
`124 passed`; the CI/portability/distribution verifier slice returned
`133 passed`. Ruff and mypy also passed for the touched verifier and
portability files.
The updated workflow action tags were checked against GitHub directly:
`actions/checkout@v6` resolved to
`de0fac2e4500dabe0009e67214ff5f5447ce83dd`, and
`actions/setup-python@v6` resolved to
`a309ff8b426b58ec0e2a45f0f869d46889d02405`.
`uv sync --locked --extra dev --extra scraper-basic --extra pdf` now installs
`pip==26.1.1`, so the CI Windows ZIP path can satisfy
`python -m pip download`.
The exact CI failure path was also rerun locally on the dirty candidate source:
`uv run python scripts/build_windows_zip.py --allow-dirty --out-zip
dist/eidp-windows-ci-diagnostic.zip` executed
`.venv/bin/python3 -m pip download`, produced `84` accepted wheels, and wrote
SHA256 `f0284e1999a30b4b5aec47d6b1a0fe889495ba90f2d18e90f7b077092183880d`.
`verify_windows_distribution.py dist/eidp-windows-ci-diagnostic.zip --json`
rejected that diagnostic package only for
`BUILD_INFO.json git_dirty must be false`, confirming the previous remote CI
failure is fixed in local source while release-grade packaging still requires a
clean committed checkout.

Diagnostic successor packaging was tested in
`docs/reports/2026-05-17-v466-diagnostic-package.md`. The current source tree
built `dist/eidp-windows-v466-diagnostic.zip` with SHA256
`6cfc475c9723c4712fd513c09ab615edbd7b1bb68ef357e6f0c44743c2820126`, runtime
and 84 accepted wheels included. It was built without `--skip-download`, and
the output showed the same `.venv/bin/python3 -m pip download` path used by CI.
`verify_windows_distribution.py` reported only `BUILD_INFO.json git_dirty must
be false`, so the current package contents meet the updated contract, including
bootstrap `--target-fiscal-year` propagation, direct
`ingest-pdfs --target-fiscal-year`, and local bug-report bundle files, but the
package is diagnostic-only until rebuilt from a clean source snapshot.
The older `dist/eidp-windows-v465.zip` still has clean `BUILD_INFO` for commit
`be32eb29212f71f72e6ab7e6d2a4f013ccb66e42`, but the current verifier rejects it
as stale: it lacks the new bug-report bundle files, publication-lag/ship-gate
tokens, weekly progress tokens, target-FY override tokens, and packaged-doc
local-user path guards.
To verify that the dirty flag is not hiding a second CI failure, the current
working tree was copied into a temporary clean git checkout and run through the
CI package path. That simulation built `dist/eidp-windows-ci.zip` without
`--allow-dirty`, verified `BUILD_INFO.git_dirty=false`, and
`run_non_windows_release_gates.py --skip-full-unit` returned `ok=true` with
package SHA256
`cdcd9832e64d182b06287fa9ef42af43b99eb63b6574734759833d7d61521cf0` from
temporary commit `54df409531d758adeef47d3edb6eb1cabbafaa21`. After adding the
historical-runbook receiver guard, bug-report secret-assignment scrub, and
forward-slash Windows user-path scrub, that current-source clean CI simulation
ZIP verified `ok=true`, had
`BUILD_INFO.git_dirty=false`, and its packaged operator docs remained free of
real local username/path tokens.
The same clean ZIP was scanned for local username leakage across `1321` text
members: tester-specific Windows and macOS username/path tokens each had `0`
offenders. Generic examples such as `C:\Users\<user>` and Python runtime
template paths remained allowed placeholders, not install-specific operator
paths. Real-looking Windows user paths are now treated as local-user paths in
packaged operator docs and are covered by verifier regression tests; they remain
acceptable only in non-packaged recovery parser fixtures/examples.
Older source-tree handoff cards may still contain historical tester paths, but
they are classified as source documentation/evidence hygiene, not operator ZIP
runtime inputs. The package collector ships only the current operator runbook
and E2E template, the packaging test fixture proves a historical
`docs/runbooks/eidp-v*` runbook does not enter the manifest, and the
distribution verifier rejects any `docs/runbooks/eidp-v*` historical handoff
card in a received ZIP. The current release-status report was also sanitized to
use `C:\Users\<operator>\...` placeholders instead of historical Windows
usernames.
`tests/unit/test_windows_packaging_spike.py` also now covers the manifest
boundary directly: a fake historical runbook with a local Windows path is
present in the source fixture, and the test asserts no
`docs/runbooks/eidp-v*` historical handoff card enters the operator ZIP.
`scripts/verify_windows_distribution.py` now rejects the same historical
runbook pattern if it appears in a ZIP assembled outside the standard packaging
path; the focused verifier slice returned `3 passed` for historical-runbook and
local-user-path rejection. The existing v466 diagnostic ZIP was rechecked after
adding that guard: its `docs/runbooks/` members are only the two current
operator docs, and the verifier still reports only the expected diagnostic
failure `BUILD_INFO.json git_dirty must be false`.
The full distribution verifier unit file also passed after the guard change:
`uv run pytest tests/unit/test_windows_distribution_verifier.py -q` returned
`124 passed`.
The packaging script also rejects release-like dirty ZIP names up front;
`--allow-dirty --out-zip dist/eidp-windows-v466.zip` now fails before wheel
build or ZIP assembly.

Mature-year acquisition proof status is now recorded in
`docs/reports/2026-05-17-mature-year-acquisition-proof-audit.md`. Existing
FY2025 bounded `last_run.json` artifacts were rejected because their denominator
was only `5` and strict target auto yield topped out at `40.0%`. A copied
URL-rich v460 SQLite dry-run for FY2025 found `target_missing_school_count=1625`
but is not proof because `dry_run=true`. A current-source FY2025 `--limit 20`
execution smoke completed on the copied DB with `crawled=20`, `downloaded=7`,
`processed=7`, `target_pdf_auto_yield_pct=25.0`, and
`operator_reviewable_yield_pct=65.0`; the proof builder correctly rejected it
because the strict target-yield, denominator, and manual-workload thresholds were
not met.

The earlier local dirty tree has been split into focused commits through
current head `844f093`. Fresh local and remote validation now covers those
commits: local `uv run pytest --cov=src/eidp --cov-report=term
--cov-fail-under=80` returned `1750 passed` with total coverage `80.87%`, and
GitHub push/PR CI completed successfully at runs `25990552563` and
`25990553361`. The remaining local dirty state is limited to report drafts:
two modified status reports and five untracked `docs/reports/2026-05-17-*.md`
files. Those drafts are not release artifacts and do not change the completion
verdict. The active thread goal remains `active`; this audit does not call
`update_goal`.

The safe next split is now: refresh/commit the status reports, build a clean
successor Windows package from the green head if needed, prepare/promote the
fixed lane only after explicit approval, prove algorithm behavior on mature-year
data, then run the owner/operator real cycle on the approved active lane.

## Missing Gates

The goal is not achieved because the following remain missing:

- Owner/operator real-cycle click-through on the approved active lane.
- Final `data\output\last_run.json` from the real cycle.
- Verifier-accepted final Stage 6 evidence ZIP from the real cycle.
- Filled `docs/runbooks/eidp-operator-e2e-template.md` return rows.
- Measured `target_pdf_auto_yield_pct`.
- Measured `operator_reviewable_yield_pct` and workload <=30% evidence.
- Audit/outbox delta from the real operator cycle.
- Owner and operator sign-off.

## Next Concrete Gate

The next release-relevant work is no longer a blind v460 owner-cycle retry.
Before asking owner/operator to run an unbounded weekly cycle, use
`docs/runbooks/eidp-v465-active-promotion.md` to prepare the v465 promotion
boundary, rerun mature-year proof if needed, and require explicit approval
before switching the Windows Scheduled Task. Local side-by-side support work can
continue, but it must not be counted as completion unless it produces the
missing measured KPI, evidence ZIP, audit/outbox, and sign-off artifacts above.

# v466 Diagnostic Package Check

Date: 2026-05-17
Branch: `sprint8-handoff-finalize`
Package: `dist/eidp-windows-v466-diagnostic.zip`
SHA256: `6cfc475c9723c4712fd513c09ab615edbd7b1bb68ef357e6f0c44743c2820126`
Status: diagnostic only, not a release package

## CI wheel-download failure fix

GitHub CI was failing at the Windows ZIP step because the workflow runs:

```bash
uv run python scripts/build_windows_zip.py --out-zip dist/eidp-windows-ci.zip
```

That path does not pass `--skip-download`, so
`scripts/build_windows_zip.py` shells out to:

```text
.venv/bin/python3 -m pip download ...
```

The `uv` virtualenv did not include `pip`, so CI failed with
`No module named pip`. The immediate fix is to include `pip>=24.0` in the
`dev` extra that CI already installs, and to lock that dependency in
`uv.lock`.

Validation:

```text
uv sync --locked --extra dev --extra scraper-basic --extra pdf
uv run python -m pip --version
uv run pytest --cov=src/eidp --cov-report=term --cov-fail-under=80
```

Result:

```text
pip 26.1.1 from .venv/lib/python3.12/site-packages/pip (python 3.12)
1724 passed, 5 warnings; total coverage 80.84%
```

The exact CI Ruff allowlist command, high-severity Bandit scan, and mypy
command also passed locally after the package-verifier local-user guard and
bug-signal API naming updates. The CI workflow now uses
`actions/checkout@v6` and `actions/setup-python@v6`; the workflow contract test
returned `7 passed`, and Ruby YAML parsing returned `workflow yaml ok`.

## Build

Command:

```bash
uv run python scripts/build_windows_zip.py \
  --allow-dirty \
  --out-zip dist/eidp-windows-v466-diagnostic.zip
```

This intentionally mirrors the CI download path and does not use
`--skip-download`. The build output showed the expected pip invocation:

```text
$ .venv/bin/python3 -m pip download -r requirements-windows.txt --dest dist/wheelhouse --platform win_amd64 --python-version 3.12 --implementation cp --abi cp312 --only-binary :all:
OK: wheelhouse contains 84 accepted wheels
OK: wrote dist/eidp-windows-v466-diagnostic.zip (202.1 MB)
OK: wrote checksum sidecar dist/eidp-windows-v466-diagnostic.zip.sha256
```

The build was intentionally run with `--allow-dirty` because the current source
tree contains uncommitted tracked changes. Therefore the ZIP records
`git_dirty=true` and cannot be a release artifact.

## CI diagnostic rerun

After confirming the remote red GitHub checks were still attached to old commit
`364f25a4fd95e1b7c85ace76e635c7a77954d583`, the same no-`--skip-download`
build path was rerun with a CI-shaped diagnostic filename:

```bash
uv run python scripts/build_windows_zip.py \
  --allow-dirty \
  --out-zip dist/eidp-windows-ci-diagnostic.zip
```

Result:

```text
$ .venv/bin/python3 -m pip download -r requirements-windows.txt --dest dist/wheelhouse --platform win_amd64 --python-version 3.12 --implementation cp --abi cp312 --only-binary :all:
OK: wheelhouse contains 84 accepted wheels
OK: wrote dist/eidp-windows-ci-diagnostic.zip (202.1 MB)
OK: wrote checksum sidecar dist/eidp-windows-ci-diagnostic.zip.sha256
```

The package SHA256 is
`f0284e1999a30b4b5aec47d6b1a0fe889495ba90f2d18e90f7b077092183880d`. Running
`uv run python scripts/verify_windows_distribution.py
dist/eidp-windows-ci-diagnostic.zip --json` rejected it only for the expected
dirty-source release blocker:

```text
BUILD_INFO.json git_dirty must be false
```

The verifier still read the package structure and reported `wheel_count=84`,
`entry_count=3099`, `project_wheel_count=1`, and the same SHA256. This is
diagnostic evidence only; the next release-grade ZIP must be rebuilt from a
clean committed checkout.

## Clean CI Simulation

To separate the expected dirty-build blocker from the next GitHub CI run, the
current working tree was copied to a temporary clean git checkout under `/tmp`,
committed there, and run through the CI package path:

```bash
uv sync --locked --extra dev --extra scraper-basic --extra pdf
uv run python scripts/download_windows_runtime.py
uv run python scripts/build_windows_zip.py --out-zip dist/eidp-windows-ci.zip
uv run python scripts/verify_windows_distribution.py dist/eidp-windows-ci.zip
uv run python scripts/run_non_windows_release_gates.py \
  dist/eidp-windows-ci.zip \
  --skip-full-unit \
  --json \
  --output logs/release-gate-ci.json
```

Result:

```text
verify_windows_distribution.py: OK core
run_non_windows_release_gates.py: "ok": true
BUILD_INFO git_dirty: false
wheel_count: 84
entry_count: 3096
sha256: cdcd9832e64d182b06287fa9ef42af43b99eb63b6574734759833d7d61521cf0
size_bytes: 211937298
```

The simulation was refreshed against the current local source snapshot after
the direct `eidp ingest-pdfs` `--target-fiscal-year` override, the
weekly-timeout bug signal detector, stable aging-signal IDs, the package
verifier local-user path guard, the `scan_bug_signals` API naming update,
manual weekly rediscovery progress JSON, duplicate-launch protection, the
shared-origin path-derived fallback budget, and the bug-report
secret-assignment scrub and the forward-slash Windows user-path scrub. The
fresh temporary clean checkout used commit
`54df409531d758adeef47d3edb6eb1cabbafaa21`;
`verify_windows_distribution.py` returned `OK core`, and
`run_non_windows_release_gates.py --skip-full-unit` returned `"ok": true` with
package SHA256
`cdcd9832e64d182b06287fa9ef42af43b99eb63b6574734759833d7d61521cf0` and
`size_bytes=211937298`.

This is not a release artifact because the commit exists only in the temporary
simulation checkout. It does prove that, after the pip dependency fix is
committed and pushed, the CI Windows ZIP and non-Windows release-gate path are
expected to pass beyond the previous `No module named pip` failure.

## Dirty-build filename guard

Dirty ZIP builds are now required to use an output filename containing
`diagnostic` or `dirty`. This command was intentionally rejected before wheel
build or ZIP assembly:

```bash
uv run python scripts/build_windows_zip.py \
  --allow-dirty \
  --skip-download \
  --out-zip dist/eidp-windows-v466.zip
```

Result:

```text
RuntimeError: --allow-dirty ZIP builds are diagnostic only; use an output filename containing 'diagnostic' or 'dirty' to avoid mistaking it for a release package
```

## Bootstrap fiscal-year override guard

The package contract now also requires `scripts/bootstrap_pdf_pipeline.py` to
carry the explicit `--target-fiscal-year` override through discovery, ingest,
status rebuild, and RCA artifacts. This prevents retroactive bootstrap/proof
runs from relying on ambient `EIDP_TARGET_FISCAL_YEAR` alone.

Validation:

```text
uv run python scripts/bootstrap_pdf_pipeline.py --help | rg -n "target-fiscal-year|EIDP_TARGET_FISCAL_YEAR"
uv run pytest tests/unit/test_bootstrap_pdf_pipeline.py tests/unit/test_windows_distribution_verifier.py -q
```

Result:

```text
--target-fiscal-year TARGET_FISCAL_YEAR
reads EIDP_TARGET_FISCAL_YEAR.
143 passed
```

## Direct ingest fiscal-year override guard

The package contract now also requires direct `eidp ingest-pdfs` invocations to
accept and forward `--target-fiscal-year`. This closes the retroactive CLI path
where ingestion could otherwise rely on ambient `settings.target_fiscal_year`.

Validation:

```text
uv run eidp ingest-pdfs --help
uv run pytest tests/unit/test_cli_ingest.py -q
```

Result:

```text
--target-fiscal-year INTEGER RANGE [2019<=x<=2099]
3 passed
```

## Local bug-report bundle guard

The package now includes the Phase 1 local-only bug-report bundle path:

- `scripts/collect_bug_report.py`
- `scripts/collect_bug_report.bat`
- `src/eidp/bug_signals/detector.py`
- `src/eidp/bug_signals/bundle.py`
- `src/eidp/review/_pages/bug_report.py`

The implementation is intentionally local-only: it detects blocking P0 signals
and the P1 `weekly_run_timeout_no_last_run` signal through `scan_bug_signals`,
keeps `scan_p0_bug_signals` as a compatibility wrapper, creates a sanitized ZIP,
excludes SQLite/PDF/Excel runtime data, scrubs path/email/school/operator
fields plus common secret assignments, and does not upload.

Validation:

```text
uv run pytest tests/unit/test_bug_signals.py tests/unit/test_review_bug_report.py \
  tests/unit/test_windows_distribution_verifier.py::test_verify_core_zip_accepts_complete_distribution -q
uv run pytest tests/unit/test_bug_signals.py tests/unit/test_review_bug_report.py \
  tests/unit/test_review_app.py tests/unit/test_windows_distribution_verifier.py -q
uv run pytest tests/unit/test_bug_signals.py tests/unit/test_review_bug_report.py \
  tests/unit/test_review_app.py \
  tests/unit/test_windows_distribution_verifier.py::test_verify_core_zip_accepts_complete_distribution -q
uv run python scripts/collect_bug_report.py \
  --root . \
  --out _temp/bug-report-current-smoke-scrubbed2.zip \
  --note "smoke C:\Users\private_user school_name test@example.com 学校名=秘密学校" \
  --json
```

The refreshed focused bug-report/UI slice returned `13 passed`, including
secret-assignment scrubbing. The broader bug-signal API slice returned
`25 passed` after renaming the primary scanner to `scan_bug_signals` and
retaining the old wrapper. The earlier focused bug-report/distribution tests
returned `11 passed`, and the broader bug-report/UI/distribution slice returned
`137 passed`. The focused
portability/runbook contract file returned `2 passed` after adding
`tests/unit/test_portability_contract.py`, which scans runtime/test/CI files
and packaged operator docs for current-machine and optional
`EIDP_FORBIDDEN_LOCAL_USERS` tokens without hardcoding private usernames in
public source, and now also guards the v465 promotion runbook's task
backup/restore approval boundary. The full distribution verifier slice
returned `124 passed` after adding a package-level rejection test for real
`C:\Users\<name>` and `/Users/<name>` path forms in the packaged runbook and
E2E template. The combined CI workflow, portability, and distribution verifier
contract refresh returned `133 passed`. Ruff and mypy passed
for the touched bug-report, UI, distribution-verifier, and portability files. The smoke
generated a local ZIP with only `lock-state.json`, `bug-signals.json`, and
`manifest.json` in the current repo state, and the CLI JSON plus ZIP manifest
scrubbed `/Users/...`, `C:\Users\...`, email, and school-name note content.
SQLite/PDF/Excel payloads were not bundled.

## Manual weekly progress guard

Manual weekly rediscovery now writes a progress JSON file and the Streamlit
school-year task page renders that progress after starting the background run.
The weekly runner accepts `--progress-file` and `--progress-log-path`, writes
selection, discovery, ingest, success, and failure states, and keeps the
artifact under `logs/weekly-rediscovery-*.json` for operator visibility.

Validation:

```text
uv run pytest tests/unit/test_run_weekly_target_year_discovery.py \
  tests/unit/test_review_school_year_tasks.py \
  tests/unit/test_windows_distribution_verifier.py::test_verify_core_zip_requires_weekly_artifact_pruning_contract -q
uv run ruff check scripts/run_weekly_target_year_discovery.py \
  src/eidp/review/_pages/school_year_tasks.py \
  tests/unit/test_run_weekly_target_year_discovery.py \
  tests/unit/test_review_school_year_tasks.py \
  scripts/verify_windows_distribution.py \
  tests/unit/test_windows_distribution_verifier.py
uv run mypy scripts/run_weekly_target_year_discovery.py \
  src/eidp/review/_pages/school_year_tasks.py \
  scripts/verify_windows_distribution.py
```

Result:

```text
83 passed
All checks passed!
Success: no issues found in 3 source files
```

## Shared-origin discovery cache stress guard

The PDF discovery cache now has a production-shape regression for large shared
corporation origins. The test seeds `150` school paths under one origin and
asserts that shared `robots.txt`, `sitemap.xml`, and common disclosure-page GETs
are each fetched once instead of once per school.
For large same-origin groups, path-derived fallback pages are now budgeted per
origin: the first `3` school sites keep the full fallback probes, then later
same-origin school sites skip those derived fallback probes. The regression
asserts `shared_origin_derived_fallback_skipped=147` for the `150`-school case,
while still allowing the school home pages themselves to be fetched.

Validation:

```text
uv run pytest tests/unit/test_pdf_discovery.py \
  -k "reuses_rejected_candidate or shared_origin_cache_scales or shared_origin_robots_sitemap or repeated_http_gets" -q
uv run ruff check tests/unit/test_pdf_discovery.py
```

Result:

```text
4 passed, 168 deselected
All checks passed!
```

## Packaged username/path scrub check

The rebuilt diagnostic ZIP was scanned directly after the operator runbooks were
changed from test-machine paths to `%USERPROFILE%` placeholders.

Validation:

```text
zipgrep -n "<local forbidden username/path pattern>" dist/eidp-windows-v466-diagnostic.zip
cat dist/eidp-windows-v466-diagnostic.zip.sha256
shasum -a 256 -c dist/eidp-windows-v466-diagnostic.zip.sha256
unzip -l dist/eidp-windows-v466-diagnostic.zip | \
  rg -n "docs/runbooks/eidp-windows.md|docs/runbooks/eidp-operator-e2e-template.md|tests/|docs/reports/"
```

Result:

```text
zipgrep: no matches, exit 1
dist/eidp-windows-v466-diagnostic.zip: OK
packaged docs: docs/runbooks/eidp-windows.md, docs/runbooks/eidp-operator-e2e-template.md
tests/docs-reports entries: none
```

## Distribution Verifier

Command:

```bash
uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v466-diagnostic.zip
```

Result: exit `1`, with exactly one blocker:

```text
error: BUILD_INFO.json git_dirty must be false
```

Verifier details included:

| Field | Value |
| --- | --- |
| `git_commit` | `364f25a4fd95e1b7c85ace76e635c7a77954d583` |
| `git_dirty` | `true` |
| `entry_count` | `3099` |
| `has_runtime` | `True` |
| `wheel_count` | `84` |
| `project_wheel_count` | `1` |
| `prefecture_seed_rows` | `47` |
| `prefecture_seed_downloadable` | `47` |
| `prefecture_seed_parser_supported` | `47` |
| `discovery_gold_set_entries` | `44` |
| `discovery_gold_set_outcomes.publication_lag_latest_public` | `17` |
| `sha256` | `6cfc475c9723c4712fd513c09ab615edbd7b1bb68ef357e6f0c44743c2820126` |
| `size_bytes` | `211941268` |

No missing publication-lag exception, mature-year metric, runbook/template,
bootstrap target-fiscal-year override, local bug-report bundle, seed, runtime,
wheelhouse, mature-year proof, or discovery-gold contract errors were reported.

## Conclusion

The current source tree packages cleanly at the content-contract level and the
CI wheel-download failure path is now directly exercised locally. The only
release blocker for a successor package is source cleanliness: commit or
otherwise produce a clean source snapshot, rebuild without `--allow-dirty`, then
rerun the package gates. This diagnostic ZIP must not be transferred as the
owner/operator release package.

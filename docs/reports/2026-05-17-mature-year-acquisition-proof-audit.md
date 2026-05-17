# Mature-Year Acquisition Proof Audit

Date: 2026-05-17
Branch: `sprint8-handoff-finalize`
Status: proof not yet satisfied

## Purpose

This audit checks whether the current source has a real mature-year acquisition
proof that can support a `publication_lag` release exception for FY2026/R8. It
does not approve release and it does not replace the owner/operator cycle.

## Proof Contract

`scripts/build_mature_year_acquisition_proof.py` now requires every passing
case to satisfy all of the following:

- `status=success`, `dry_run=false`, and `current_fy` matches the case year.
- `target_pdf_auto_yield_pct >= 60.0`.
- `operator_reviewable_yield_pct >= 70.0`, equivalent to manual workload
  `<= 30.0`.
- `target_pdf_auto_denominator_count >= 1000`.
- `target_pdf_auto_denominator_scope == "target_missing_schools_before_run"`.
- `ship_gate_status` is consistent with `operator_reviewable_yield_pct`.

The same denominator and scope checks are enforced by
`scripts/verify_stage6_return.py` before it accepts a mature-year proof JSON.
This prevents a small bounded sample from being treated as production-scale
evidence.

## Existing Artifacts

The only existing FY2025 `last_run.json` artifacts with measured KPI values are
bounded Windows runs:

| Artifact | FY | Denominator | Strict target auto yield | Operator-reviewable yield | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| `logs/win-v452-stage6/last_run.json` | 2025 | 5 | 20.0% | 60.0% | not proof |
| `logs/win-v453-stage6/last_run.json` | 2025 | 5 | 40.0% | 60.0% | not proof |
| `logs/win-v454-stage6/last_run.json` | 2025 | 5 | 40.0% | 100.0% | not proof |

Command:

```bash
uv run python scripts/build_mature_year_acquisition_proof.py \
  --case 2025=logs/win-v454-stage6/last_run.json \
  --output logs/mature-year-acquisition-proof-existing-artifacts-20260517.json \
  --json
```

Result: `ok=false`. The proof builder rejected the best existing bounded case
because strict target auto yield was `40.0 < 60.0` and denominator was
`5 < 1000`.

## Current-Source Dry Run

A copy of the URL-rich v460 SQLite snapshot was used to avoid touching the live
repo DB:

```bash
cp logs/win-v460-plan-a/eidp-after-url-bootstrap-20260516-192256.sqlite3 \
  _temp/mature-year-fy2025-proof-20260517/data/eidp.sqlite3

EIDP_DATABASE_URL=sqlite:///$PWD/_temp/mature-year-fy2025-proof-20260517/data/eidp.sqlite3 \
EIDP_DATA_DIR=$PWD/_temp/mature-year-fy2025-proof-20260517/data \
uv run python scripts/run_weekly_target_year_discovery.py \
  --current-fy 2025 --dry-run --no-lock \
  --storage-dir _temp/mature-year-fy2025-proof-20260517/pdfs \
  --logs-dir _temp/mature-year-fy2025-proof-20260517/logs \
  --output-dir _temp/mature-year-fy2025-proof-20260517/output \
  --last-run-path _temp/mature-year-fy2025-proof-20260517/last_run.dry-run.json
```

Result:

- `target_missing_school_count=1625`.
- `no_crawlable_url_school_count=613`.
- `target_pdf_auto_yield_pct=0.0`, because this was dry-run only.
- The dry-run artifact is correctly rejected as proof because `dry_run=true`.

## Limit-20 Execution Smoke

To verify current-source execution on the mature FY2025 path without starting an
unbounded production run, the copied DB was run with `--limit 20`:

```bash
EIDP_DATABASE_URL=sqlite:///$PWD/_temp/mature-year-fy2025-proof-20260517/data/eidp.sqlite3 \
EIDP_DATA_DIR=$PWD/_temp/mature-year-fy2025-proof-20260517/data \
uv run python scripts/run_weekly_target_year_discovery.py \
  --current-fy 2025 --limit 20 --batch-size 20 \
  --rate-limit 0.1 --request-timeout 10 --ingest-batch-size 50 \
  --no-lock \
  --storage-dir _temp/mature-year-fy2025-proof-20260517/pdfs \
  --logs-dir _temp/mature-year-fy2025-proof-20260517/logs \
  --output-dir _temp/mature-year-fy2025-proof-20260517/output \
  --last-run-path _temp/mature-year-fy2025-proof-20260517/last_run.limit20.json
```

Result:

| Metric | Value |
| --- | ---: |
| `target_missing_school_count` | 20 |
| `crawled` | 20 |
| `found` | 16 |
| `downloaded` | 7 |
| `processed` | 7 |
| `target_pdf_auto_acquired_count` | 5 |
| `target_pdf_auto_yield_pct` | 25.0 |
| `operator_reviewable_count` | 13 |
| `operator_reviewable_yield_pct` | 65.0 |
| `ship_gate_status` | `pass` |
| `http_cache_hits` | 45 |
| `http_cache_misses` | 83 |
| `discovery_rejections.jsonl` | 130 lines / 56 KB |

Command:

```bash
uv run python scripts/build_mature_year_acquisition_proof.py \
  --case 2025=_temp/mature-year-fy2025-proof-20260517/last_run.limit20.json \
  --output _temp/mature-year-fy2025-proof-20260517/mature-year-proof-limit20.json \
  --json
```

Result: `ok=false`. The proof builder rejected the execution smoke because:

- Strict target auto yield was `25.0 < 60.0`.
- Denominator was `20 < 1000`.
- Manual workload was `35.0 > 30.0`.

## Sanko Hashed 2025 Target-Form Tuning

The first limit-20 smoke showed a concrete false negative in Sanko-family
disclosure pages. Current FY2025 pages can publish the target form under a
hash-like filename while the visible link text is only `2025年度`; the enclosing
section heading is `高等教育の修学支援新制度 申請様式`. The previous
site-family pre-download guard only treated `申請書`, `確認申請`, and
`様式第2号` style text as target-form context, so these candidates were
incorrectly rejected as `pre_filtered_non_target_hint`.

Current-source fix: treat `申請様式` as an application-form context only when it
combines with support-system context such as `高等教育` / `修学支援`. The
regression test
`test_sanko_support_application_form_heading_keeps_hashed_target_pdf` covers the
real observed shape without allowing unrelated Sanko course/syllabus PDFs.

A fresh copied-DB limit-20 smoke after the fix used
`_temp/mature-year-fy2025-proof-sanko-fix-20260517` and preserved its evidence
there after cleaning the default ignored runtime outputs generated by the run.

| Metric | Before fix | After fix |
| --- | ---: | ---: |
| `target_missing_school_count` | 20 | 20 |
| `downloaded` | 7 | 10 |
| `processed` | 7 | 10 |
| `target_pdf_auto_acquired_count` | 5 | 7 |
| `target_pdf_auto_yield_pct` | 25.0 | 35.0 |
| `operator_reviewable_count` | 13 | 12 |
| `operator_reviewable_yield_pct` | 65.0 | 60.0 |
| `pre_filtered` | 66 | 3 |
| `cached_rejections` | 31 | 5 |

The proof builder still correctly rejected the post-fix bounded smoke:

```bash
uv run python scripts/build_mature_year_acquisition_proof.py \
  --case 2025=_temp/mature-year-fy2025-proof-sanko-fix-20260517/last_run.limit20.json \
  --output _temp/mature-year-fy2025-proof-sanko-fix-20260517/mature-year-proof-limit20.json \
  --json
```

Result: `ok=false`, with strict target auto yield `35.0 < 60.0`, denominator
`20 < 1000`, and estimated manual workload `40.0 > 30.0`.

## Shared-Origin Inverted Disclosure Tuning

A larger copied-DB `--limit 50` smoke after the Sanko hashed-form fix exposed a
second false negative. The run-scoped shared-corporation cache correctly reduced
duplicate `robots.txt`, sitemap, and root-page fetches, but it also skipped too
many per-school derived disclosure probes on shared origins. Sanko official
index URLs often appear as school-local paths such as
`https://www.sanko.ac.jp/tokyo-med/disclosure/`, while the live publication page
is the inverted path `https://www.sanko.ac.jp/disclosure/tokyo-med/`.

Current-source fix: keep the shared-origin skip for generic fallback crawling,
but allow one inverted disclosure probe when the registered school URL ends in a
disclosure-like path. The regression test
`test_run_pdf_discovery_keeps_inverted_disclosure_probe_for_shared_origin`
covers the side effect: after the shared-origin threshold is exceeded, each
school-specific inverted disclosure URL is still tried, while broader fallback
probing remains capped.

| Metric | Sanko fix only, limit 50 | Shared-origin fix, limit 50 |
| --- | ---: | ---: |
| `target_missing_school_count` | 50 | 50 |
| `downloaded` | 17 | 22 |
| `processed` | 17 | 22 |
| `target_pdf_auto_acquired_count` | 9 | 11 |
| `target_pdf_auto_yield_pct` | 18.0 | 22.0 |
| `operator_reviewable_count` | 14 | 16 |
| `operator_reviewable_yield_pct` | 28.0 | 32.0 |
| `pre_filtered` | 29 | 16 |
| `cached_rejections` | 239 | 187 |
| `shared_origin_derived_fallback_skipped` | 31 | 26 |
| `http_cache_hits` | 64 | 81 |
| `http_cache_misses` | 90 | 83 |

The proof builder still correctly rejected the bounded smoke:

```bash
uv run python scripts/build_mature_year_acquisition_proof.py \
  --case 2025=_temp/mature-year-fy2025-proof-limit50-shared-origin-fix-20260517/last_run.limit50.json \
  --output _temp/mature-year-fy2025-proof-limit50-shared-origin-fix-20260517/mature-year-proof-limit50.json \
  --json
```

Result: `ok=false`, with strict target auto yield `22.0 < 60.0`, denominator
`50 < 1000`, and estimated manual workload `68.0 > 30.0`. This run is useful as
a false-negative tuning smoke, not as mature-year production-scale evidence.

## NKZ Multibrand URL Override Tuning

The limit-50 RCA also showed several `no_candidates_found` rows for
日本教育財団 schools whose `SchoolSite` rows still pointed only at the
corporation root. The exact NKZ disclosure indexes are public, school-specific
pages:

- `HAL東京` -> `https://www.nkz.ac.jp/clginfo/thinfo.html`
- `HAL大阪` -> `https://www.nkz.ac.jp/clginfo/ohinfo.html`
- `HAL名古屋` -> `https://www.nkz.ac.jp/clginfo/nhinfo.html`
- `首都医校` -> `https://www.nkz.ac.jp/clginfo/siinfo.html`
- `大阪医専` -> `https://www.nkz.ac.jp/clginfo/oiinfo.html`
- `名古屋医専` -> `https://www.nkz.ac.jp/clginfo/niinfo.html`

Current-source fix: add these school-domain overrides, plus their public brand
homepages, to `data/url-discovery/school_domain_overrides.csv`. The checked-in
CSV is now covered by
`test_checked_in_school_domain_overrides_cover_nkz_multibrand_schools`.

A copied-DB `--limit 12` smoke was run twice. The first run accidentally skipped
the override-infer step because the local helper script used a non-existent
`session_scope`; it is retained only as an old-DB comparison. The valid second
run applied `infer_corporation_urls(..., data_dir=Path("data"))` to the copied
DB before weekly discovery:

| Metric | Old copied DB, limit 12 | Overrides applied, limit 12 |
| --- | ---: | ---: |
| `target_missing_school_count` | 12 | 12 |
| `downloaded` | 3 | 4 |
| `processed` | 3 | 4 |
| `target_pdf_auto_acquired_count` | 2 | 4 |
| `target_pdf_auto_yield_pct` | 16.7 | 33.3 |
| `operator_reviewable_count` | 7 | 10 |
| `operator_reviewable_yield_pct` | 58.3 | 83.3 |
| `no_candidates_found` | 3 | 2 |

The proof builder still correctly rejected the override smoke:

```bash
uv run python scripts/build_mature_year_acquisition_proof.py \
  --case 2025=_temp/mature-year-fy2025-proof-limit12-nkz-overrides-applied-20260517/last_run.limit12.json \
  --output _temp/mature-year-fy2025-proof-limit12-nkz-overrides-applied-20260517/mature-year-proof-limit12.json \
  --json
```

Result: `ok=false`, with strict target auto yield `33.3 < 60.0` and denominator
`12 < 1000`. The operator-reviewable yield passed for this tiny sample, but the
sample is too small and still below the strict auto-yield release line.

A read-only live status probe for NKZ static target-form filename variants found
that `_25` cannot be generalized across the whole NKZ family:

| Prefix | `_13_25.pdf` | `_13.pdf` | Current implication |
| --- | --- | --- | --- |
| `oh` | 206 PDF | 404 | `_25` variant is the current strict candidate |
| `oi` | 206 PDF | 404 | `_25` variant is the current strict candidate |
| `om` | 206 PDF | 404 | `_25` variant is the current strict candidate |
| `th` | 404 | 206 PDF | base file remains the only published form |
| `nh` | 404 | 206 PDF | base file remains the only published form |
| `si` | 404 | 206 PDF | base file remains the only published form |
| `ni` | 404 | 206 PDF | base file remains the only published form |
| `tm` | 404 | 206 PDF | base file remains the only published form |
| `nm` | 404 | 206 PDF | base file remains the only published form |

This explains why some limit-100 NKZ rows can appear or disappear across live
runs. A safe implementation cannot blindly synthesize `_25` variants for every
NKZ prefix. It would need either page-level links to the `_25` file, a prefix
allowlist backed by live evidence, or operator confirmation.

## Remaining No-Year Target Forms

The post-fix smoke still emitted `8` `target_fiscal_year_not_detected` rows.
They collapse to two observed patterns:

| Pattern | Schools / URLs | Evidence result | Decision |
| --- | --- | --- | --- |
| NKZ static embedded target forms | `tmZ-studyspt_13.pdf`, `nmZ-studyspt_13.pdf`, `nhZ-studyspt_13.pdf` | PDF sample text classified as `target`, but `_detect_fiscal_year_from_text(..., max_fiscal_year=2025)` returned `None`; page context also lacks a `2025年度` / `令和7年度` label | keep operator-reviewable |
| NEEC current publication page | `portal_syllabus_kamata_yoshiki.pdf`, `portal_syllabus_hachioji_yoshiki.pdf` | PDF sample text classified as `target`, but detected year returned `None`; link text names the target form but not the fiscal year | keep operator-reviewable |

These are not safe candidates for automatic current-FY acquisition under the
strict contract. Accepting them would require trusting a live publication page
or a yearless static filename as current-year evidence, which is the same class
of false-positive risk that the strict target-FY gate is meant to prevent. They
should remain reviewable until a reliable site-specific year signal or operator
confirmation exists.

## Post-Patch Limit-100 FY2025 Smoke

A later copied-DB FY2025 `--limit 100` smoke was run after the Sanko,
shared-origin, NKZ override, SNM bare-year, cached-rejection evidence
suppression, public metadata cache, legal-citation, and file-like derived-path
fixes. The run stayed isolated under
`_temp/fy2025-postpatch-limit100-20260517` and used its own PDF storage path;
a follow-up `data/pdfs` mtime check found no default-runtime writes.

| Metric | Previous FY2025 limit-100 | Post-patch FY2025 limit-100 |
| --- | ---: | ---: |
| `target_missing_school_count` | 100 | 100 |
| `downloaded` | 44 | 45 |
| `processed` | 44 | 45 |
| `target_pdf_auto_acquired_count` | 31 | 32 |
| `target_pdf_auto_yield_pct` | 31.0 | 32.0 |
| `operator_reviewable_count` | 46 | 46 |
| `operator_reviewable_yield_pct` | 46.0 | 46.0 |
| `discovery_rejections.jsonl` | 583 rows | 295 rows |
| `cached_rejection_evidence_suppressed` | n/a | 277 |

The SNM candidate
`confirmation-application.pdf?date=2025` was accepted and inserted as a FY2025
document for `school_id=80`; that accounts for the one-point strict auto-yield
increase. The proof builder would still reject this bounded smoke because
strict target auto yield is `32.0 < 60.0`, denominator is `100 < 1000`, and
manual workload remains above the `30%` release line.

## Disclosure-Path Year Hint Tuning

The legal-citation and file-path RCA found another concrete false negative in
Sendai Eco-family disclosure paths. The target form body and filename can look
yearless, while the stable public-information path itself carries the current
year, for example:

`https://www.sendai-eco.ac.jp/assets/doc/school/public_info/2025/12/kakunin_02.pdf`

Current-source fix: trust a path year only when it is inside a disclosure-like
segment such as `public_info/2025/` or `pdf2025/` and the URL/text context is
already strongly target-form-like (`kakunin`, `shinsei`,
`confirmation_application`, or equivalent Japanese support/application text).
The regression tests
`test_download_pdf_accepts_disclosure_path_year_when_body_is_target_form` and
`test_pre_download_rejects_stale_disclosure_path_year_for_target_form` cover
both the accepted current-year case and a stale `public_info_2024/.../kakunin`
rejection.

A targeted copied-DB probe against the observed Sendai-family school set used
`_temp/fy2025-disclosure-path-targeted-20260517`:

| Metric | Value |
| --- | ---: |
| `crawled` | 5 |
| `found` | 5 |
| `downloaded` | 1 |
| `failed` | 0 |
| `target_fiscal_year_not_detected` | 6 |
| `fiscal_year_mismatch` | 4 |

The new acquisition was `school_id=88`, inserted as FY2025 target evidence with
`year_evidence=url_hint` from
`https://www.sendai-eco.ac.jp/assets/doc/school/public_info/2025/12/kakunin_02.pdf`.

A fresh isolated FY2025 `--limit 100` run after this tuning used
`_temp/fy2025-disclosure-path-limit100-20260517`:

| Metric | Post-patch limit-100 | Disclosure-path limit-100 |
| --- | ---: | ---: |
| `target_missing_school_count` | 100 | 100 |
| `downloaded` | 45 | 44 |
| `processed` | 45 | 44 |
| `target_pdf_auto_acquired_count` | 32 | 30 |
| `target_pdf_auto_yield_pct` | 32.0 | 30.0 |
| `operator_reviewable_count` | 46 | 41 |
| `operator_reviewable_yield_pct` | 46.0 | 41.0 |
| `cached_rejection_evidence_suppressed` | 277 | 381 |
| `http_cache_hits` | n/a | 397 |
| `http_cache_misses` | n/a | 207 |

The run proves the disclosure-path rule is useful but not yet gate-moving. It
gained the `school_id=88` Sendai Eco target PDF, while the live sample lost two
previously accepted NKZ rows for `school_id=8` and `school_id=11`. The strict
auto-yield line remains far below the 60% release contract, and the denominator
is still a bounded smoke (`100 < 1000`), not production-scale proof.

This is also a gate-design finding, not only an algorithm bug finding. The
bounded FY2025 sample is mature-year data, yet the measured strict auto yield is
only `30.0%` and the operator-reviewable yield is only `41.0%`. That means the
current `60%` strict-auto gate cannot be explained by FY2026/R8 publication lag
alone. Before owner sign-off, the release gate needs an explicit business
decision: either lower/recalibrate the strict-auto threshold, redefine the
numerator to include operator-reviewable/manual-confirmed coverage, or invest in
additional discovery work until true strict-auto yield approaches the original
60-70% target.

Current source now makes this threshold gap machine-readable via
`ship_gate_threshold_gaps(...)`. For the observed FY2025 `30.0%` strict-auto /
`41.0%` operator-reviewable result, the expected gaps are
`["strict_auto_yield", "manual_workload"]`. This does not lower the release
gate by itself; it forces the recalibration discussion to be explicit before
owner sign-off.

## Legal-Citation And File-Path Noise Tuning

The same limit-100 evidence exposed `14` `fiscal_year_mismatch:2019` rows whose
year came from the fixed legal citation `令和元年法律第8号`, not from a stale
fiscal-year label. Current source now ignores that legal-citation suffix when
parsing URL/anchor fiscal-year hints. A targeted 5-school run showed all `14`
rows are no longer pre-download rejected, but they still did not become
automatic acquisitions because the downloaded target-form PDFs lacked reliable
FY2025 evidence or were classified as non-target.

A second targeted run also confirmed that file-like disclosure URLs such as
`public_info.html` are no longer expanded into invalid paths like
`public_info.html/information`. In the 5-school targeted comparison,
`not_pdf_magic` dropped from `2` to `0`, `candidate_budget_dropped` dropped from
`8` to `0`, and invalid `public_info.html/...` evidence rows dropped from `10`
to `0`. This is a performance/noise fix, not a yield claim.

## Verification

```bash
uv run pytest \
  tests/unit/test_mature_year_acquisition_proof.py \
  tests/unit/test_stage6_return_verifier.py \
  tests/unit/test_ship_gate_contract.py -q
```

Result: `22 passed`.

```bash
uv run pytest tests/unit/test_pdf_discovery.py \
  -k "disclosure_path_year or upload_path or law_enactment_year_reference" -q
```

Result: `4 passed, 177 deselected, 5 warnings`.

```bash
uv run pytest tests/unit/test_pdf_discovery.py -q
```

Result: `181 passed, 5 warnings`.

```bash
uv run pytest -q
```

Result: `1740 passed, 5 warnings`.

```bash
uv run ruff check src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py
```

Result: `All checks passed!`.

```bash
uv run mypy src/eidp/scraper/pdf_discovery.py
```

Result: `Success: no issues found in 1 source file`.

```bash
uv run pytest tests/unit/test_url_discovery.py -q
```

Result: `20 passed`.

```bash
uv run ruff check tests/unit/test_url_discovery.py
```

Result: `All checks passed!`.

```bash
uv run ruff check \
  scripts/build_mature_year_acquisition_proof.py \
  scripts/verify_stage6_return.py \
  scripts/ship_gate_contract.py \
  tests/unit/test_mature_year_acquisition_proof.py \
  tests/unit/test_stage6_return_verifier.py \
  tests/unit/test_ship_gate_contract.py
```

Result: `All checks passed!`.

```bash
uv run mypy \
  scripts/build_mature_year_acquisition_proof.py \
  scripts/verify_stage6_return.py \
  scripts/ship_gate_contract.py
```

Result: `Success: no issues found in 3 source files`.

## Conclusion

No current artifact satisfies mature-year production-scale acquisition proof.
The current source can complete small FY2025 execution smokes on a copied
URL-rich DB, and the Sanko hashed-form plus shared-origin inverted-disclosure
tuning measurably improved the strict target yield in bounded samples. The NKZ
multibrand overrides also improved a small operator-reviewable smoke, and the
disclosure-path year hint fix rescues a real Sendai-family false negative. The
measured strict target auto yield, operator-reviewable yield, and denominator
remain below the release proof contract. The repeated FY2025 bounded evidence
also suggests the existing gate threshold may be miscalibrated for the current
algorithm, even on mature-year data. The next non-owner path is therefore both
technical and contractual: continue bounded RCA against remaining
`target_fiscal_year_not_detected` candidates and site-family false negatives,
while redesigning the ship gate so it explicitly distinguishes true strict-auto
yield, operator-reviewable coverage, and manual-confirmed coverage. For NKZ
specifically, `_25` static-form variants are real for a small allowlisted subset
but unsafe as a family-wide inference. A larger controlled FY2025 run on the
copied DB should wait until these site-family rules are explicitly bounded and
tested.

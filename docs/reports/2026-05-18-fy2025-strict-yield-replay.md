# FY2025 Strict Yield Replay

Date: 2026-05-18
Scope: Mac-side only. No Windows SSH, no active-lane promotion.

## Purpose

Round 10/11 changed the release KPI semantics from broad target-PDF reach to
strict Excel-importable acquisition:

- strict target PDF = `confirmed_target` with parsed Excel data rows
- broad target PDF = target-FY PDF candidate found, not necessarily usable for Excel
- image-only PDFs without OCR-ready extraction remain `image_pending`

This replay measures the effect of current local source changes on the existing
FY2025/R7 limit-1000 probe instead of relying on theory.

## Input Artifacts

Baseline probe:

- `_temp/fy2025-yield-probe-6ef4d15-v469-limit1000/data/eidp.sqlite3`
- `_temp/fy2025-yield-probe-6ef4d15-v469-limit1000/output/20260517_233027-summary.json`
- `_temp/fy2025-yield-probe-6ef4d15-v469-limit1000/output/20260517_233027-discovery-rejections.jsonl`

Replay outputs:

- `_temp/fy2025-yield-probe-current-baseline-20260518_144024/`
- `_temp/fy2025-yield-probe-current-replay-20260518_143634/`
- `_temp/fy2025-targeted-discovery-current-20260518_144205/`

The selected-school denominator is the exact `school_ids[]` from
`20260517_233027-summary.json`, not a numeric `BETWEEN` range.

## Commands

Baseline-current-semantics rebuild:

```bash
EIDP_APP_ROOT="$PWD" \
EIDP_DATA_DIR="$PWD/_temp/fy2025-yield-probe-current-baseline-20260518_144024/data" \
EIDP_DATABASE_URL="sqlite:///$PWD/_temp/fy2025-yield-probe-current-baseline-20260518_144024/data/eidp.sqlite3" \
EIDP_TARGET_FISCAL_YEAR=2025 \
uv run eidp rebuild-school-year-tasks \
  --fiscal-year 2025 \
  --discovery-evidence-log _temp/fy2025-yield-probe-6ef4d15-v469-limit1000/output/20260517_233027-discovery-rejections.jsonl
```

Original `school_mismatch` replay:

```bash
EIDP_APP_ROOT="$PWD" \
EIDP_DATA_DIR="$PWD/_temp/fy2025-yield-probe-current-replay-20260518_143634/data" \
EIDP_DATABASE_URL="sqlite:///$PWD/_temp/fy2025-yield-probe-current-replay-20260518_143634/data/eidp.sqlite3" \
EIDP_TARGET_FISCAL_YEAR=2025 \
uv run python - <<'PY'
from pathlib import Path
from eidp.db.session import SessionLocal
from eidp.pipeline.ingest import run_ingestion

replay = Path("_temp/fy2025-yield-probe-current-replay-20260518_143634")
ids = [
    int(line)
    for line in (replay / "output/school_mismatch_existing_ids.txt").read_text().splitlines()
    if line.strip()
]
session = SessionLocal()
try:
    stats = run_ingestion(
        session,
        batch_size=len(ids),
        document_ids=ids,
        target_fiscal_year=2025,
        evidence_path=replay / "output/ingest-replay.jsonl",
    )
    session.commit()
    print(stats)
finally:
    session.close()
PY
```

Targeted discovery for the remaining 35 mismatch schools:

```bash
EIDP_APP_ROOT="$PWD" \
EIDP_DATA_DIR="$PWD/_temp/fy2025-targeted-discovery-current-20260518_144205/data" \
EIDP_DATABASE_URL="sqlite:///$PWD/_temp/fy2025-targeted-discovery-current-20260518_144205/data/eidp.sqlite3" \
EIDP_TARGET_FISCAL_YEAR=2025 \
uv run eidp discover-pdfs \
  --storage-dir "$PWD/_temp/fy2025-targeted-discovery-current-20260518_144205/pdfs" \
  --batch-size 35 \
  --request-timeout 10 \
  --rate-limit 0.1 \
  --evidence-log "$PWD/_temp/fy2025-targeted-discovery-current-20260518_144205/output/discovery-rejections.jsonl" \
  --school-id 179 --school-id 180 --school-id 181 --school-id 182 --school-id 187 \
  --school-id 191 --school-id 236 --school-id 254 --school-id 255 --school-id 274 \
  --school-id 275 --school-id 278 --school-id 285 --school-id 293 --school-id 294 \
  --school-id 295 --school-id 296 --school-id 297 --school-id 298 --school-id 299 \
  --school-id 407 --school-id 408 --school-id 429 --school-id 430 --school-id 491 \
  --school-id 501 --school-id 502 --school-id 529 --school-id 530 --school-id 596 \
  --school-id 625 --school-id 887 --school-id 888 --school-id 889 --school-id 1117
```

## Results

Selected-school denominator: `1000`.

| Scenario | strict parsed | strict pct | broad confirmed | broad pct | combined reviewable |
| --- | ---: | ---: | ---: | ---: | ---: |
| current-semantics baseline | 384 | 38.4% | 488 | 48.8% | 708 / 70.8% |
| original mismatch ingest replay | 388 | 38.8% | 492 | 49.2% | 712 / 71.2% |
| targeted discovery + original replay | 389 | 38.9% | 494 | 49.4% | 714 / 71.4% |

Original mismatch replay:

- input `school_mismatch` documents: `39`
- files present: `39`
- re-ingested: `4`
- still `school_mismatch`: `35`
- rescued document IDs: `8`, `27`, `55`, `488`

Targeted discovery on the remaining 35 mismatch schools:

- `crawled=35`
- `downloaded=6`
- new downloaded candidates that ingested: `2`
- new downloaded candidates still `school_mismatch`: `4`
- `candidate_school_mismatch=15541`
- `candidate_budget_dropped=2954`

## Interpretation

The current local fixes improve strict FY2025 limit-1000 yield by only
`+5/1000` schools, from `38.4%` to `38.9%`.

That is not close to the v1.0 release line of 60-70% strict target-PDF
auto-acquisition. The remaining gap is not an owner-cycle problem and not a
metric-display problem. It is primarily dense / multibrand page candidate
ranking and filtering:

- many pages expose many valid target-form PDFs for sibling schools
- current discovery can find/download some correct replacements
- most accepted candidates on these dense pages still resolve to the wrong
  sibling school at ingest time

## Decision

Do not use broad target-PDF reach or operator-reviewable coverage as a
substitute for strict Excel-importable acquisition.

Before v1.0 can claim the 60-70% strict line, EIDP needs additional discovery
algorithm work, most likely in dense-page ranking / per-school candidate
selection. Local AI / LLM candidate ranking may be useful for v1.1, but the
current v1.0 code path remains below the strict release gate.

## Post-Report All-Japan Group-Page Probe

Commit `a642416` adds WordPress group-heading context for dense All-Japan
`academic_support.pdf` links and expands school-label parsing for leading
`専門学校...` names plus NFKC ampersand names.

A copied-DB smoke at `_temp/all-japan-expanded-smoke/` reran all schools with
an All-Japan `school_site` (`40` sites):

- discovery: `downloaded=23`, `failed=15`
- evidence buckets: `accepted_target_pdf=23`, `school_identity_mismatch=1`,
  `non_target_candidates_only=15`
- public disclosure-page slice `289`-`312`: all exact current-year target PDFs
  were accepted except school `294`, whose PDF body school name still needs
  operator-reviewed alias evidence

After `ingest-pdfs`, `rebuild-school-year-tasks`, and
`analyze_strict_yield_gaps.py` on that copied DB:

| Scenario | strict parsed | strict pct | broad confirmed | broad pct | excel-ready |
| --- | ---: | ---: | ---: | ---: | ---: |
| targeted discovery + original replay | 389 | 16.1% status-scope | 494 | 20.4% status-scope | 389 |
| All-Japan group-heading copied replay | 408 | 16.9% status-scope | 514 | 21.3% status-scope | 408 |

This is a real dense-page ranking improvement (`+19` strict/excel-ready schools
on the full 2418-school status scope), but it still leaves the strict line far
below 60-70%. The next algorithmic blockers remain O-Hara / Sanko / other dense
group hosts and no-url coverage.

## Post-Report O-Hara Shared-Disclosure Probe

The current local patch gives `www.o-hara.ac.jp` a host-specific first derived
disclosure URL, `https://www.o-hara.ac.jp/about/joho/`, and lets that single
high-confidence URL bypass shared-origin derived-fallback throttling in the
same way as per-school inverted disclosure URLs.

Focused unit coverage:

- `test_o_hara_root_derives_about_joho_first_for_shared_origin_budget`
- `test_run_pdf_discovery_keeps_host_specific_disclosure_probe_for_shared_origin`

A copied-DB smoke at `_temp/o-hara-about-joho-smoke-small/` reran five O-Hara
root-site schools (`179`, `180`, `182`, `183`, `205`) after deleting their
existing `Document` and `CrawlJob` rows:

- discovery: `crawled=5`, `found=5`, `downloaded=1`, `failed=0`
- `shared_origin_derived_fallback_skipped=0`
- accepted school: `205` / `大原簿記公務員専門学校千葉校`
- accepted PDF:
  `https://www.o-hara.ac.jp/about/joho/pdf/2025-1-29-01-5.pdf`
- accepted evidence: `page_url=https://www.o-hara.ac.jp/about/joho/`,
  `year_evidence=url_hint`

The failed sample rows show the next O-Hara blocker is not URL reachability:

- school `179` target name is `大原簿記公務員情報医療専門学校函館校`, while the
  matching O-Hara PDF label is
  `大原公務員・医療事務・語学専門学校函館校`; discovery correctly records
  `candidate_school_mismatch` without alias evidence.
- school `180` target name is `大原簿記情報ビジネス医療福祉専門学校盛岡校`, while
  the current O-Hara PDF labels include `大原ビジネス公務員専門学校盛岡校` and
  `盛岡情報ITクリエイター専門学校`.

Therefore the O-Hara fix is a real shared-disclosure reachability improvement,
but it is not enough to move O-Hara into the strict 60-70% line. The next
O-Hara layer needs dense-page per-school candidate selection and
operator-reviewed rename / alias evidence, not broad school-name acceptance.

## Post-Report Sanko Exact-Site Override Probe

The current local data patch adds `22` exact Sanko school-site overrides to
`data/url-discovery/school_domain_overrides.csv`. Each added URL was checked on
2026-05-18 by fetching the live page and requiring HTTP `200` plus a `<title>`
that matched the target school name after local normalization. Candidate URLs
with a title mismatch, HTTP `503`, or HTTP `404` were intentionally excluded.

`test_checked_in_school_domain_overrides_cover_sanko_exact_school_sites`
guards the checked-in Sanko override set.

A copied-DB write smoke at `_temp/sanko-overrides-smoke/` called
`infer_corporation_urls(..., data_dir=Path("data"))` against the FY2025 replay
DB copy. It added exactly `22` Sanko `school_domain_override` rows, including
root-bucket schools such as:

- `16` / `千葉医療秘書&IT専門学校` ->
  `https://www.sanko.ac.jp/chiba-med/`
- `23` / `神戸元町医療秘書専門学校` ->
  `https://www.sanko.ac.jp/kobe-med/`
- `25` / `福岡医療秘書福祉専門学校` ->
  `https://www.sanko.ac.jp/fukuoka-med/`
- `31` / `千葉リゾート＆スポーツ専門学校` ->
  `https://www.sanko.ac.jp/chiba-sports/`
- `68` / `福岡ウェディング＆ブライダル専門学校` ->
  `https://www.sanko.ac.jp/fukuoka-bridal/`

The 22-school discovery smoke then deleted existing `Document` / `CrawlJob`
rows for those schools and reran targeted discovery on the copied DB:

- discovery: `crawled=44`, `found=44`, `downloaded=9`, `failed=22`
- `school_domain_override` successes accepted via `year_evidence=url_hint`
- accepted schools: `16`, `23`, `25`, `31`, `37`, `54`, `59`, `60`, `68`
- representative accepted PDF:
  `https://www.sanko.ac.jp/disclosure/chiba-med/docs/yoshiki2025.pdf`

After `ingest-pdfs`, `rebuild-school-year-tasks`, and
`analyze_strict_yield_gaps.py` on that copied DB:

| Scenario | strict parsed | strict pct | broad confirmed | broad pct | excel-ready |
| --- | ---: | ---: | ---: | ---: | ---: |
| current v481 replay baseline | 389 | 16.1% status-scope | 494 | 20.4% status-scope | 389 |
| Sanko exact-site copied replay | 397 | 16.4% status-scope | 503 | 20.8% status-scope | 397 |

This is a real offline URL-coverage improvement (`+8` strict/excel-ready
schools on the full 2418-school status scope). It also confirms the remaining
Sanko failures are not a single URL-root issue. Many beauty / AI pages either
publish stale-year target forms, body-name mismatches, or target-form candidates
that still require stricter candidate ranking / year-evidence handling.

## Verification

After the related local code changes and this report:

```bash
uv run pytest -q
uv run mypy src
uv run ruff check src/eidp/review/_pages/school_year_tasks.py \
  scripts/validate_windows_install.py scripts/ship_gate_contract.py \
  tests/unit/test_review_school_year_tasks.py \
  tests/unit/test_windows_install_validator.py tests/unit/test_ship_gate_contract.py
git diff --check
```

Observed:

- `1795 passed, 5 warnings`
- `mypy`: success, 89 source files
- `ruff`: all checks passed for the targeted files
- `git diff --check`: clean

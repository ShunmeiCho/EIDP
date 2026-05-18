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

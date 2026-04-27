# Sprint 1 B2 - Aichi/Niigata Parser + Apply Gate Review

**日付:** 2026-04-27
**対象:** B2 read-only expansion, verified-only apply safety
**結論:** B2 は次工程に進める。ただし `--apply` は owner 承認済み verification file を明示すること。

---

## 1. Parser expansion result

| Pref | Extracted | Matched | Actionable before verify | Review | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| aichi | 111 | 104 | 63 | 7 | Official Aichi HTML index. All 111 rows have URLs. |
| niigata | 69 | 63 | 0 | 6 | 13-col PDF parsed, but current source has no URL values. |

Commit: `2585ac2 feat(aggregator): parse Aichi index and Niigata list`

## 2. HTTP verification

Verification artifact:

```bash
output/pref-aggregator/url-verification-20260427_162629.json
```

| Pref | ownership_ok rows | unique URLs |
| --- | ---: | ---: |
| aichi | 44 | 42 |
| miyagi | 3 | 3 |
| tokyo | 1 | 1 |
| **total** | **48** | **46** |

Verified-only dry-run after safety fix:

```bash
uv run python scripts/apply_writer_plan.py --all --verified-only \
  --verification-file output/pref-aggregator/url-verification-20260427_162629.json
```

Result:

| add | upgrade | review | skipped_not_verified | errors |
| ---: | ---: | ---: | ---: | ---: |
| 6 | 42 | 73 | 60 | 0 |

Prefecture split:

| Pref | add | upgrade |
| --- | ---: | ---: |
| aichi | 6 | 38 |
| miyagi | 0 | 3 |
| tokyo | 0 | 1 |

## 3. Discovery simulation

Simulation artifact:

```bash
output/pref-aggregator/sim-discover-20260427_163016.json
```

| Pref | rows | target_likely | target_marginal | ambiguous | no_pdf_found |
| --- | ---: | ---: | ---: | ---: | ---: |
| aichi | 44 | 14 | 11 | 9 | 10 |
| miyagi | 3 | 0 | 2 | 0 | 1 |
| tokyo | 1 | 0 | 1 | 0 | 0 |
| **total** | **48** | **14** | **14** | **9** | **11** |

Expected near-term discovery yield: 28/48 rows have target-likely or target-marginal candidates.
Only 3/48 have R8 URL/anchor signals, so this remains a coverage/discovery step, not an R8 completion step.

## 4. Review findings and fixes

### P0 fixed: shared URL leakage

Bug:

- `apply_writer_plan.py --verified-only` used a URL-only set.
- If two schools shared one disclosure URL, one `ownership_ok=True` row could authorize a sibling row where `ownership_ok=False`.
- Real leaked candidate: Aichi shared URL for `https://www.ndanma.ac.jp/information/disclose/`.

Fix:

- Gate now uses `(pref, school_id, url)`.
- Regression test added for shared URL row identity.

Commit: `afe843a Prevent verified-only apply from leaking shared URLs`

### P1 fixed: verification artifact reproducibility

Risk:

- After B2, `--all --verified-only` no longer means old B1 scope.
- Auto-latest verification changed expected dry-run from old B1 `upgrade=2` to B2 `add=6, upgrade=42`.

Fix:

- Added `--verification-file`.
- Apply report records the selected verification artifact.
- Owner-approved apply commands can now replay the exact dry-run artifact.

Commit: `7fd6bae Make aggregator apply verification reproducible`

Old B1 scope remains reproducible:

```bash
uv run python scripts/apply_writer_plan.py --all --verified-only \
  --verification-file output/pref-aggregator/url-verification-20260427_143941.json
```

Result: `add=0, upgrade=2, errors=0`.

## 5. Verification

Local:

- `uv run ruff check scripts/apply_writer_plan.py tests/unit/test_apply_writer_plan.py` - PASS
- `uv run pytest -q tests/unit/test_apply_writer_plan.py -p no:cacheprovider` - PASS
- `uv run pytest -q -p no:cacheprovider` - 137 passed

Venus:

- `uv run --extra dev ruff check scripts/apply_writer_plan.py tests/unit/test_apply_writer_plan.py` - PASS
- `uv run --extra dev pytest -q -p no:cacheprovider` - 137 passed
- B2 verified-only dry-run - `add=6, upgrade=42, errors=0`
- Old B1 verified-only dry-run - `add=0, upgrade=2, errors=0`

Known existing verification debt:

- `uv run ruff check .` still fails on pre-existing migrations/debug/operator UI lint debt.
- `uv run mypy src` still fails on pre-existing typing/stub debt.

## 6. Go / no-go decision

**Go for next read-only / owner-approved step.**

Recommended options:

1. Owner-approved B2 apply:

```bash
uv run python scripts/apply_writer_plan.py --all --apply --verified-only \
  --verification-file output/pref-aggregator/url-verification-20260427_162629.json
```

Expected: `add=6, upgrade=42, errors=0`.

2. Conservative old-B1-only apply:

```bash
uv run python scripts/apply_writer_plan.py --all --apply --verified-only \
  --verification-file output/pref-aggregator/url-verification-20260427_143941.json
```

Expected: `add=0, upgrade=2, errors=0`.

3. Continue read-only parser expansion before any write:

- rescue Aichi `html_suspect/http_err` rows
- find URL-bearing Niigata source or alternate official index
- spike remaining unknown prefectures

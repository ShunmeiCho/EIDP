# v513 Sanko Disclosure Probe Package

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
Package: `dist/eidp-windows-v513.zip`
Package source commit: `2905397b0d9f0e595b3a0f79d375c360e5eb5e43`
Package SHA256: `92dc137bdb5c7d2ec662102367daec11ebe1ebd3d1e34f6cbd617f82f02e8fca`

## Summary

v513 is a Mac-side package rebuild after addressing a v502 limit-50 RCA
`no_pdf_candidates` bucket for Sanko medical-secretary schools. The checked-in
Sanko overrides correctly point at exact school roots such as
`https://www.sanko.ac.jp/chiba-med/`, but several of those roots are sparse;
their target-form history is published on the group disclosure path
`https://www.sanko.ac.jp/disclosure/<school-slug>/`.

The shared-origin throttle already preserves inverted disclosure probes and
host-specific probes. v513 adds a Sanko-scoped per-school slug probe so the
throttle still allows one `/disclosure/{slug}` page for Sanko exact school
roots. This keeps the large shared-origin performance guard intact for
unrelated hosts.

This is a discovery-evidence improvement, not a release-gate bypass. It can
convert sparse-root Sanko cases from `no_pdf_candidates` into concrete
disclosure-page evidence, but stale FY2025 forms still do not count as strict
FY2026/R8 success.

## Evidence

The v502 RCA batch plan showed `no_pdf_candidates` for schools including:

- `千葉医療秘書&IT専門学校` with root `https://www.sanko.ac.jp/chiba-med/`
- `東京医療秘書歯科衛生＆IT専門学校` with root `https://www.sanko.ac.jp/tokyo-med/`
- `横浜医療秘書専門学校` with root `https://www.sanko.ac.jp/yokohama-med/`
- `名古屋医療秘書福祉&IT専門学校` with root `https://www.sanko.ac.jp/nagoya-med/`
- `大阪医療秘書福祉&IT専門学校` with root `https://www.sanko.ac.jp/osaka-med/`
- `神戸元町医療秘書専門学校` with root `https://www.sanko.ac.jp/kobe-med/`
- `広島医療秘書こども専門学校` with root `https://www.sanko.ac.jp/hiroshima-med/`
- `福岡医療秘書福祉専門学校` with root `https://www.sanko.ac.jp/fukuoka-med/`

`https://www.sanko.ac.jp/disclosure/chiba-med/` follows the reusable live
shape: group disclosure path plus school slug. The currently visible target
form entries remain latest-public FY2025 evidence, so they support RCA and
operator review but not strict FY2026 success.

## Verification

| Check | Result |
| --- | --- |
| Red test before implementation | `uv run pytest tests/unit/test_pdf_discovery.py::test_run_pdf_discovery_keeps_slug_disclosure_probe_for_shared_origin -q` -> failed with `downloaded=1` and `shared_origin_derived_fallback_skipped=2` |
| Focused slug-probe test after implementation | same focused command -> `1 passed` |
| Shared-origin regression checks | `uv run pytest tests/unit/test_pdf_discovery.py::test_run_pdf_discovery_keeps_slug_disclosure_probe_for_shared_origin tests/unit/test_pdf_discovery.py::test_run_pdf_discovery_shared_origin_cache_scales_to_many_school_paths -q` -> `2 passed` |
| Related shared-origin tests | `uv run pytest tests/unit/test_pdf_discovery.py::test_run_pdf_discovery_keeps_inverted_disclosure_probe_for_shared_origin tests/unit/test_pdf_discovery.py::test_run_pdf_discovery_keeps_slug_disclosure_probe_for_shared_origin tests/unit/test_pdf_discovery.py::test_run_pdf_discovery_keeps_host_specific_disclosure_probe_for_shared_origin -q` -> `3 passed` |
| Full PDF discovery unit suite | `uv run pytest tests/unit/test_pdf_discovery.py -q` -> `224 passed` |
| Ruff | `uv run ruff check src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py` -> pass |
| Mypy | `uv run mypy src/eidp/scraper/pdf_discovery.py` -> pass |
| Whitespace check | `git diff --check` -> pass |
| Build | `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v513.zip --latest-alias` -> wrote v513 ZIP and refreshed latest alias |
| Non-Windows release gate | `logs/win-v513-stage6-v513-non-windows-release-gates-20260520.json` -> `ok=true`, package/source fresh, full unit `1890 passed` |
| Core + OCR add-on verifier | `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v513.zip --ocr-addon dist/eidp-ocr-addon-windows-v497-smoke.zip --json` -> core `ok=true`, OCR add-on `ok=true` |

## Release Boundary

v513 is the latest package/source candidate. It has not completed Windows
side-by-side validation because the Windows OpenSSH/IP blocker is still
unresolved.

v502 remains the latest partial Windows side-by-side setup/canary package, and
v501 remains the latest complete Windows side-by-side smoke package.

v1.0 remains blocked until the FY2026/R8 strict-yield issue is resolved or the
`publication_lag` exception is explicitly approved, and until owner real-cycle
sign-off is returned.

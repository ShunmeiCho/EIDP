# v519 Vocational-Practice Basic-Info Filter Package

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
Package: `dist/eidp-windows-v519.zip`
Package source commit: `24fa09a49115196c2a977296eec127f6747e4426`
Package SHA256: `fbc2ae0016b7b293c0fd534d7b3e7eb881f74205fa6df19acda42a8d21ba195a`

## Scope

v519 is a Mac-side package rebuild after tightening PDF body classification for
vocational-practice basic-information PDFs. The FY2026/R8 strict-yield RCA
showed current-year URL hints such as `/2026/02/...pdf` on documents whose body
is actually `別紙様式4` / `職業実践専門課程等の基本情報について`, not the
institution-requirements confirmation application form.

Before this fix, incidental body text such as `高等教育の修学支援新制度` could
make those PDFs look like target-form candidates. v519 classifies any
`別紙様式4` / vocational-practice basic-info PDF body as `non_target`, so those
documents do not inflate target-form review buckets.

This improves manual-review hygiene. It does not create FY2026/R8 strict target
PDF success and does not remove the current release blocker.

## Evidence

- The regression test failed before the classifier change:
  `test_download_pdf_rejects_vocational_practice_basic_info_with_incidental_support_text`
  saved the PDF as accepted instead of `classified_non_target`.
- After the fix, the same test passes and the four local RCA sample PDFs in
  `_temp/fy2026-strict-proof-v485-20260519_065006/current-hint-target-samples/`
  classify as `non_target`.

## Verification

| Check | Result |
| --- | --- |
| Red test | `uv run pytest tests/unit/test_pdf_discovery.py::test_download_pdf_rejects_vocational_practice_basic_info_with_incidental_support_text -q` failed before the code change |
| Focused green tests | `uv run pytest tests/unit/test_pdf_discovery.py::test_download_pdf_rejects_vocational_practice_basic_info_with_incidental_support_text tests/unit/test_pdf_discovery.py::test_download_pdf_rejects_vocational_practice_basic_info_even_with_trusted_year tests/unit/test_pdf_discovery.py::test_download_pdf_rejects_url_target_hint_when_body_is_not_target_form -q` -> `3 passed` |
| PDF discovery unit suite | `uv run pytest tests/unit/test_pdf_discovery.py -q` -> `225 passed` |
| Ruff | `uv run ruff check src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py` -> `All checks passed!` |
| Local RCA sample probe | four `current-hint-target-samples/*.pdf` files now classify as `non_target` |
| Build | `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v519.zip --latest-alias` -> wrote v519 ZIP and refreshed latest alias |
| Core + OCR add-on verifier | `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v519.zip --ocr-addon dist/eidp-ocr-addon-windows-v497-smoke.zip --json` -> core `ok=true`, OCR add-on `ok=true` |
| Non-Windows release gate | `logs/win-v519-stage6-v519-non-windows-release-gates-20260520.json` -> `ok=true`, package/source fresh, full unit `1893 passed` |
| Post-docs-only release gate | `logs/win-v519-stage6-v519-post-docs-only-gates-20260520.json` -> `ok=true`, `docs_only_stale=true`, full unit `1893 passed` |

## Current Decision

v519 is the latest Mac-side package/source candidate. It includes all v518
package features plus the vocational-practice basic-info non-target filter.

v519 has not completed Windows side-by-side validation because the Windows
OpenSSH/IP blocker remains unresolved. v502 remains the latest partial Windows
side-by-side setup/canary package, and v501 remains the latest complete Windows
side-by-side smoke package.

Do not merge PR #2, tag v1.0, or request owner sign-off from v519 alone. The
release still requires either strict FY2026/R8 production-scale success or an
approved `publication_lag` exception plus owner real-cycle evidence verified by
`scripts/verify_stage6_return.py`.

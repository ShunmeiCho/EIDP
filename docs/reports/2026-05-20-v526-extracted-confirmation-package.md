# v526 Extracted Confirmation Package And Windows Smoke Evidence

Date: 2026-05-20
Package: `dist/eidp-windows-v526.zip`
Package SHA256: `4a03e975243d1327e79470de82fe468814c42a66e2749ec32c3251176da9ebca`
Source commit: `5b30eb78edc331f992c1a99fdc7611174791ab87`

## Scope

v526 includes all v525 package evidence and adds the operator flow for
confirming or supplementing already extracted PDFs.

- `school_year_tasks` now shows `抽出済内容を確認・補足` for extracted
  `confirmed_target` rows with `parsed` or `manual_entered` extraction status
  and a `latest_document_id`.
- The existing PDF確認・手入力 page is reused through the existing
  `manual_entry_prefill_for_row` document prefill.
- The manual-entry form preloads current `DepartmentYearly`,
  `Department`, and `SupportRecipient` values for the selected document and
  fiscal year.
- `ingested` documents are save-eligible in the manual-entry page so operator
  confirmation/supplement saves continue through the existing append-only
  manual-entry path and `ManualActionLog` coverage.
- No schema migration or `operator_confirmed` flag is introduced in v526.

This is not v1.0 GA approval. FY2026/R8 strict yield and owner sign-off remain
blocked.

## Mac / Package Evidence

| Check | Evidence |
| --- | --- |
| Build | `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v526.zip --latest-alias` |
| SHA256 | `shasum -a 256 -c dist/eidp-windows-v526.zip.sha256` -> OK |
| Core + OCR verifier | `logs/win-v526-stage6-v526-verify-windows-distribution-with-ocr-addon-20260520.json` -> core `ok=true`, OCR add-on `ok=true` |
| Non-Windows release gate | `logs/win-v526-stage6-v526-non-windows-release-gates-20260520.json` -> `ok=true`, package/source fresh, full unit `1901 passed` |
| Package source check | package commit and source commit both `5b30eb78edc331f992c1a99fdc7611174791ab87`, `source_dirty=false`, `stale=false` |
| Focused UI/manual-entry tests | `uv run pytest tests/unit/test_review_school_year_tasks.py tests/unit/test_review_pdf_manual_entry.py tests/unit/test_manual_entry_contract.py tests/unit/test_review_ui_lock_disable_contract.py tests/unit/test_operator_pages.py -q` -> `168 passed` |
| Ruff / mypy focused slice | `ruff` and `mypy` passed for the touched review modules and tests |

## Windows Side-By-Side Evidence

Windows root: `C:\Users\cyo20\EIDP-v526-5b30eb7-env0`

| Check | Evidence |
| --- | --- |
| Setup summary | `logs/win-v526-stage6-v526-setup-summary-20260520.json` -> `ok=true`, setup/validate/OCR/recovery rc all `0` |
| Setup validator | `logs/win-v526-stage6-v526-env0-validate-after-setup-20260520.json` -> `ok=true`, `school_count=2418`, `school_fiscal_year_status_count=2418`, SQLite integrity `ok`, build commit `5b30eb78edc331f992c1a99fdc7611174791ab87` |
| OCR runtime | `logs/win-v526-stage6-v526-env0-validate-ocr-runtime-20260520.json` -> `ok=true`, Tesseract `5.4.0.20240606`, `jpn` and `jpn_vert` present |
| UI smoke | `logs/win-v526-stage6-v526-ui-smoke-20260520.json` -> `ok=true`, port `8526`, health `200/ok`, root `200`, no traceback, listener stopped |
| Extracted supplement helper smoke | Windows package import smoke confirmed the extracted-row CTA label, document prefill, and `ingested` save eligibility |
| Weekly canary | `logs/win-v526-stage6-v526-weekly-canary-limit50-summary-20260520.json` -> `ok=true`, weekly rc `0`, validate-after-weekly rc `0`, recovery rc `0` |
| Last run | `logs/win-v526-stage6-v526-last-run-after-weekly-canary-limit50-20260520.json` -> `status=success`, `current_fy=2026`, strict `5/50 (10.0%)`, operator-reviewable `50/50 (100.0%)`, `ship_gate_status=below_gate` |
| Discovery / ingest stats | v526 limit-50 canary crawled `59` site rows, found `50` candidates, downloaded `5`, failed `1`, processed `5` documents into `106` departments and `107` yearly rows |
| Excel smoke | `logs/win-v526-stage6-v526-excel-summary-20260520.json` -> `ok=true`, master workbook, competition workbook, and gap report generated |
| Stage 6 recovery | `logs/stage6-recovery-20260520-v526.json` -> `ok=true`, active task matches expected v485 weekly action |
| Residual cleanup | `logs/stage6-residual-cleanup-20260520-v526.json` -> dry run `ok=true`, `existing_count=0`, `moved_count=0` |
| Stage 6 bundle | `logs/stage6-evidence-20260520-091540.zip`, SHA256 `1e7efcb1bdbac6c88d3b38f2b209655fc022518ddaeefa07c2b15fc57c2f2283` |
| Stage 6 verifier | `logs/stage6-evidence-verify-local-v526-20260520.json` -> `ok=true`, required labels present, no unsafe or forbidden entries |

## Release Boundary

v526 supersedes v525 as the latest package/source and complete Windows
side-by-side smoke package. It preserves the same business blocker:

- FY2026/R8 strict current-year target PDF yield remains `5/50 (10.0%)`,
  below the 60% release line.
- Owner real-cycle evidence and sign-off are still missing.
- `docs/reports/2026-05-19-publication-lag-release-exception-record.md` remains
  `NOT_APPROVED`.

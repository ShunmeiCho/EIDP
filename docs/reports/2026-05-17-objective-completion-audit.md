# 2026-05-17 Objective Completion Audit

Status: **not complete**

This audit maps the current EIDP objective to concrete artifacts and evidence.
It is intentionally stricter than unit-test or package-verifier success: proxy
signals do not count as completion unless they cover the release requirement.

## Objective Restatement

EIDP must let one Windows operator handle 1,700+ Japanese vocational schools
each rolling fiscal year by:

1. discovering school public URLs from the 47 prefectural official lists,
2. finding and downloading only the current target-FY institution-confirmation
   PDF in strict mode,
3. extracting department/support-recipient rows with pdfplumber, PyMuPDF, and
   Tesseract/OCR fallback while enforcing confidence >= 0.70,
4. writing accepted rows append-only into SQLite,
5. exporting/transcribing to the Excel template,
6. preserving all operator actions in audit logs,
7. distributing as an offline Windows ZIP with double-click setup and browser UI,
8. proving the ship line: 60-70% true target-PDF auto-acquisition and manual
   workload <=30%, or an explicitly approved publication-lag exception backed
   by mature-year evidence.

## Prompt-To-Artifact Checklist

| Requirement | Current Artifact / Evidence | Status |
| --- | --- | --- |
| 47-prefecture official-list URL discovery | Existing bootstrap/discovery pipeline; current-source local changes preserve target-FY override and URL discovery. Clean CI simulation recorded in `docs/reports/2026-05-17-local-change-readiness.md`. | Partial: implemented, but final active-lane owner proof still missing. |
| Strict current target-FY PDF discovery; stale-year fallback excluded from成果 | `src/eidp/scraper/pdf_discovery.py`, strict gold-set tests, and current-source shared-origin cache fix. The current `logs/release-gate-current-source-retroactive-matrix-20260517.json` is Excel business-value proof only, not mature-year PDF discovery/yield proof. `docs/reports/2026-05-17-mature-year-acquisition-proof-audit.md` records that existing FY2025 bounded artifacts and a current-source FY2025 limit-20 execution smoke were correctly rejected as release proof. | Partial: discovery code is guarded and current source can execute a small R7 smoke, but mature-year production-scale target-PDF acquisition proof and current R8 live yield remain missing. |
| Extraction confidence >=0.70 and append-only writes | Existing ingest/confidence tests plus target-FY override tests; latest targeted evidence recorded as `63 passed` in local readiness report. | Partial: covered by tests, but not by final owner-cycle evidence. |
| Excel template output | Historical R7 browser Excel and retroactive matrix evidence recorded in `docs/reports/current-release-status.md` and `docs/reports/2026-05-17-current-source-retroactive-matrix.md`. | Partial: Excel proof exists; final active owner-cycle Excel preview/download still missing. |
| ManualActionLog / outbox audit of operator actions | Existing UI/audit sandbox evidence in `docs/reports/current-release-status.md`. | Partial: sandbox evidence only; real final owner/operator audit/outbox delta missing. |
| Offline Windows ZIP, double-click setup, browser UI | Diagnostic v466/current-source ZIP builds pass all checks except dirty-build protection; clean CI simulation passes release gate with SHA256 `cdcd9832e64d182b06287fa9ef42af43b99eb63b6574734759833d7d61521cf0`. | Partial: local clean simulation proven; remote PR is still old red and no clean release package has been pushed from these changes. |
| No tester username or local path leak into operator ZIP | `scripts/build_windows_zip.py` packages only current operator docs; `scripts/verify_windows_distribution.py` rejects historical runbooks and real local user path tokens; clean ZIP scan found 0 offenders for `<operator-user>`, `<developer-user>`, `C:\Users\<operator-user>`, `C:/Users/<operator-user>`, `/Users/<developer-user>`. | Covered for operator ZIP; repo-public historical docs use privacy placeholders rather than runtime input. |
| Ship gate 60-70% auto-yield / manual workload <=30% | `scripts/ship_gate_contract.py` defines `publication_lag`; `scripts/build_mature_year_acquisition_proof.py` can build proof JSON from mature-year weekly `last_run.json`; `scripts/verify_stage6_return.py` accepts measured threshold miss only with explicit exception and a mature-year proof whose basis is `mature_year_retroactive_operator_reviewable_acquisition`. It rejects Excel-only proof, null KPI, and mature-year proof with denominator below `1000`. | Partial: proof format/tooling is now stricter, but real mature-year production-scale acquisition proof, final owner sign-off, and measured evidence are still missing. |
| CI quality gate green | Local candidate fixes the CI root cause by adding `pip>=24.0`; local ruff/mypy/Bandit/full pytest/clean release-gate simulation pass. | Missing: GitHub PR #2 still points at commit `364f25a4fd95e1b7c85ace76e635c7a77954d583` with two failed CI checks. |
| Active lane usable for owner cycle | v465 promotion runbook exists and v465 source/cache fix is proven. | Missing: no approved Windows active-lane swap performed. |
| Final Stage 6 release evidence | `verify_stage6_return.py` requires successful `last_run`, labels, measured KPI, release rows, and sign-off. | Missing: no final owner/operator cycle, final `last_run`, evidence ZIP, audit/outbox delta, or sign-off. |

## Current Blockers

1. Remote GitHub CI is still red because the fixed local worktree has not been
   committed and pushed. The old remote head still fails in the Windows ZIP
   build path.
2. A clean, pushed release candidate package is not yet available; diagnostic
   local ZIPs are intentionally dirty and therefore rejected by the verifier.
3. The active Windows owner lane has not been promoted from v460 to the fixed
   current-source/v465+ lane.
4. The owner/operator real cycle has not been completed on the approved lane.
5. Final release artifacts are missing: successful `last_run.json`, verified
   Stage 6 evidence ZIP, KPI rows, audit/outbox delta, owner sign-off, and
   operator sign-off.

## Next Concrete Actions

1. With explicit approval, split the dirty worktree by the existing commit plan
   and push the CI/package fixes so PR #2 gets a fresh GitHub CI run.
2. After CI is green, build a clean release-candidate ZIP from the pushed commit
   and verify it with `scripts/verify_windows_distribution.py`.
3. Promote the fixed Windows lane side-by-side, keeping v460 as fallback.
4. Run the owner/operator real cycle and collect/verify Stage 6 return evidence.

Do not mark the active goal complete until all missing items above are backed by
fresh evidence.

# EIDP v460 Stage 6 Evidence Draft

Updated: 2026-05-17

This draft records the current v460 Mac/non-Windows gate and Windows setup
staging. It is not the final Stage 6 operator-PC real-cycle sign-off.

## Package

| Item | Evidence |
| --- | --- |
| Package | `dist/eidp-windows-v460.zip` |
| SHA256 | `ce5fa49b8c30900a33b31fd317c6846ffe5839053f2bdd1ffdeb8cca2113129c` |
| BUILD_INFO commit | `01e44279238aaef9127ed9b578e29dc8e0070499` |
| Windows root | `C:\Users\cyo20\EIDP-v460-01e4427` |
| Release gate | `logs/release-gate-v460.json`, `ok=true` |
| Companion docs | `dist/eidp-v460-operator-docs-20260516.zip`; verify with `dist/eidp-v460-operator-docs-20260516.zip.sha256` |
| Windows staging docs companion | `C:\EIDP-staging\eidp-v460-operator-docs-20260516.zip`; Windows `Get-FileHash` matched the sidecar |
| Windows staging docs directory | `C:\EIDP-staging\v460-operator-docs` with `00-READ-ME-FIRST.txt` |
| Top-level README source | `docs/runbooks/00-READ-ME-FIRST-v460.txt`; SHA256 `047ae62bce4c8b419630dff777973a0cd5c285ecd01d2d4b69601f0d6fa9e8b7` |

The v460 core ZIP includes the current version-neutral E2E template. The
companion docs ZIP carries this version-specific evidence draft, real-cycle card,
and release-status snapshot. The top-level staging readme is
`C:\EIDP-staging\00-READ-ME-FIRST-v460.txt`; it is mirrored in git as
`docs/runbooks/00-READ-ME-FIRST-v460.txt` with the same SHA256 recorded in the
handoff manifest.

## Mac / Non-Windows Gate

| Check | Result |
| --- | --- |
| Source/package freshness | `package_commit=source_commit=01e44279238aaef9127ed9b578e29dc8e0070499`, `source_dirty=false`, `stale=false` |
| SHA256 sidecar | matched `ce5fa49b8c30900a33b31fd317c6846ffe5839053f2bdd1ffdeb8cca2113129c` |
| Full unit | `1665 passed`, 5 PyMuPDF/import warnings |
| Validator distribution unit | `166 passed` |
| Validator mypy/Ruff | passed |
| Discovery gold summary | 44 entries, no undemonstrated pattern sources |
| Expected predictions | `exact_matches=44`, `failed_predictions=0` |
| Package verifier | passed |
| Demonstrated-pattern package verifier | passed |

## Mac Algorithm Regression Support

| Check | Result |
| --- | --- |
| v463 retroactive Excel matrix | `logs/release-gate-v463-retroactive-matrix.json` returned `ok=true`, `case_count=3` |
| FY2025 reference diff | `logs/release-gate-v463-retroactive-fy2025-reference.json` returned `ok=true`; reference `_temp/v459-reference2-fy2025/output/retroactive-fy2025-v459-reference.xlsx`; `missing_rows=0`, `extra_rows=0`, `differing_fields=0` |
| FY2024 reference diff | `logs/release-gate-v463-retroactive-fy2024-reference.json` returned `ok=true`; reference `_temp/v459-reference2-fy2024/output/retroactive-fy2024-v459-reference.xlsx`; `missing_rows=0`, `extra_rows=0`, `differing_fields=0` |
| FY2023 reference diff | `logs/release-gate-v463-retroactive-fy2023-reference.json` returned `ok=true`; reference `_temp/v459-reference2-fy2023/output/retroactive-fy2023-v459-reference.xlsx`; `missing_rows=0`, `extra_rows=0`, `differing_fields=0` |

These v463 checks prove the current Mac package lane still reproduces the
historical Excel business values for FY2025/FY2024/FY2023 when compared against
references regenerated from the frozen v459 package. The earlier raw
`data/master.xlsx` comparison attempt is not valid evidence because that workbook
contains later-year fields and is not a FY-specific pass/fail reference. This is
algorithm regression evidence only; it does not replace the v460 owner/operator
real-cycle, evidence ZIP sign-off, or FY2026/R8 live KPI record.

## Windows Setup Staging

| Check | Result |
| --- | --- |
| Transfer SHA | Win `Get-FileHash` matched the sidecar SHA256 |
| Extraction | `C:\Users\cyo20\EIDP-v460-01e4427` |
| Setup | `EIDP-setup.bat` exited `0`; `sqlite_integrity_check=ok`; `school_count=2418`; `school_fiscal_year_status_count=2418`; `wheel_count=78` |
| Setup validator | `scripts\validate_install.bat --after-setup --json` returned `ok=true` |
| Recovery check | `scripts\stage6_recovery_check.bat C:\Users\cyo20\EIDP-v460-01e4427\scripts\weekly_run.bat --json` returned `ok=true`, `action_matches_expected=true` |
| Task Scheduler | `EIDP Weekly Run` now executes `"C:\Users\cyo20\EIDP-v460-01e4427\scripts\weekly_run.bat"` |
| Diagnostics | `C:\Users\cyo20\EIDP-v460-01e4427\logs\diagnostics-20260516-170035.txt`; Mac copy `logs/win-v460-stage6/diagnostics-20260516-170035.txt` |
| Mac copy SHA256 | diagnostics `6b4d566433db64c730737f925f0559e9b06582eed4cb0b6cd51f0623f153b445`; recovery JSON `41dd47aee0a304371cab5633397017f45e4f1a1d090b186986d48c49cf38acf6` |
| UI health / read-only nav | Direct Streamlit launch served Windows `127.0.0.1:8501/_stcore/health=ok`; Mac tunnel `127.0.0.1:18506` returned health `ok`; browser smoke wrote `output/playwright/v460-ui-smoke/summary.json` with `hasV460Build=true`, `hasJapaneseUi=true`, `hasTargetFiscalYear=true`, `hasErrorTraceback=false`, and `navAllClicked=true` |
| Diagnostic evidence-bundle guard | `EIDP-stage6-evidence.bat` created `C:\Users\cyo20\EIDP-v460-01e4427\logs\stage6-evidence-20260516-082906.zip`, but `EIDP-stage6-verify-evidence.bat` correctly returned `ok=false`, `missing_required_labels=["last_run"]`; Mac copy SHA256: ZIP `35b2042dbd50c1fd5156975876d5c35eca97c80ad1f42ab327852eef4c621f29`, verify JSON `d774b02dd31e0b71d0531f0577b9f452a1f4ca9a85bff8cad8b3fd36230a19a9` |
| Plan A CLI weekly | `scripts\weekly_run.bat` exited `0` on `2026-05-16T18:43:45`; `data\output\last_run.json` has `status=success`, `dry_run=false`, `current_fy=2026`, `no_crawlable_url_school_count=2418`, `target_missing_school_count=0`, `target_pdf_auto_yield_pct=null`, `operator_reviewable_yield_pct=null`, and `ship_gate_status=not_measured` |
| Plan A evidence bundle | `C:\Users\cyo20\EIDP-v460-01e4427\logs\stage6-evidence-20260516-094432.zip`; verifier `ok=true`, `missing_required_labels=[]`, labels `build_info`, `diagnostics`, `last_run`, `stage6_recovery`, `weekly_run_logs`; Mac copy `logs/win-v460-plan-a/stage6-evidence-20260516-094432.zip` SHA256 `491129595c97191069708ec47386663d62321fb5ead35a827e6acbfd6aaf7e0e` |
| Plan A URL bootstrap | Before the second run, a backup was written at `data\backups\plan-a\eidp-before-url-bootstrap-20260516-184839.sqlite3`; bootstrap log `logs\bootstrap-pdfs-20260516-184850.log` recorded `seed_urls_imported imported=48`, `corporation_urls_inferred=296`, `search_found=180`, and produced DB counts `school_count=2418`, `school_site_count=1838`, `schools_with_url=1805`, `schools_with_verified_url=1312`, `document_count=0`, `crawl_job_count=0` |
| Plan A second FY2026 weekly after URL bootstrap | Started at `2026-05-16 19:24:43` JST and was stopped at `2026-05-17 05:06` JST after about 9h41m without writing a new summary or `last_run.json`; it generated `data\output\target-year-discovery\20260516_102444-discovery-rejections.jsonl` with `234238` lines / `101997049` bytes and left `Document=0`, `CrawlJob=0`; repeated-domain counts in the log included O-Hara `robots.txt=152`, O-Hara `sitemap.xml=52`, O-Hara `about/joho/=283`, Sanko `robots.txt=136`, and Jikei `post-sitemap2/3=16/16` |

Plan A proved that the v460 CLI weekly runner can create a `last_run` and a
verifier-accepted evidence ZIP, but it did not prove the shipping KPI. The run
selected no schools because the fresh v460 DB had `2418` schools with no
crawlable URL, so `ship_gate_status=not_measured` and `ship_readiness_rc=1`.
No v460 write-path browser flow or owner/operator real-cycle was executed. The
v460 browser smoke was read-only: it did not generate a workbook, save settings,
or commit operator writes.

The second Plan A run is not release evidence and does not replace the first
verifier-accepted evidence bundle. It is useful as a production-scale probe: the
strict FY2026/R8 filters rejected large numbers of non-target PDFs, but the run
also exposed a v1.1 performance issue where corporation domains are re-crawled
per school instead of being cached or de-duplicated at run scope.

## Disk State

| Environment | Result |
| --- | --- |
| Mac dev | `ok=true`, `warn_count=0`, `block_count=0`, project `1.7GiB`, `dist=738.8MiB`, `_temp=0B`, `logs=4.3MiB`, protected `data=20.0MiB` |
| Win v460 root | `ok=true`, `warn_count=0`, `block_count=0`, app root `843.0MiB`, `data\pdfs=0B`, `data\output=0B`, `logs=10.6KiB` |
| Retention | Mac and Win staging retain v460 current plus v459 fallback; stale v454 package/deploy artifacts were pruned |

## Open Gates

- The real operator-PC one-cycle sign-off remains open.
- FY2026/R8 live yield is record-only during the May publication-lag window; it
  is not the v1.0 algorithm-proof gate. Plan A returned
  `target_pdf_auto_yield_pct=null`, and the second post-bootstrap run did not
  complete.
- Operator workload `<=30%` remains open; Plan A diagnostics reported
  `estimated_manual_workload_rate=1.0`.
- Production-scale weekly performance on URL-rich DBs remains open; the second
  post-bootstrap run exposed repeated corporation-domain recrawls.
- v459 browser navigation, R7 browser Excel, and UI write/audit sandbox evidence
  remain historical bounded support, not v460 real-cycle sign-off.

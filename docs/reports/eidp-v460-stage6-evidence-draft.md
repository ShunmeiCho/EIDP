# EIDP v460 Stage 6 Evidence Draft

Updated: 2026-05-16

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

No v460 weekly run, write-path browser flow, verifier-accepted evidence bundle,
or owner/operator real-cycle was executed during this staging update. The v460
browser smoke was read-only: it did not run weekly collection, generate a
workbook, save settings, or commit operator writes. The diagnostic evidence ZIP
is intentionally not release evidence because `last_run` is missing.

## Disk State

| Environment | Result |
| --- | --- |
| Mac dev | `ok=true`, `warn_count=0`, `block_count=0`, project `1.7GiB`, `dist=738.8MiB`, `_temp=0B`, `logs=4.3MiB`, protected `data=20.0MiB` |
| Win v460 root | `ok=true`, `warn_count=0`, `block_count=0`, app root `843.0MiB`, `data\pdfs=0B`, `data\output=0B`, `logs=10.6KiB` |
| Retention | Mac and Win staging retain v460 current plus v459 fallback; stale v454 package/deploy artifacts were pruned |

## Open Gates

- The real operator-PC one-cycle sign-off remains open.
- FY2026/R8 production strict target-PDF auto-yield remains open.
- Operator workload `<=30%` remains open until a real cycle is measured.
- v459 browser navigation, R7 browser Excel, and UI write/audit sandbox evidence
  remain historical bounded support, not v460 real-cycle sign-off.

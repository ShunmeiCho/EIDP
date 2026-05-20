# v526 Post-Reboot Active Task Preflight

Date: 2026-05-20

## Scope

This is a post-reboot Windows preflight check for the v526 handoff state. It
does not approve release, does not switch the active Scheduled Task, and does
not replace the missing owner real-cycle evidence.

The check was run after SSH to the Windows host was restored. It verifies that
the v526 staging/package files remain intact, that the active weekly task has
not been accidentally promoted to v526, and that the active v485 task state is
not mistaken for v526 release evidence.

## Findings

| Check | Result |
| --- | --- |
| Windows host | `ssh win hostname` returned `junming` |
| v526 package hash on Windows | `C:\EIDP-staging\eidp-windows-v526.zip` SHA256 `4a03e975243d1327e79470de82fe468814c42a66e2749ec32c3251176da9ebca`; sidecar matched |
| OCR add-on hash on Windows | `C:\EIDP-staging\eidp-ocr-addon-windows-v497-smoke.zip` SHA256 `3d0d03d4b49eb1bf5d8acc2030c00189702519d01ac80886bb7507a1d619450f`; sidecar matched |
| v526 owner docs ZIP hash on Windows | `C:\EIDP-staging\eidp-v526-owner-docs-20260520.zip` SHA256 `01b88191e5ee6c6e37ef8f9ad6223594a6f26c7d1e7b5a8ae5b49a0750d87af2` |
| v526 extracted root | `C:\Users\cyo20\EIDP-v526-5b30eb7-env0` present |
| Active Scheduled Task action | `C:\Users\cyo20\EIDP-v485-70e3db4\scripts\weekly_run.bat` |
| Active Scheduled Task state | Ready/enabled, next run `2026-05-25 02:00`, missed runs `0` |
| Active Scheduled Task last result | `1` from the historical `2026-05-18 02:00` run |
| v526 recovery check with active-v485 expected action | `ok=true`, `action_matches_expected=true`, `lock_probe.held=false`, rc `0` |
| v485 recovery check with active-v485 expected action | `ok=true`, `action_matches_expected=true`, `lock_probe.held=false`, rc `0` |
| Active v485 latest weekly log | `logs\run-20260519.log` failed with `ImportError: cannot import name 'func' from 'sqlalchemy'` and `rc=1` |
| Active v485 `last_run.json` | missing |

## Interpretation

The active Scheduled Task was not accidentally promoted to v526. This preserves
the side-by-side safety boundary.

However, the active v485 lane is not healthy release evidence: its latest
weekly log fails before discovery with a SQLAlchemy import error, and no
`data\output\last_run.json` is present. Therefore active-task preservation
should be read only as "no accidental promotion", not as proof that v485 can
run the current workflow.

The selected v526 candidate remains the only current package/source and Windows
side-by-side smoke candidate. It still requires an explicit release decision
before owner sign-off:

- strict FY2026/R8 path: wait for current-year strict yield to reach the release
  line;
- `publication_lag` exception path: approve the exception record and then run
  the owner real cycle on the selected v526 side-by-side lane.

Do not use the active v485 Scheduled Task as v1.0 proof.

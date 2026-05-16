# EIDP v448 Stage 6 Evidence Draft

Updated: 2026-05-16

This draft records the v448 Windows setup, disk-health, and artifact-retention
evidence. It is not a completed operator real-cycle Stage 6 sign-off. v447
remains the latest bounded weekly, evidence-bundle, and UI-health proof.

## Package

| Item | Value |
| --- | --- |
| ZIP | `dist/eidp-windows-v448.zip` |
| SHA256 | `5306b983debe3aee743869d64ded5557eacb4ab70042e5e6862cdbf3a5a9a09e` |
| Package snapshot | `639dbbbac5b1b957bb30e419d84f909b683aedec` |
| Windows deploy path | `C:\Users\cyo20\EIDP-v448-639dbbb` |
| Non-Windows gate | `logs/release-gate-v448.json` |

## Evidence

| Check | Result | Notes |
| --- | --- | --- |
| Non-Windows release gate | pass | `logs/release-gate-v448.json` returned `ok=true`, package/source commit match, SHA sidecar match, validator/distribution tests `164 passed`, mypy/Ruff pass, discovery-gold predictions `44/44`, and both package verifier modes passed. |
| Windows transfer + SHA | pass | `dist/eidp-windows-v448.zip` and sidecar were copied to `C:\EIDP-staging`; `Get-FileHash` matched `5306b983debe3aee743869d64ded5557eacb4ab70042e5e6862cdbf3a5a9a09e`. |
| Windows extract | pass | Expanded to `C:\Users\cyo20\EIDP-v448-639dbbb`; `BUILD_INFO.json` reports commit `639dbbbac5b1b957bb30e419d84f909b683aedec`, `git_dirty=false`, and `scripts\disk_health_check.py` exists. |
| Setup | pass | `EIDP-setup.bat` completed; `scripts\validate_install.bat --after-setup --json` returned `ok=true`, `school_count=2418`, `school_fiscal_year_status_count=2418`, and `sqlite_integrity_check=ok`. |
| Operator disk health | pass | `scripts\disk_health_check.py --profile operator-win --json` returned `ok=true` after setup with `app_root_total=843.0MiB`, `data\pdfs=0B`, `data\output=0B`, `logs=3.8KiB`, and no warn/block entries. |
| Windows retention prune | pass | v448 packaged pruner dry-run found only v447 staging/deploy candidates; `--apply` deleted v447 ZIP, sidecar, and `EIDP-v447-55cbc1b`, freeing `1104022134` bytes while keeping v448 current plus v442 fallback. |
| Mac disk health | pass | Mac pruning deleted v446/v447 ZIPs and sidecars, freeing `422489392` bytes. `scripts\disk_health_check.py --profile mac-dev --json` returned `ok=true`, `project_total=1.7GiB`, `dist=738.7MiB`, `_temp=0B`, `logs=3.4MiB`, and protected `data=20.0MiB`. |

## Boundary

v448 has not yet run URL-only bootstrap, bounded `weekly_run.bat`, UI health,
or Stage 6 evidence-bundle collection. Those latest proofs remain on v447. The
ship gate remains incomplete because the operator real-cycle sign-off is missing
and the latest bounded strict target PDF auto-yield is still `0.0%`.

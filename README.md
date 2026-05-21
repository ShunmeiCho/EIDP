# EIDP

Education Institution Data Pipeline

EIDP automates collection, review, and Excel export of Japanese vocational
school disclosure data. Sprint 8 targets a one-operator Windows PC deployment:
extract a ZIP, double-click root-level `.bat` launchers, and operate through
the Streamlit UI.

## For Operators

Use the Windows runbook:

- [EIDP Windows 運用ランブック](docs/runbooks/eidp-windows.md)

Normal workflow:

1. Extract `eidp-windows.zip` to `C:\EIDP`.
2. Run `C:\EIDP\EIDP-setup.bat` once.
3. Run `C:\EIDP\EIDP-start.bat` to open the UI.
4. Review PDFs, manual-entry items, fiscal-year corrections, Excel preview, and audit logs
   in the Streamlit sidebar.
5. Let `weekly_run.bat` run by Windows Task Scheduler, or run it manually when
   instructed.
6. If setup, startup, or URL/PDF acquisition fails, run
   `C:\EIDP\EIDP-diagnose.bat` and share the generated `logs\diagnostics-*.txt`
   with the administrator.

Optional OCR:

- Extract `eidp-ocr-addon-windows.zip` into `C:\EIDP`.
- Confirm `ocr-addon\tesseract\tesseract.exe` and
  `ocr-addon\tessdata\jpn.traineddata` exist.
- Restart EIDP with `EIDP-start.bat`.

Optional Playwright/Chromium:

- Not required for normal v1.0 operation.
- Distributed separately if JavaScript-heavy school sites require it.

## For Developers

Architecture and planning:

- [Architecture](docs/architecture.md)
- [Sprint 8 release gate audit](docs/plans/2026-05-05-sprint8-release-gate-audit.md)
- [Sprint 8 handoff](docs/plans/2026-05-05-sprint8-handoff.md)
- [Future v2 roadmap](docs/plans/future-v2-roadmap.md)
- [Future natural-language query note](docs/plans/future-natural-language-query.md)

Install development dependencies:

```bash
uv sync --extra dev
```

Common checks:

```bash
uv run pytest tests/unit -q
uv run ruff check .
uv run mypy src
uv run python scripts/check_windows_paths.py
```

Windows packaging is built from macOS/Linux but must be validated on Windows:

```bash
uv run python scripts/download_windows_runtime.py
uv run python scripts/build_windows_zip.py
```

Before moving ZIPs to the Windows VM, run the distribution verifier and keep
the JSON with the ZIPs on the internal file server:

```bash
uv run python scripts/verify_windows_distribution.py dist/eidp-windows.zip \
  --ocr-addon dist/eidp-ocr-addon-windows.zip \
  --playwright-addon dist/eidp-playwright-addon-windows.zip \
  --json > dist/windows-distribution-verification.json
```

Optional add-on packagers:

```bash
uv run python scripts/build_ocr_addon_zip.py --tesseract-dir <dir> --tessdata-dir <dir>
uv run python scripts/build_playwright_addon_zip.py --wheelhouse <dir> --browsers-dir <dir>
```

Mac-side tests prove business logic and package shape only. Windows VM offline
validation remains the deployment gate. Use:

- [Windows VM validation checklist](docs/runbooks/eidp-windows-vm-validation.md)
- `scripts\validate_install.bat` after setup and weekly run
- [Operator PC E2E template](docs/runbooks/eidp-operator-e2e-template.md) for
  the real-PC Stage 6 cycle

VM / real-PC validation must cover:

- `EIDP-setup.bat`
- `EIDP-start.bat`
- `first_setup.bat`
- `launch.bat`
- `weekly_run.bat`
- SQLite file locking
- Excel output and file-lock error handling
- OCR add-on execution
- Defender / SmartScreen behavior

## Deployment Status

Venus cron/systemd operation is archived, not live:

- legacy assets: `deploy/legacy-venus/`
- archived runbook: [legacy target-year rediscovery runbook](docs/runbooks/eidp-r8-rediscovery.md)

The active deployment target is Windows PC.

@echo off
REM Sprint 8.5.a — first-run setup for the Windows operator PC.
REM Sprint 8.5.a.1 — fixed venv creation, fixed CLI command name, removed
REM use of `uv pip install` against the wheelhouse without a target env.
REM
REM Resolves the application root from the script location, pins it via
REM EIDP_APP_ROOT, creates an isolated .venv from the bundled
REM python-build-standalone runtime, installs from the bundled
REM wheelhouse with no network, bootstraps the SQLite database, imports
REM the master school list (if present), and registers the weekly Task
REM Scheduler entry.

setlocal EnableExtensions EnableDelayedExpansion

REM 1. Anchor at the application root regardless of who invoked us.
cd /d "%~dp0\.."
set "EIDP_APP_ROOT=%CD%"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
set "PYTHONPATH=%EIDP_APP_ROOT%\src;%PYTHONPATH%"

REM 2. Make sure data/, logs/, output/ exist before any tool writes.
if not exist "data"        mkdir "data"
if not exist "data\pdfs"   mkdir "data\pdfs"
if not exist "data\output" mkdir "data\output"
if not exist "data\audit"  mkdir "data\audit"
if not exist "logs"        mkdir "logs"

REM 3. Prevent two setup runs from clearing .venv at the same time.
REM    If setup crashed and left a lock behind, recover it after a short
REM    TTL so non-technical operators do not have to delete hidden folders.
set "SETUP_LOCK_DIR=%EIDP_APP_ROOT%\.setup.lock"
set "SETUP_LOCK_STALE_HOURS=2"
if exist "%SETUP_LOCK_DIR%" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $p=$env:SETUP_LOCK_DIR; if (Test-Path -LiteralPath $p) { $age=(Get-Date)-(Get-Item -LiteralPath $p).LastWriteTime; if ($age.TotalHours -ge [double]$env:SETUP_LOCK_STALE_HOURS) { Remove-Item -LiteralPath $p -Recurse -Force; exit 0 }; exit 1 }; exit 0"
    if not errorlevel 1 echo [first_setup] Removed stale setup lock older than %SETUP_LOCK_STALE_HOURS% hours.
)
mkdir "%SETUP_LOCK_DIR%" 2>nul
if errorlevel 1 (
    echo [first_setup] ERROR: setup is already running in this folder.
    echo [first_setup] Wait until the other setup window finishes, then run setup again.
    endlocal & exit /b 4
)
set "SETUP_RC=0"

REM 4. Use the bundled python-build-standalone runtime so we never
REM    depend on whatever Python the operator might have installed.
set "RUNTIME_PY=%EIDP_APP_ROOT%\runtime\python\python.exe"
set "OFFLINE_PIP=%EIDP_APP_ROOT%\scripts\offline_pip_install.py"
set "VENV_SITE_PACKAGES=%EIDP_APP_ROOT%\.venv\Lib\site-packages"
if not exist "%RUNTIME_PY%" (
    echo [first_setup] ERROR: runtime\python\python.exe is missing. Re-extract the ZIP.
    set "SETUP_RC=2"
    goto :finish
)
if not exist "%OFFLINE_PIP%" (
    echo [first_setup] ERROR: scripts\offline_pip_install.py is missing. Re-extract the ZIP.
    set "SETUP_RC=2"
    goto :finish
)

REM 5. Create an isolated venv if needed. Use the stdlib venv module rather
REM    than `uv venv`: live operator-PC v394 probing showed `uv venv` can
REM    hang while checking the bundled Python interpreter, while
REM    `python -m venv --without-pip` returns immediately. Dependencies are
REM    installed into .venv\Lib\site-packages by scripts\offline_pip_install.py,
REM    which runs under the bundled runtime Python and avoids pip's Windows
REM    WMI truststore hang. Do not clear an existing venv: Windows may keep
REM    .venv\Scripts files locked while the UI is still running. Dependency
REM    refresh happens through the offline install steps.
set "VENV_PY=%EIDP_APP_ROOT%\.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
    "%RUNTIME_PY%" -m venv --without-pip ".venv"
    if errorlevel 1 (
        echo [first_setup] stdlib venv creation failed
        set "SETUP_RC=1"
        goto :finish
    )
)
if not exist "%VENV_PY%" (
    echo [first_setup] venv python missing after creation
    set "SETUP_RC=1"
    goto :finish
)

REM 6. Offline install from the bundled wheelhouse into the venv.
"%RUNTIME_PY%" "%OFFLINE_PIP%" install ^
    --target "%VENV_SITE_PACKAGES%" ^
    --no-index ^
    --find-links "%EIDP_APP_ROOT%\wheelhouse" ^
    --upgrade ^
    --requirement "%EIDP_APP_ROOT%\requirements-windows.txt"
if errorlevel 1 (
    echo [first_setup] dependency install failed
    set "SETUP_RC=1"
    goto :finish
)

REM Install eidp itself from the exact bundled wheel file. Installing by
REM package name can reuse a same-version uv cache entry from an older ZIP.
set "EIDP_WHEEL="
for %%F in ("%EIDP_APP_ROOT%\wheelhouse\eidp-*.whl") do (
    if not exist "%%~fF" (
        echo [first_setup] ERROR: wheelhouse\eidp-*.whl is missing.
        set "SETUP_RC=2"
        goto :finish
    )
    if defined EIDP_WHEEL (
        echo [first_setup] ERROR: multiple eidp wheels found in wheelhouse.
        set "SETUP_RC=2"
        goto :finish
    )
    set "EIDP_WHEEL=%%~fF"
)
"%RUNTIME_PY%" "%OFFLINE_PIP%" install ^
    --target "%VENV_SITE_PACKAGES%" ^
    --no-index ^
    --find-links "%EIDP_APP_ROOT%\wheelhouse" ^
    --no-cache-dir ^
    --upgrade ^
    --force-reinstall ^
    --no-deps ^
    "%EIDP_WHEEL%"
if errorlevel 1 (
    echo [first_setup] eidp wheel install failed
    set "SETUP_RC=1"
    goto :finish
)

REM 6b. Optional browser crawler add-on. If the operator has extracted
REM     eidp-playwright-addon-windows.zip into the app root, install its
REM     offline wheels into the same venv. Running setup again after extracting
REM     the add-on is safe because we do not delete .venv above.
set "PLAYWRIGHT_ADDON_WHEELHOUSE=%EIDP_APP_ROOT%\playwright-addon\wheelhouse"
if exist "%PLAYWRIGHT_ADDON_WHEELHOUSE%" (
    echo [first_setup] installing optional Playwright/Scrapling add-on wheels
    "%RUNTIME_PY%" "%OFFLINE_PIP%" install ^
        --target "%VENV_SITE_PACKAGES%" ^
        --no-index ^
        --find-links "%EIDP_APP_ROOT%\playwright-addon\wheelhouse" ^
        --no-cache-dir ^
        --upgrade ^
        "scrapling[fetchers]" playwright
    if errorlevel 1 (
        echo [first_setup] optional Playwright/Scrapling add-on install failed
        set "SETUP_RC=1"
        goto :finish
    )
)

REM 7. Bootstrap the SQLite database (idempotent).
"%VENV_PY%" -m eidp.cli db-bootstrap --sqlite
if errorlevel 1 (
    echo [first_setup] db-bootstrap failed
    set "SETUP_RC=1"
    goto :finish
)

REM 8. Import the master school list. CLI command is import-excel.
REM    master.xlsx is mandatory for v1: without it the task board is empty
REM    and the operator has no entry point. Fail loud rather than
REM    quietly continuing — discovered on the 2026-05-06 Win VM dry run.
if not exist "%EIDP_APP_ROOT%\data\master.xlsx" (
    echo [first_setup] ERROR: data\master.xlsx is missing.
    echo [first_setup] The Windows ZIP must ship with data\master.xlsx.
    echo [first_setup] Re-extract the ZIP, or place a master Excel at
    echo [first_setup]   %EIDP_APP_ROOT%\data\master.xlsx
    echo [first_setup] and re-run this script.
    set "SETUP_RC=3"
    goto :finish
)
"%VENV_PY%" -m eidp.cli import-excel ^
    "%EIDP_APP_ROOT%\data\master.xlsx"
if errorlevel 1 (
    echo [first_setup] master import failed
    set "SETUP_RC=1"
    goto :finish
)

REM 9. Build the initial school x target-year task board so the first UI
REM    launch has actionable rows without requiring the operator to press
REM    "年度タスクを再計算".
"%VENV_PY%" -m eidp.cli rebuild-school-year-tasks
if errorlevel 1 (
    echo [first_setup] school year task rebuild failed
    set "SETUP_RC=1"
    goto :finish
)

REM 10. Register weekly Task Scheduler entry (Mondays 02:00 local).
schtasks /Create /F /SC WEEKLY /D MON /ST 02:00 ^
    /TN "EIDP Weekly Run" ^
    /TR "\"%EIDP_APP_ROOT%\scripts\weekly_run.bat\"" >nul
if errorlevel 1 (
    echo [first_setup] WARNING: schtasks registration failed; operator may need to run weekly_run.bat manually.
    > "%EIDP_APP_ROOT%\data\weekly-task-registration-warning.txt" echo Task Scheduler registration failed during setup. Use the UI weekly rediscovery button, or run setup as a user allowed to create scheduled tasks.
) else (
    if exist "%EIDP_APP_ROOT%\data\weekly-task-registration-warning.txt" del "%EIDP_APP_ROOT%\data\weekly-task-registration-warning.txt" >nul 2>nul
)

REM 11. Run the same after-setup validator used by the VM/operator gate.
REM     This catches broken extracted installs before the operator opens
REM     a confusing half-working UI.
call "%EIDP_APP_ROOT%\scripts\validate_install.bat" --after-setup
if errorlevel 1 (
    echo [first_setup] after-setup validation failed
    set "SETUP_RC=1"
    goto :finish
)

echo [first_setup] complete.
echo [first_setup] Next steps:
echo [first_setup]   1. Double-click EIDP-start.bat to open the operator UI.
echo [first_setup]   2. In the UI, press the initial URL/PDF acquisition button.
set "SETUP_RC=0"

:finish
if defined SETUP_LOCK_DIR if exist "%SETUP_LOCK_DIR%" rmdir "%SETUP_LOCK_DIR%" >nul 2>nul
endlocal & exit /b %SETUP_RC%

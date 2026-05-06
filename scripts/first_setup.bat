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

REM 3. Use the bundled python-build-standalone runtime so we never
REM    depend on whatever Python the operator might have installed.
set "RUNTIME_PY=%EIDP_APP_ROOT%\runtime\python\python.exe"
set "UV_EXE=%EIDP_APP_ROOT%\runtime\uv.exe"
if not exist "%RUNTIME_PY%" (
    echo [first_setup] ERROR: runtime\python\python.exe is missing. Re-extract the ZIP.
    exit /b 2
)
if not exist "%UV_EXE%" (
    echo [first_setup] ERROR: runtime\uv.exe is missing. Re-extract the ZIP.
    exit /b 2
)

REM 4. Create an isolated venv. Use --clear so re-running first_setup.bat
REM    after a partial failure (or to refresh deps) is safe and idempotent.
"%UV_EXE%" venv ".venv" --python "%RUNTIME_PY%" --clear
if errorlevel 1 (
    echo [first_setup] uv venv failed
    exit /b 1
)
set "VENV_PY=%EIDP_APP_ROOT%\.venv\Scripts\python.exe"

REM 5. Offline install from the bundled wheelhouse into the venv.
"%UV_EXE%" pip install ^
    --python "%VENV_PY%" ^
    --no-index ^
    --find-links "%EIDP_APP_ROOT%\wheelhouse" ^
    --requirement "%EIDP_APP_ROOT%\requirements-windows.txt"
if errorlevel 1 (
    echo [first_setup] dependency install failed
    exit /b 1
)

REM Install eidp itself from the exact bundled wheel file. Installing by
REM package name can reuse a same-version uv cache entry from an older ZIP.
set "EIDP_WHEEL="
for %%F in ("%EIDP_APP_ROOT%\wheelhouse\eidp-*.whl") do (
    if not exist "%%~fF" (
        echo [first_setup] ERROR: wheelhouse\eidp-*.whl is missing.
        exit /b 2
    )
    if defined EIDP_WHEEL (
        echo [first_setup] ERROR: multiple eidp wheels found in wheelhouse.
        exit /b 2
    )
    set "EIDP_WHEEL=%%~fF"
)
"%UV_EXE%" pip install ^
    --python "%VENV_PY%" ^
    --no-index ^
    --find-links "%EIDP_APP_ROOT%\wheelhouse" ^
    --no-cache ^
    --reinstall-package eidp ^
    "%EIDP_WHEEL%"
if errorlevel 1 (
    echo [first_setup] eidp wheel install failed
    exit /b 1
)

REM 6. Bootstrap the SQLite database (idempotent).
"%VENV_PY%" -m eidp.cli db-bootstrap --sqlite
if errorlevel 1 (
    echo [first_setup] db-bootstrap failed
    exit /b 1
)

REM 7. Import the master school list. CLI command is import-excel.
REM    master.xlsx is mandatory for v1: without it the task board is empty
REM    and the operator has no entry point. Fail loud rather than
REM    quietly continuing — discovered on the 2026-05-06 Win VM dry run.
if not exist "%EIDP_APP_ROOT%\data\master.xlsx" (
    echo [first_setup] ERROR: data\master.xlsx is missing.
    echo [first_setup] The Windows ZIP must ship with data\master.xlsx.
    echo [first_setup] Re-extract the ZIP, or place a master Excel at
    echo [first_setup]   %EIDP_APP_ROOT%\data\master.xlsx
    echo [first_setup] and re-run this script.
    exit /b 3
)
"%VENV_PY%" -m eidp.cli import-excel ^
    "%EIDP_APP_ROOT%\data\master.xlsx"
if errorlevel 1 (
    echo [first_setup] master import failed
    exit /b 1
)

REM 8. Build the initial school x target-year task board so the first UI
REM    launch has actionable rows without requiring the operator to press
REM    "年度タスクを再計算".
"%VENV_PY%" -m eidp.cli rebuild-school-year-tasks
if errorlevel 1 (
    echo [first_setup] school year task rebuild failed
    exit /b 1
)

REM 9. Register weekly Task Scheduler entry (Mondays 02:00 local).
schtasks /Create /F /SC WEEKLY /D MON /ST 02:00 ^
    /TN "EIDP Weekly Run" ^
    /TR "\"%EIDP_APP_ROOT%\scripts\weekly_run.bat\"" >nul
if errorlevel 1 (
    echo [first_setup] WARNING: schtasks registration failed; operator may need to run weekly_run.bat manually.
)

echo [first_setup] complete.
echo [first_setup] Next steps:
echo [first_setup]   1. Double-click EIDP-start.bat to open the operator UI.
echo [first_setup]   2. In the UI, press the initial URL/PDF acquisition button.
endlocal
exit /b 0

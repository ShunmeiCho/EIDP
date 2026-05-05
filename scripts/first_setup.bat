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
"%UV_EXE%" pip install ^
    --python "%VENV_PY%" ^
    --no-index ^
    --find-links "%EIDP_APP_ROOT%\wheelhouse" ^
    eidp
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

REM 7. Import the master school list if it exists. CLI command is import-excel.
if exist "%EIDP_APP_ROOT%\data\master.xlsx" (
    "%VENV_PY%" -m eidp.cli import-excel ^
        "%EIDP_APP_ROOT%\data\master.xlsx"
    if errorlevel 1 (
        echo [first_setup] master import failed
        exit /b 1
    )
) else (
    echo [first_setup] WARNING: data\master.xlsx is missing — operator must import manually before week 1.
)

REM 8. Register weekly Task Scheduler entry (Mondays 02:00 local).
schtasks /Create /F /SC WEEKLY /D MON /ST 02:00 ^
    /TN "EIDP Weekly Run" ^
    /TR "\"%EIDP_APP_ROOT%\scripts\weekly_run.bat\"" >nul
if errorlevel 1 (
    echo [first_setup] WARNING: schtasks registration failed; operator may need to run weekly_run.bat manually.
)

echo [first_setup] complete. Launch the UI by double-clicking scripts\launch.bat
endlocal
exit /b 0

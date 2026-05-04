@echo off
REM Sprint 8.5.a — first-run setup for the Windows operator PC.
REM
REM Resolves the application root from the script location (cd /d
REM "%~dp0\.."), pins it via EIDP_APP_ROOT so subsequent processes
REM agree on the path, then installs from the bundled wheelhouse with
REM no network, bootstraps the SQLite database, imports the master
REM school list, and registers the weekly Task Scheduler entry.
REM
REM This script is hand-written and intended to be reviewed statically
REM on Mac before being executed for real on the Windows VM gate.

setlocal EnableExtensions EnableDelayedExpansion

REM 1. Anchor at the application root regardless of who invoked us.
cd /d "%~dp0\.."
set "EIDP_APP_ROOT=%CD%"

REM 2. Make sure data/, logs/, output/ exist before any tool writes.
if not exist "data"        mkdir "data"
if not exist "data\pdfs"   mkdir "data\pdfs"
if not exist "data\output" mkdir "data\output"
if not exist "data\audit"  mkdir "data\audit"
if not exist "logs"        mkdir "logs"

REM 3. Use the bundled python-build-standalone runtime so we never
REM    depend on whatever Python the operator might have installed.
set "PYTHONHOME=%EIDP_APP_ROOT%\runtime\python"
set "PATH=%EIDP_APP_ROOT%\runtime\python;%EIDP_APP_ROOT%\runtime;%PATH%"

REM 4. Offline install from the bundled wheelhouse.
"%EIDP_APP_ROOT%\runtime\uv.exe" pip install ^
    --no-index ^
    --find-links "%EIDP_APP_ROOT%\wheelhouse" ^
    --requirement "%EIDP_APP_ROOT%\requirements-windows.txt"
if errorlevel 1 (
    echo [first_setup] dependency install failed
    exit /b 1
)
"%EIDP_APP_ROOT%\runtime\uv.exe" pip install ^
    --no-index ^
    --find-links "%EIDP_APP_ROOT%\wheelhouse" ^
    eidp
if errorlevel 1 (
    echo [first_setup] eidp wheel install failed
    exit /b 1
)

REM 5. Bootstrap the SQLite database (idempotent).
"%EIDP_APP_ROOT%\runtime\python\python.exe" -m eidp.cli db-bootstrap --sqlite
if errorlevel 1 (
    echo [first_setup] db-bootstrap failed
    exit /b 1
)

REM 6. Import the master school list if it exists.
if exist "%EIDP_APP_ROOT%\data\master.xlsx" (
    "%EIDP_APP_ROOT%\runtime\python\python.exe" -m eidp.cli import-master ^
        "%EIDP_APP_ROOT%\data\master.xlsx"
    if errorlevel 1 (
        echo [first_setup] master import failed
        exit /b 1
    )
) else (
    echo [first_setup] WARNING: data\master.xlsx is missing — operator must import manually before week 1.
)

REM 7. Register weekly Task Scheduler entry (Mondays 02:00 local).
schtasks /Create /F /SC WEEKLY /D MON /ST 02:00 ^
    /TN "EIDP Weekly Run" ^
    /TR "\"%EIDP_APP_ROOT%\scripts\weekly_run.bat\"" >nul
if errorlevel 1 (
    echo [first_setup] WARNING: schtasks registration failed; operator may need to run weekly_run.bat manually.
)

echo [first_setup] complete. Launch the UI by double-clicking scripts\launch.bat
endlocal
exit /b 0

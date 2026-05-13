@echo off
REM Build a read-only Stage 6 evidence ZIP for operator-PC handoff.
REM
REM This wrapper first refreshes diagnostics, then bundles the latest logs,
REM last_run.json, RCA plan, recovery JSON, and Excel exports. It does not copy
REM the live SQLite database, WAL/SHM sidecars, downloaded PDFs, runtime, or
REM wheelhouse.
REM Output: logs\stage6-evidence-*.zip

setlocal EnableExtensions

cd /d "%~dp0\.."
set "EIDP_APP_ROOT=%CD%"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"

if not exist "logs" mkdir "logs"

set "VENV_PY=%EIDP_APP_ROOT%\.venv\Scripts\python.exe"
set "RUNTIME_PY=%EIDP_APP_ROOT%\runtime\python\python.exe"

if exist "%VENV_PY%" (
    set "PY_EXE=%VENV_PY%"
) else if exist "%RUNTIME_PY%" (
    set "PY_EXE=%RUNTIME_PY%"
) else (
    echo [collect_stage6_evidence] ERROR: no Python found. Run EIDP-setup.bat or re-extract the ZIP.
    exit /b 2
)

call "%EIDP_APP_ROOT%\scripts\diagnose.bat"
set "DIAG_RC=%ERRORLEVEL%"

"%PY_EXE%" "%EIDP_APP_ROOT%\scripts\collect_stage6_evidence.py" "%EIDP_APP_ROOT%" --json
set "BUNDLE_RC=%ERRORLEVEL%"

if not "%DIAG_RC%"=="0" (
    echo [collect_stage6_evidence] WARNING: diagnostics returned %DIAG_RC%; evidence ZIP may still contain useful files.
)
if not "%BUNDLE_RC%"=="0" (
    echo [collect_stage6_evidence] ERROR: evidence ZIP creation failed with exit code %BUNDLE_RC%.
)

endlocal & exit /b %BUNDLE_RC%

@echo off
REM Build a read-only Stage 6 evidence ZIP for operator-PC handoff.
REM
REM This wrapper first refreshes diagnostics, then bundles the latest logs,
REM last_run.json, discovery evidence, RCA plan, and recovery JSON. It does not copy the live SQLite database,
REM WAL/SHM sidecars, downloaded PDFs, Excel exports, runtime, or
REM wheelhouse unless an explicit Python-level opt-in is passed.
REM
REM To include Excel exports for internal-only handoff:
REM   scripts\collect_stage6_evidence.bat --include-excel
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

"%PY_EXE%" "%EIDP_APP_ROOT%\scripts\collect_stage6_evidence.py" "%EIDP_APP_ROOT%" --json %*
set "BUNDLE_RC=%ERRORLEVEL%"

if not "%DIAG_RC%"=="0" (
    echo [collect_stage6_evidence] WARNING: diagnostics returned %DIAG_RC%; evidence ZIP may still contain useful files.
)
if not "%BUNDLE_RC%"=="0" (
    echo [collect_stage6_evidence] ERROR: evidence ZIP creation failed with exit code %BUNDLE_RC%.
)

endlocal & exit /b %BUNDLE_RC%

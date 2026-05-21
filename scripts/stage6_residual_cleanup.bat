@echo off
REM Archive known interrupted Stage 6 smoke artifacts.
REM
REM Dry-run by default:
REM   scripts\stage6_residual_cleanup.bat --json
REM
REM To move residual files into logs\stage6-residual-archive\<timestamp>:
REM   scripts\stage6_residual_cleanup.bat --apply --json

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
    echo [stage6_residual_cleanup] ERROR: no Python found. Run EIDP-setup.bat or re-extract the ZIP.
    exit /b 2
)

echo [stage6_residual_cleanup] dry-run unless --apply is passed.
"%PY_EXE%" "%EIDP_APP_ROOT%\scripts\stage6_residual_cleanup.py" --app-root "%EIDP_APP_ROOT%" %*
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
    echo [stage6_residual_cleanup] Residual artifacts still exist or cleanup failed. Review the JSON above.
)

endlocal & exit /b %RC%

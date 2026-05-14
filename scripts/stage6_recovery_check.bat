@echo off
REM Read-only Stage 6 recovery checker for the Windows operator PC.
REM
REM Usage:
REM   scripts\stage6_recovery_check.bat
REM   scripts\stage6_recovery_check.bat "C:\EIDP\scripts\weekly_run.bat"
REM
REM By default, this wrapper skips the scheduled-task action path check to avoid
REM false positives from disposable ZIP extraction directories. To verify the
REM production runtime, pass that path as the first argument or set
REM EIDP_EXPECTED_WEEKLY_ACTION.

setlocal EnableExtensions

cd /d "%~dp0\.."
set "EIDP_APP_ROOT=%CD%"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"

if not exist "logs" mkdir "logs"

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "RECOVERY_STAMP=%%I"
if "%RECOVERY_STAMP%"=="" set "RECOVERY_STAMP=unknown-date"
set "RECOVERY_FILE=%EIDP_APP_ROOT%\logs\stage6-recovery-%RECOVERY_STAMP%.json"

set "EXPECTED_WEEKLY_ACTION=%~1"
if "%EXPECTED_WEEKLY_ACTION%"=="" set "EXPECTED_WEEKLY_ACTION=%EIDP_EXPECTED_WEEKLY_ACTION%"

set "VENV_PY=%EIDP_APP_ROOT%\.venv\Scripts\python.exe"
set "RUNTIME_PY=%EIDP_APP_ROOT%\runtime\python\python.exe"

if exist "%VENV_PY%" (
    set "PY_EXE=%VENV_PY%"
) else if exist "%RUNTIME_PY%" (
    set "PY_EXE=%RUNTIME_PY%"
) else (
    echo [stage6_recovery_check] ERROR: no Python found. Run EIDP-setup.bat or re-extract the ZIP.
    exit /b 2
)

if "%EXPECTED_WEEKLY_ACTION%"=="" (
    echo [stage6_recovery_check] expected weekly action: skipped
    "%PY_EXE%" "%EIDP_APP_ROOT%\scripts\stage6_recovery_check.py" --json > "%RECOVERY_FILE%"
) else (
    echo [stage6_recovery_check] expected weekly action: %EXPECTED_WEEKLY_ACTION%
    "%PY_EXE%" "%EIDP_APP_ROOT%\scripts\stage6_recovery_check.py" --expected-weekly-action "%EXPECTED_WEEKLY_ACTION%" --json > "%RECOVERY_FILE%"
)
set "RC=%ERRORLEVEL%"

type "%RECOVERY_FILE%"
echo.
echo [stage6_recovery_check] wrote %RECOVERY_FILE%
if not "%RC%"=="0" (
    echo [stage6_recovery_check] Review the recommendations above before resuming Stage 6.
)

endlocal & exit /b %RC%

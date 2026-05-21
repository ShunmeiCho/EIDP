@echo off
REM Weekly target-fiscal-year discovery runner for Task Scheduler.
REM Sprint 8.5.a.1 — runs from the .venv created by first_setup.bat.
REM
REM Same EIDP_APP_ROOT / encoding contract as launch.bat. Writes a
REM rotating log under logs\ and lets the Python process create the
REM shared lock at data\.lock so the running UI knows to disable
REM write controls.

setlocal EnableExtensions

cd /d "%~dp0\.."
set "EIDP_APP_ROOT=%CD%"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
set "PYTHONPATH=%EIDP_APP_ROOT%\src;%PYTHONPATH%"

set "VENV_PY=%EIDP_APP_ROOT%\.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
    echo [weekly_run] ERROR: .venv not found. Run EIDP-setup.bat first.
    exit /b 2
)

if not exist "logs" mkdir "logs"

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd"') do set "DATESTAMP=%%I"
if "%DATESTAMP%"=="" set "DATESTAMP=unknown-date"
set "LOGFILE=%EIDP_APP_ROOT%\logs\run-%DATESTAMP%.log"

set "WEEKLY_ARGS="
if defined EIDP_WEEKLY_CURRENT_FY set "WEEKLY_ARGS=%WEEKLY_ARGS% --current-fy %EIDP_WEEKLY_CURRENT_FY%"
if defined EIDP_WEEKLY_LIMIT set "WEEKLY_ARGS=%WEEKLY_ARGS% --limit %EIDP_WEEKLY_LIMIT%"
if defined EIDP_WEEKLY_BATCH_SIZE set "WEEKLY_ARGS=%WEEKLY_ARGS% --batch-size %EIDP_WEEKLY_BATCH_SIZE%"
if defined EIDP_WEEKLY_RATE_LIMIT set "WEEKLY_ARGS=%WEEKLY_ARGS% --rate-limit %EIDP_WEEKLY_RATE_LIMIT%"
if defined EIDP_WEEKLY_REQUEST_TIMEOUT set "WEEKLY_ARGS=%WEEKLY_ARGS% --request-timeout %EIDP_WEEKLY_REQUEST_TIMEOUT%"
if /I "%EIDP_WEEKLY_DRY_RUN%"=="1" set "WEEKLY_ARGS=%WEEKLY_ARGS% --dry-run"
if /I "%EIDP_WEEKLY_DRY_RUN%"=="true" set "WEEKLY_ARGS=%WEEKLY_ARGS% --dry-run"

echo [weekly_run] start %DATE% %TIME% >> "%LOGFILE%"
if defined WEEKLY_ARGS echo [weekly_run] args%WEEKLY_ARGS% >> "%LOGFILE%"
if not "%~1"=="" echo [weekly_run] cli_args %* >> "%LOGFILE%"
"%VENV_PY%" "%EIDP_APP_ROOT%\scripts\run_weekly_target_year_discovery.py" %WEEKLY_ARGS% %* >> "%LOGFILE%" 2>&1
set "RC=%ERRORLEVEL%"
echo [weekly_run] end %DATE% %TIME% rc=%RC% >> "%LOGFILE%"

endlocal & exit /b %RC%

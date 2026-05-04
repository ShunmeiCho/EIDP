@echo off
REM Sprint 8.5.a — weekly R8 rediscovery runner for Task Scheduler.
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

set "VENV_PY=%EIDP_APP_ROOT%\.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
    echo [weekly_run] ERROR: .venv not found. Run scripts\first_setup.bat first.
    exit /b 2
)

if not exist "logs" mkdir "logs"

set "DATESTAMP=%DATE:~0,4%%DATE:~5,2%%DATE:~8,2%"
set "LOGFILE=%EIDP_APP_ROOT%\logs\run-%DATESTAMP%.log"

echo [weekly_run] start %DATE% %TIME% >> "%LOGFILE%"
"%VENV_PY%" "%EIDP_APP_ROOT%\scripts\run_r8_rediscovery_weekly.py" >> "%LOGFILE%" 2>&1
set "RC=%ERRORLEVEL%"
echo [weekly_run] end %DATE% %TIME% rc=%RC% >> "%LOGFILE%"

endlocal
exit /b %RC%

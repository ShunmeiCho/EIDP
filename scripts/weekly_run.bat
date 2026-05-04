@echo off
REM Sprint 8.5.a — weekly R8 rediscovery runner for Task Scheduler.
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

set "PYTHONHOME=%EIDP_APP_ROOT%\runtime\python"
set "PATH=%EIDP_APP_ROOT%\runtime\python;%EIDP_APP_ROOT%\runtime;%PATH%"

if not exist "logs" mkdir "logs"

set "DATESTAMP=%DATE:~0,4%%DATE:~5,2%%DATE:~8,2%"
set "LOGFILE=%EIDP_APP_ROOT%\logs\run-%DATESTAMP%.log"

echo [weekly_run] start %DATE% %TIME% >> "%LOGFILE%"
"%EIDP_APP_ROOT%\runtime\python\python.exe" ^
    "%EIDP_APP_ROOT%\scripts\run_r8_rediscovery_weekly.py" >> "%LOGFILE%" 2>&1
set "RC=%ERRORLEVEL%"
echo [weekly_run] end %DATE% %TIME% rc=%RC% >> "%LOGFILE%"

endlocal
exit /b %RC%

@echo off
REM Root-level Stage 6 recovery launcher for non-technical Windows operators.
REM scripts\stage6_recovery_check.bat owns the actual read-only recovery contract.

setlocal EnableExtensions

cd /d "%~dp0"
call "%~dp0scripts\stage6_recovery_check.bat" %*
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo [EIDP] Stage 6 recovery check passed.
) else (
    echo [EIDP] Stage 6 recovery check failed with exit code %RC%.
    echo [EIDP] Keep this window open and share the message above with the administrator.
)
echo.
pause

endlocal & exit /b %RC%

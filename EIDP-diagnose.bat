@echo off
REM Root-level diagnostics launcher for non-technical Windows operators.
REM scripts\diagnose.bat owns the actual collection contract.

setlocal EnableExtensions

cd /d "%~dp0"
call "%~dp0scripts\diagnose.bat"
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo [EIDP] Diagnostics collected.
) else (
    echo [EIDP] Diagnostics command failed with exit code %RC%.
    echo [EIDP] Keep this window open and share the message above with the administrator.
)
echo.
pause

endlocal & exit /b %RC%

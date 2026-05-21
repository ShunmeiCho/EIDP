@echo off
REM Root-level Stage 6 evidence bundle launcher for non-technical Windows operators.
REM scripts\collect_stage6_evidence.bat owns the actual read-only bundle contract.

setlocal EnableExtensions

cd /d "%~dp0"
call "%~dp0scripts\collect_stage6_evidence.bat"
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo [EIDP] Stage 6 evidence bundle created.
    echo [EIDP] Share the newest logs\stage6-evidence-*.zip file with the administrator.
) else (
    echo [EIDP] Stage 6 evidence bundle failed with exit code %RC%.
    echo [EIDP] Keep this window open and share the message above with the administrator.
)
echo.
pause

endlocal & exit /b %RC%

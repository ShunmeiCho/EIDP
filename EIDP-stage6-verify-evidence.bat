@echo off
REM Root-level Stage 6 evidence verifier launcher for Windows operators/admins.
REM scripts\verify_stage6_evidence.bat owns the actual read-only verifier contract.

setlocal EnableExtensions

cd /d "%~dp0"
call "%~dp0scripts\verify_stage6_evidence.bat"
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo [EIDP] Stage 6 evidence ZIP verified.
) else (
    echo [EIDP] Stage 6 evidence ZIP verification failed with exit code %RC%.
    echo [EIDP] Keep this window open and share the message above with the administrator.
)
echo.
pause

endlocal & exit /b %RC%

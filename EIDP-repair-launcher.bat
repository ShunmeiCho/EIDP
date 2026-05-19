@echo off
REM Root-level launcher repair helper for non-technical Windows operators.
REM scripts\repair_streamlit_launcher.bat owns the actual dry-run/apply contract.

setlocal EnableExtensions

cd /d "%~dp0"
call "%~dp0scripts\repair_streamlit_launcher.bat" %*
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo [EIDP] Launcher repair check completed.
    echo [EIDP] If this was a dry-run and it reported a pending repair, rerun with --apply.
) else (
    echo [EIDP] Launcher repair check failed with exit code %RC%.
    echo [EIDP] Keep this window open and share the message above with the administrator.
)
echo.
pause

endlocal & exit /b %RC%

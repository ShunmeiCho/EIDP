@echo off
REM Root-level first setup launcher for non-technical Windows operators.
REM Keep this wrapper small: scripts\first_setup.bat owns the real setup
REM contract and is covered by the Windows validation gate.

setlocal EnableExtensions

cd /d "%~dp0"
call "%~dp0scripts\first_setup.bat"
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo [EIDP] Setup completed.
    echo [EIDP] Next: double-click EIDP-start.bat.
) else (
    echo [EIDP] Setup failed with exit code %RC%.
    echo [EIDP] Keep this window open and share the message above with the administrator.
)
echo.
pause

endlocal & exit /b %RC%

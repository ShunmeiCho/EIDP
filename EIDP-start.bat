@echo off
REM Root-level Streamlit launcher for non-technical Windows operators.
REM scripts\launch.bat owns the actual app startup contract.

setlocal EnableExtensions

cd /d "%~dp0"
call "%~dp0scripts\launch.bat"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
    echo.
    echo [EIDP] App launch failed with exit code %RC%.
    echo [EIDP] Run EIDP-setup.bat first. If setup already ran, share the message above with the administrator.
    echo.
    pause
)

endlocal & exit /b %RC%

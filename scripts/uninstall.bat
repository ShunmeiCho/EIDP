@echo off
REM Sprint 8.5.a — uninstall the operator install.
REM
REM Removes the Task Scheduler entry. Does NOT delete the data
REM directory automatically (operator data is precious; deletion is an
REM explicit choice the operator can do via Explorer).

setlocal EnableExtensions

schtasks /Delete /F /TN "EIDP Weekly Run" >nul 2>&1
if errorlevel 1 (
    echo [uninstall] no Task Scheduler entry found, or deletion failed; continuing.
) else (
    echo [uninstall] removed Task Scheduler entry "EIDP Weekly Run".
)

echo [uninstall] data\, logs\, output\ left in place. Delete manually if you want a clean slate.
endlocal
exit /b 0

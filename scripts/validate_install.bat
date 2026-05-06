@echo off
REM Sprint 8.7 — Windows VM / operator-PC install validator wrapper.
REM
REM Runs scripts\validate_windows_install.py from the extracted EIDP
REM directory. After first_setup.bat it uses the .venv Python; before
REM setup it can fall back to the bundled runtime Python because the
REM validator is stdlib-only.

setlocal EnableExtensions

cd /d "%~dp0\.."
set "EIDP_APP_ROOT=%CD%"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"

set "VENV_PY=%EIDP_APP_ROOT%\.venv\Scripts\python.exe"
set "RUNTIME_PY=%EIDP_APP_ROOT%\runtime\python\python.exe"

if exist "%VENV_PY%" (
    set "PY_EXE=%VENV_PY%"
) else if exist "%RUNTIME_PY%" (
    set "PY_EXE=%RUNTIME_PY%"
) else (
    echo [validate_install] ERROR: no Python found. Run EIDP-setup.bat or re-extract the ZIP.
    exit /b 2
)

"%PY_EXE%" "%EIDP_APP_ROOT%\scripts\validate_windows_install.py" "%EIDP_APP_ROOT%" %*
set "RC=%ERRORLEVEL%"

endlocal & exit /b %RC%

@echo off
REM Repair a stale Streamlit launcher that still calls streamlit.main.
REM
REM Dry-run by default:
REM   scripts\repair_streamlit_launcher.bat --json
REM
REM To rewrite scripts\launch.bat and keep a .bak backup:
REM   scripts\repair_streamlit_launcher.bat --apply --json

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
    echo [repair_streamlit_launcher] ERROR: no Python found. Run EIDP-setup.bat or re-extract the ZIP.
    exit /b 2
)

echo [repair_streamlit_launcher] dry-run unless --apply is passed.
"%PY_EXE%" "%EIDP_APP_ROOT%\scripts\repair_streamlit_launcher.py" "%EIDP_APP_ROOT%" %*
set "RC=%ERRORLEVEL%"

endlocal & exit /b %RC%

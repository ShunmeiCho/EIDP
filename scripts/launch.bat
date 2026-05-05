@echo off
REM Sprint 8.5.a — Streamlit launcher for the operator PC.
REM Sprint 8.5.a.1 — runs from the .venv created by first_setup.bat.
REM
REM Anchors EIDP_APP_ROOT, forces UTF-8 console output (Windows default
REM is cp932 in Japan, which corrupts emoji and the few Japanese
REM characters Streamlit echoes), and starts the review app on
REM localhost:8501.

setlocal EnableExtensions

cd /d "%~dp0\.."
set "EIDP_APP_ROOT=%CD%"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"

set "VENV_PY=%EIDP_APP_ROOT%\.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
    echo [launch] ERROR: .venv not found. Run scripts\first_setup.bat first.
    exit /b 2
)

"%VENV_PY%" -m streamlit run ^
    "%EIDP_APP_ROOT%\src\eidp\review\app.py" ^
    --server.port 8501 ^
    --server.headless true
set "RC=%ERRORLEVEL%"

endlocal & exit /b %RC%

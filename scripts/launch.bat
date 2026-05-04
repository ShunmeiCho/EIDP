@echo off
REM Sprint 8.5.a — Streamlit launcher for the operator PC.
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

set "PYTHONHOME=%EIDP_APP_ROOT%\runtime\python"
set "PATH=%EIDP_APP_ROOT%\runtime\python;%EIDP_APP_ROOT%\runtime;%PATH%"

"%EIDP_APP_ROOT%\runtime\python\python.exe" -m streamlit run ^
    "%EIDP_APP_ROOT%\src\eidp\review\app.py" ^
    --server.port 8501 ^
    --server.headless true

endlocal
exit /b %ERRORLEVEL%

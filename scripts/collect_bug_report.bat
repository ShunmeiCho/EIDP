@echo off
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
  echo [collect_bug_report] ERROR: no Python found. Run EIDP-setup.bat or re-extract the ZIP.
  exit /b 2
)

"%PY_EXE%" "%EIDP_APP_ROOT%\scripts\collect_bug_report.py" --root "%EIDP_APP_ROOT%" %*
exit /b %ERRORLEVEL%

@echo off
REM Verify the latest read-only Stage 6 evidence ZIP.
REM
REM Usage:
REM   scripts\verify_stage6_evidence.bat
REM   scripts\verify_stage6_evidence.bat "C:\EIDP\logs\stage6-evidence-YYYYMMDD-HHMMSS.zip"
REM
REM Output: logs\stage6-evidence-verify-*.json

setlocal EnableExtensions

cd /d "%~dp0\.."
set "EIDP_APP_ROOT=%CD%"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"

if not exist "logs" mkdir "logs"

set "EVIDENCE_ZIP=%~1"
if "%EVIDENCE_ZIP%"=="" (
    for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "$p = Get-ChildItem -Path 'logs' -Filter 'stage6-evidence-*.zip' -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName; if ($p) { $p }"`) do set "EVIDENCE_ZIP=%%I"
)

if "%EVIDENCE_ZIP%"=="" (
    echo [verify_stage6_evidence] ERROR: no logs\stage6-evidence-*.zip file found.
    echo [verify_stage6_evidence] Run EIDP-stage6-evidence.bat first.
    exit /b 3
)

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "VERIFY_STAMP=%%I"
if "%VERIFY_STAMP%"=="" set "VERIFY_STAMP=unknown-date"
set "VERIFY_FILE=%EIDP_APP_ROOT%\logs\stage6-evidence-verify-%VERIFY_STAMP%.json"

set "VENV_PY=%EIDP_APP_ROOT%\.venv\Scripts\python.exe"
set "RUNTIME_PY=%EIDP_APP_ROOT%\runtime\python\python.exe"

if exist "%VENV_PY%" (
    set "PY_EXE=%VENV_PY%"
) else if exist "%RUNTIME_PY%" (
    set "PY_EXE=%RUNTIME_PY%"
) else (
    echo [verify_stage6_evidence] ERROR: no Python found. Run EIDP-setup.bat or re-extract the ZIP.
    exit /b 2
)

echo [verify_stage6_evidence] evidence ZIP: %EVIDENCE_ZIP%

"%PY_EXE%" "%EIDP_APP_ROOT%\scripts\verify_stage6_evidence.py" "%EVIDENCE_ZIP%" --json --require-label last_run > "%VERIFY_FILE%"
set "RC=%ERRORLEVEL%"

type "%VERIFY_FILE%"
echo.
echo [verify_stage6_evidence] wrote %VERIFY_FILE%
if not "%RC%"=="0" (
    echo [verify_stage6_evidence] Do not treat this ZIP as Stage 6 release evidence until the errors are fixed.
)

endlocal & exit /b %RC%

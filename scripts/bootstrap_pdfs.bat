@echo off
REM Sprint 8.7.e — operator-side first-time PDF bootstrap.
REM
REM Runs the end-to-end discovery pipeline on the operator PC:
REM   1. download prefecture artifact PDFs from seed.csv URLs
REM   2. parse each into school_site rows (eidp prefecture-aggregate --apply)
REM   3. crawl school sites for disclosure PDFs (eidp discover-pdfs)
REM   4. parse downloaded PDFs into DB rows (eidp ingest-pdfs)
REM
REM This is online — the operator must have internet access. Run once
REM after first_setup.bat completes; weekly_run.bat keeps everything
REM fresh thereafter.

setlocal EnableExtensions
cd /d "%~dp0\.."
set "EIDP_APP_ROOT=%CD%"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"

set "VENV_PY=%EIDP_APP_ROOT%\.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
    echo [bootstrap_pdfs] ERROR: .venv missing. Run EIDP-setup.bat first.
    exit /b 2
)

set "LOGS_DIR=%EIDP_APP_ROOT%\logs"
if not exist "%LOGS_DIR%" mkdir "%LOGS_DIR%"
for /f "delims=" %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "RUN_ID=%%T"
set "LOG_PATH=%LOGS_DIR%\bootstrap-pdfs-%RUN_ID%.log"
set "PROGRESS_PATH=%LOGS_DIR%\bootstrap-pdfs-%RUN_ID%.json"

echo [bootstrap_pdfs] writing log to %LOG_PATH%
"%VENV_PY%" "%EIDP_APP_ROOT%\scripts\bootstrap_pdf_pipeline.py" --progress-file "%PROGRESS_PATH%" %* > "%LOG_PATH%" 2>&1
set "RC=%ERRORLEVEL%"
type "%LOG_PATH%"

if %RC% EQU 0 (
    echo [bootstrap_pdfs] complete. Open the UI to review queued PDFs.
) else (
    echo [bootstrap_pdfs] exited with code %RC%.
)
endlocal & exit /b %RC%

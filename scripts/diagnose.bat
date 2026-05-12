@echo off
REM Collect operator-PC diagnostics into logs\diagnostics-*.txt.
REM
REM This wrapper is intentionally stdlib-only and can run before setup
REM completes. It never mutates application data; it only reads status,
REM build metadata, validation output, and recent logs.

setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0\.."
set "EIDP_APP_ROOT=%CD%"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"

if not exist "logs" mkdir "logs"

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "DIAG_STAMP=%%I"
if "%DIAG_STAMP%"=="" set "DIAG_STAMP=unknown-date"
set "DIAG_FILE=%EIDP_APP_ROOT%\logs\diagnostics-%DIAG_STAMP%.txt"

set "VENV_PY=%EIDP_APP_ROOT%\.venv\Scripts\python.exe"
set "RUNTIME_PY=%EIDP_APP_ROOT%\runtime\python\python.exe"
if exist "%VENV_PY%" (
    set "PY_EXE=%VENV_PY%"
) else if exist "%RUNTIME_PY%" (
    set "PY_EXE=%RUNTIME_PY%"
) else (
    set "PY_EXE="
)

> "%DIAG_FILE%" echo EIDP diagnostics
>> "%DIAG_FILE%" echo generated_at=%DATE% %TIME%
>> "%DIAG_FILE%" echo app_root=%EIDP_APP_ROOT%
>> "%DIAG_FILE%" echo python=%PY_EXE%
>> "%DIAG_FILE%" echo.

>> "%DIAG_FILE%" echo [BUILD_INFO.json]
if exist "%EIDP_APP_ROOT%\BUILD_INFO.json" (
    type "%EIDP_APP_ROOT%\BUILD_INFO.json" >> "%DIAG_FILE%"
) else (
    >> "%DIAG_FILE%" echo missing BUILD_INFO.json
)
>> "%DIAG_FILE%" echo.

>> "%DIAG_FILE%" echo [validate_install core]
if defined PY_EXE (
    "%PY_EXE%" "%EIDP_APP_ROOT%\scripts\validate_windows_install.py" "%EIDP_APP_ROOT%" >> "%DIAG_FILE%" 2>&1
    set "VALIDATE_CORE_RC=!ERRORLEVEL!"
    >> "%DIAG_FILE%" echo validate_core_rc=!VALIDATE_CORE_RC!
) else (
    >> "%DIAG_FILE%" echo no Python found; cannot run validator
)
>> "%DIAG_FILE%" echo.

>> "%DIAG_FILE%" echo [validate_install after-setup]
if exist "%VENV_PY%" (
    "%VENV_PY%" "%EIDP_APP_ROOT%\scripts\validate_windows_install.py" "%EIDP_APP_ROOT%" --after-setup >> "%DIAG_FILE%" 2>&1
    set "VALIDATE_SETUP_RC=!ERRORLEVEL!"
    >> "%DIAG_FILE%" echo validate_after_setup_rc=!VALIDATE_SETUP_RC!
) else (
    >> "%DIAG_FILE%" echo skipped; .venv Python is missing
)
>> "%DIAG_FILE%" echo.

set "HAS_BOOTSTRAP_PROGRESS="
for /f "delims=" %%F in ('dir /b /o-d "%EIDP_APP_ROOT%\logs\bootstrap-pdfs-*.json" 2^>nul') do (
    if not defined HAS_BOOTSTRAP_PROGRESS set "HAS_BOOTSTRAP_PROGRESS=1"
)
>> "%DIAG_FILE%" echo [validate_install after-bootstrap]
if exist "%VENV_PY%" (
    if defined HAS_BOOTSTRAP_PROGRESS (
        "%VENV_PY%" "%EIDP_APP_ROOT%\scripts\validate_windows_install.py" "%EIDP_APP_ROOT%" --after-setup --after-bootstrap >> "%DIAG_FILE%" 2>&1
        set "VALIDATE_BOOTSTRAP_RC=!ERRORLEVEL!"
        >> "%DIAG_FILE%" echo validate_after_bootstrap_rc=!VALIDATE_BOOTSTRAP_RC!
    ) else (
        >> "%DIAG_FILE%" echo skipped; no bootstrap progress file found
    )
) else (
    >> "%DIAG_FILE%" echo skipped; .venv Python is missing
)
>> "%DIAG_FILE%" echo.

>> "%DIAG_FILE%" echo [validate_install after-bootstrap require-ship-gate]
if exist "%VENV_PY%" (
    if defined HAS_BOOTSTRAP_PROGRESS (
        "%VENV_PY%" "%EIDP_APP_ROOT%\scripts\validate_windows_install.py" "%EIDP_APP_ROOT%" --after-setup --after-bootstrap --require-ship-gate >> "%DIAG_FILE%" 2>&1
        set "VALIDATE_BOOTSTRAP_SHIP_GATE_RC=!ERRORLEVEL!"
        >> "%DIAG_FILE%" echo validate_after_bootstrap_ship_gate_rc=!VALIDATE_BOOTSTRAP_SHIP_GATE_RC!
    ) else (
        >> "%DIAG_FILE%" echo skipped; no bootstrap progress file found
    )
) else (
    >> "%DIAG_FILE%" echo skipped; .venv Python is missing
)
>> "%DIAG_FILE%" echo.

>> "%DIAG_FILE%" echo [weekly task registration warning]
if exist "%EIDP_APP_ROOT%\data\weekly-task-registration-warning.txt" (
    type "%EIDP_APP_ROOT%\data\weekly-task-registration-warning.txt" >> "%DIAG_FILE%"
) else (
    >> "%DIAG_FILE%" echo none
)
>> "%DIAG_FILE%" echo.

>> "%DIAG_FILE%" echo [last_run.json]
if exist "%EIDP_APP_ROOT%\data\output\last_run.json" (
    type "%EIDP_APP_ROOT%\data\output\last_run.json" >> "%DIAG_FILE%"
) else (
    >> "%DIAG_FILE%" echo missing data\output\last_run.json
)
>> "%DIAG_FILE%" echo.

>> "%DIAG_FILE%" echo [validate_install after-weekly]
if exist "%VENV_PY%" (
    if exist "%EIDP_APP_ROOT%\data\output\last_run.json" (
        "%VENV_PY%" "%EIDP_APP_ROOT%\scripts\validate_windows_install.py" "%EIDP_APP_ROOT%" --after-setup --after-weekly >> "%DIAG_FILE%" 2>&1
        set "VALIDATE_WEEKLY_RC=!ERRORLEVEL!"
        >> "%DIAG_FILE%" echo validate_after_weekly_rc=!VALIDATE_WEEKLY_RC!
    ) else (
        >> "%DIAG_FILE%" echo skipped; no last_run.json found
    )
) else (
    >> "%DIAG_FILE%" echo skipped; .venv Python is missing
)
>> "%DIAG_FILE%" echo.

>> "%DIAG_FILE%" echo [validate_install after-weekly require-ship-gate]
if exist "%VENV_PY%" (
    if exist "%EIDP_APP_ROOT%\data\output\last_run.json" (
        "%VENV_PY%" "%EIDP_APP_ROOT%\scripts\validate_windows_install.py" "%EIDP_APP_ROOT%" --after-setup --after-weekly --require-ship-gate >> "%DIAG_FILE%" 2>&1
        set "VALIDATE_WEEKLY_SHIP_GATE_RC=!ERRORLEVEL!"
        >> "%DIAG_FILE%" echo validate_after_weekly_ship_gate_rc=!VALIDATE_WEEKLY_SHIP_GATE_RC!
    ) else (
        >> "%DIAG_FILE%" echo skipped; no last_run.json found
    )
) else (
    >> "%DIAG_FILE%" echo skipped; .venv Python is missing
)
>> "%DIAG_FILE%" echo.

>> "%DIAG_FILE%" echo [final objective ship readiness]
if exist "%VENV_PY%" (
    "%VENV_PY%" -m eidp.cli report ship-readiness --json --fail-on-missing-goal >> "%DIAG_FILE%" 2>&1
    set "SHIP_READINESS_RC=!ERRORLEVEL!"
    >> "%DIAG_FILE%" echo ship_readiness_rc=!SHIP_READINESS_RC!
) else (
    >> "%DIAG_FILE%" echo skipped; .venv Python is missing
)
>> "%DIAG_FILE%" echo.

>> "%DIAG_FILE%" echo [latest discovery RCA batch plan]
powershell -NoProfile -Command "$root=$env:EIDP_APP_ROOT; $last=Join-Path $root 'data\output\last_run.json'; $path=$null; if (Test-Path -LiteralPath $last) { try { $json=Get-Content -LiteralPath $last -Raw | ConvertFrom-Json; $path=$json.discovery_rca.batch_plan_path } catch { Write-Output ('last_run_json_error=' + $_.Exception.Message) } }; if ($path) { if (-not [System.IO.Path]::IsPathRooted([string]$path)) { $path=Join-Path $root ([string]$path) } }; if (-not $path -or -not (Test-Path -LiteralPath $path)) { $dir=Join-Path $root 'data\output\target-year-discovery'; if (Test-Path -LiteralPath $dir) { $latest=Get-ChildItem -LiteralPath $dir -Filter '*-discovery-rca-batch-plan.json' -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1; if ($latest) { $path=$latest.FullName } } }; if ($path -and (Test-Path -LiteralPath $path)) { Write-Output $path; Get-Content -LiteralPath $path -TotalCount 240 } else { Write-Output 'none' }" >> "%DIAG_FILE%" 2>&1
>> "%DIAG_FILE%" echo.

set "LATEST_PROGRESS="
for /f "delims=" %%F in ('dir /b /o-d "%EIDP_APP_ROOT%\logs\bootstrap-pdfs-*.json" 2^>nul') do (
    if not defined LATEST_PROGRESS set "LATEST_PROGRESS=%%F"
)
>> "%DIAG_FILE%" echo [latest bootstrap progress]
if defined LATEST_PROGRESS (
    >> "%DIAG_FILE%" echo logs\%LATEST_PROGRESS%
    type "%EIDP_APP_ROOT%\logs\%LATEST_PROGRESS%" >> "%DIAG_FILE%"
) else (
    >> "%DIAG_FILE%" echo none
)
>> "%DIAG_FILE%" echo.

set "LATEST_BOOTSTRAP_LOG="
for /f "delims=" %%F in ('dir /b /o-d "%EIDP_APP_ROOT%\logs\bootstrap-pdfs-*.log" 2^>nul') do (
    if not defined LATEST_BOOTSTRAP_LOG set "LATEST_BOOTSTRAP_LOG=%%F"
)
>> "%DIAG_FILE%" echo [latest bootstrap log tail]
if defined LATEST_BOOTSTRAP_LOG (
    >> "%DIAG_FILE%" echo logs\%LATEST_BOOTSTRAP_LOG%
    powershell -NoProfile -Command "Get-Content -LiteralPath (Join-Path $env:EIDP_APP_ROOT 'logs\%LATEST_BOOTSTRAP_LOG%') -Tail 120" >> "%DIAG_FILE%" 2>&1
) else (
    >> "%DIAG_FILE%" echo none
)
>> "%DIAG_FILE%" echo.

echo [diagnose] wrote %DIAG_FILE%
endlocal & exit /b 0

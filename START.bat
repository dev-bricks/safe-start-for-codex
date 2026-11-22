@echo off
setlocal EnableExtensions
cd /d "%~dp0"

REM If run without arguments, or with 'tray', prioritize the compiled standalone GUI executable
if "%~1"=="" (
    if exist "%~dp0dist\CodexSafeStart.exe" (
        start "" "%~dp0dist\CodexSafeStart.exe"
        exit /b 0
    )
    if exist "C:\_Local_DEV\codex-safe-start\bin\CodexSafeStart.exe" (
        start "" "C:\_Local_DEV\codex-safe-start\bin\CodexSafeStart.exe"
        exit /b 0
    )
)

if /I "%~1"=="tray" (
    if exist "%~dp0dist\CodexSafeStart.exe" (
        start "" "%~dp0dist\CodexSafeStart.exe"
        exit /b 0
    )
    if exist "C:\_Local_DEV\codex-safe-start\bin\CodexSafeStart.exe" (
        start "" "C:\_Local_DEV\codex-safe-start\bin\CodexSafeStart.exe"
        exit /b 0
    )
)

REM CLI subcommands (start, status, dry-run, dashboard, backup, etc.)
set "PYTHONPATH=%~dp0src"
where py >nul 2>&1
if not errorlevel 1 (
    py -3 -m safe_start_for_codex %*
    exit /b %ERRORLEVEL%
)

where python >nul 2>&1
if not errorlevel 1 (
    python -m safe_start_for_codex %*
    exit /b %ERRORLEVEL%
)

where pythonw >nul 2>&1
if not errorlevel 1 (
    start "" pythonw -m safe_start_for_codex %*
    exit /b 0
)

echo [FEHLER] Weder CodexSafeStart.exe noch Python gefunden!
pause
exit /b 1

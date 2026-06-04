@echo off
cd /d "%~dp0"
python --version >nul 2>&1
if errorlevel 1 (
    echo [FEHLER] Python nicht gefunden!
    pause
    exit /b 1
)

set "PROJECT_ROOT=%CD%"
set "PYTHONPATH=%PROJECT_ROOT%\src;%PYTHONPATH%"
set "DIST_DIR=C:\_Local_DEV\codex-safe-start\bin"
set "WORK_DIR=C:\_Local_DEV\codex_build\safe-start-for-codex"
set "SPEC_DIR=C:\_Local_DEV\codex_build\safe-start-for-codex-spec"

python -m compileall -q src tests
if errorlevel 1 pause & exit /b 1

python -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name CodexSafeStart ^
  --paths "%PROJECT_ROOT%\src" ^
  --distpath "%DIST_DIR%" ^
  --workpath "%WORK_DIR%" ^
  --specpath "%SPEC_DIR%" ^
  "%PROJECT_ROOT%\src\safe_start_for_codex\tray_app.py"

if errorlevel 1 pause & exit /b 1
echo EXE erstellt: %DIST_DIR%\CodexSafeStart.exe

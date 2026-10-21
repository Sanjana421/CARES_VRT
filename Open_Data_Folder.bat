@echo off
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
    echo  Run Setup.bat first.
    pause
    exit /b 1
)
"venv\Scripts\python.exe" -c "import os; from modules import paths; os.makedirs(paths.DATA_DIR, exist_ok=True); os.startfile(paths.DATA_DIR)"

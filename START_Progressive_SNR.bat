@echo off
setlocal
cd /d "%~dp0"

if not defined LOCALAPPDATA set "LOCALAPPDATA=%USERPROFILE%\AppData\Local"
set "PYTHON_EXE=%LOCALAPPDATA%\CARES_VRT\venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo Python environment not found for this Windows account.
    echo Run START.bat once to complete setup, then try again.
    pause
    exit /b 1
)

"%PYTHON_EXE%" -m modules.progressive_snr
if errorlevel 1 pause

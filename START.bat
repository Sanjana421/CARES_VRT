@echo off
cd /d "%~dp0"
title CARES_VRT - keep this window open
if not exist "venv\.setup_ok" (
    call Setup.bat nopause
    if errorlevel 1 exit /b 1
)
"venv\Scripts\python.exe" main.py
if errorlevel 1 pause

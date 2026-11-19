@echo off
setlocal
cd /d "%~dp0"
title CARES_VRT - keep this window open

if not defined LOCALAPPDATA set "LOCALAPPDATA=%USERPROFILE%\AppData\Local"
set "APP_ENV=%LOCALAPPDATA%\CARES_VRT"
set "VENV_DIR=%APP_ENV%\venv"
set "SETUP_MARKER=%APP_ENV%\.setup_ok"

if not exist "%SETUP_MARKER%" (
    call "%~dp0Setup.bat" nopause
    if errorlevel 1 exit /b 1
)

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo  This account's Python environment is missing. Running setup...
    call "%~dp0Setup.bat" nopause
    if errorlevel 1 exit /b 1
)

"%VENV_DIR%\Scripts\python.exe" main.py
if errorlevel 1 pause


@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title CARES_VRT - Setup

if not defined LOCALAPPDATA set "LOCALAPPDATA=%USERPROFILE%\AppData\Local"
set "APP_ENV=%LOCALAPPDATA%\CARES_VRT"
set "VENV_DIR=%APP_ENV%\venv"
set "SETUP_MARKER=%APP_ENV%\.setup_ok"

echo.
echo  CARES_VRT setup for this Windows account
echo  -----------------------------------------
echo  Python environment: %VENV_DIR%
echo.

if not exist "main.py" (
    echo  [X] main.py not found. Put this .bat file in the CARES_VRT folder, next to main.py.
    pause
    exit /b 1
)

if not exist "%APP_ENV%" mkdir "%APP_ENV%"
if errorlevel 1 (
    echo  [X] Could not create the per-account app folder:
    echo      %APP_ENV%
    pause
    exit /b 1
)

rem Remove the completion marker until setup succeeds again.
if exist "%SETUP_MARKER%" del /q "%SETUP_MARKER%"

rem Remove this account's broken environment if its Python cannot start.
if exist "%VENV_DIR%\Scripts\python.exe" (
    "%VENV_DIR%\Scripts\python.exe" -c "import sys" >nul 2>&1
    if errorlevel 1 (
        echo  Existing Python environment is invalid. Recreating it...
        rmdir /s /q "%VENV_DIR%"
    )
)

set "PYCMD="
for %%V in (3.12 3.13 3.11 3.14 3.10) do (
    if not defined PYCMD (
        py -%%V -c "import sys" >nul 2>&1
        if !errorlevel! equ 0 set "PYCMD=py -%%V"
    )
)

if not defined PYCMD (
    python -c "import sys" >nul 2>&1
    if !errorlevel! equ 0 set "PYCMD=python"
)

if not defined PYCMD (
    echo  [X] Python was not found for this Windows account.
    echo      Install Python 3.10 or newer for this account, or ask IT to
    echo      install Python for all users. Then run Setup.bat again.
    pause
    exit /b 1
)

echo  [OK] Using this account's Python command: %PYCMD%

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo  Creating this account's virtual environment...
    %PYCMD% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo  [X] Could not create the virtual environment.
        pause
        exit /b 1
    )
)

echo  Installing packages...
"%VENV_DIR%\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo.
    echo  Pinned package versions failed. Trying compatible current versions...
    echo  requirements.txt will not be changed.
    "%VENV_DIR%\Scripts\python.exe" -m pip install --disable-pip-version-check numpy scipy sounddevice soundfile PySide6 openpyxl
    if errorlevel 1 (
        echo  [X] Package installation failed. Check the internet connection and run Setup.bat again.
        pause
        exit /b 1
    )
)

"%VENV_DIR%\Scripts\python.exe" -c "import numpy, scipy, soundfile, sounddevice, PySide6, openpyxl; print('  [OK] Required packages load')"
if errorlevel 1 (
    echo  [X] A required package did not load.
    pause
    exit /b 1
)

echo ok>"%SETUP_MARKER%"
if errorlevel 1 (
    echo  [X] Could not save the setup marker:
    echo      %SETUP_MARKER%
    pause
    exit /b 1
)

echo.
echo  Setup complete for this Windows account.
echo  Start the app with START.bat.
if /i not "%~1"=="nopause" pause
exit /b 0

@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title CARES_VRT - Setup
echo.
echo  CARES_VRT one-time setup for this PC
echo  ------------------------------------
if not exist "main.py" (
    echo  [X] main.py not found. Put these .bat files in the CARES_VRT folder, next to main.py.
    pause
    exit /b 1
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
    echo  [X] Python not found. Ask IT to install Python 3.11 or newer ^(64-bit, Add to PATH^).
    pause
    exit /b 1
)
echo  [OK] Using %PYCMD%
if not exist "venv\Scripts\python.exe" (
    echo  Creating virtual environment...
    %PYCMD% -m venv venv
    if errorlevel 1 ( echo  [X] Could not create venv. & pause & exit /b 1 )
)
echo  Installing packages ^(a few minutes^)...
"venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo.
    echo  Pinned versions in requirements.txt failed on this Python. Trying latest compatible versions instead
    echo  ^(requirements.txt itself is NOT changed^)...
    "venv\Scripts\python.exe" -m pip install --disable-pip-version-check numpy scipy sounddevice soundfile PySide6
    if errorlevel 1 ( echo  [X] Install failed. Check internet and run again. & pause & exit /b 1 )
)
"venv\Scripts\python.exe" -c "import numpy, scipy, soundfile, sounddevice, PySide6; print('  [OK] All packages load')"
if errorlevel 1 ( echo  [X] A package did not load. & pause & exit /b 1 )
echo ok> "venv\.setup_ok"
echo.
echo  Done. Start the app with Start_Collection.bat
if /i not "%~1"=="nopause" pause
exit /b 0

@echo off
cd /d "%~dp0"
title DistVRT Collection - Check collected data
if not exist "venv\Scripts\python.exe" (
    echo  Run Setup.bat first.
    pause
    exit /b 1
)
rem Optional:  Check_Data.bat 2004     (one participant)
"venv\Scripts\python.exe" tools\check_data.py %*
echo.
pause

@echo off
cd /d "%~dp0"
title DistVRT Collection - Check setup
if not exist "venv\Scripts\python.exe" (
    echo  Run Setup.bat first.
    pause
    exit /b 1
)
"venv\Scripts\python.exe" -m modules.preflight
echo.
set /p T= Play a quiet test tone through the speakers (left, then right)? [Y/N]: 
if /i "%T%"=="Y" "venv\Scripts\python.exe" -c "from modules.audio_engine import AudioEngine; AudioEngine().play_test_tone(); print('Done.')"
echo.
pause

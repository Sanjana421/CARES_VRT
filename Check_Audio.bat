@echo off
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" ( echo Run Setup.bat first. & pause & exit /b 1 )
"venv\Scripts\python.exe" -c "import sounddevice as sd; [print('%2d'%i, d['max_input_channels'], d['max_output_channels'], d['name']) for i,d in enumerate(sd.query_devices())]"
pause

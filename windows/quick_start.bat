@echo off
REM TriSonica Data Logger - Windows Quick Start
cd /d "%~dp0"
call venv\Scripts\activate.bat
echo Starting Trisonica Logger with auto-detection...
python datalogger.py --port auto
pause
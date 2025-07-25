@echo off
REM TriSonica Data Logger - Windows Runner
cd /d "%~dp0"
call venv\Scripts\activate.bat
python datalogger.py %*
pause
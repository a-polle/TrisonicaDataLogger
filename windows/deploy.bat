@echo off
REM TriSonica Data Logger - Windows Deployment Script
REM Optimized for Windows 10/11 desktop environments

setlocal enabledelayedexpansion

REM Colors (using escape sequences for Windows 10+)
for /F %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"
set "RED=%ESC%[91m"
set "GREEN=%ESC%[92m"
set "YELLOW=%ESC%[93m"
set "BLUE=%ESC%[94m"
set "NC=%ESC%[0m"

echo %BLUE%TriSonica Data Logger - Windows Deployment%NC%
echo ==============================================

REM Get script directory
set "SCRIPT_DIR=%~dp0"
set "INSTALL_DIR=%SCRIPT_DIR%"
set "LOG_DIR=%INSTALL_DIR%OUTPUT"
set "VENV_DIR=%INSTALL_DIR%venv"

REM Function to print status messages
goto :main

:print_status
echo %GREEN%[OK] %~1%NC%
goto :eof

:print_warning
echo %YELLOW%[WARNING] %~1%NC%
goto :eof

:print_error
echo %RED%[ERROR] %~1%NC%
goto :eof

:check_windows
REM Check if running on Windows
ver | findstr /i "Windows" >nul
if errorlevel 1 (
    call :print_error "This script is designed for Windows only"
    exit /b 1
)
call :print_status "Running on Windows"
goto :eof

:check_python
REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    call :print_error "Python is not installed or not in PATH"
    echo Please install Python from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%v"
call :print_status "Python !PYTHON_VERSION! found"
goto :eof

:check_pip
REM Check pip installation
python -m pip --version >nul 2>&1
if errorlevel 1 (
    call :print_error "pip is not available"
    echo Please ensure pip is installed with Python
    pause
    exit /b 1
)
call :print_status "pip is available"
goto :eof

:create_directories
echo %BLUE%Creating directories...%NC%
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
if not exist "%INSTALL_DIR%backups" mkdir "%INSTALL_DIR%backups"
call :print_status "Directories created"
goto :eof

:create_venv
echo %BLUE%Creating Python virtual environment...%NC%

if exist "%VENV_DIR%" (
    call :print_warning "Virtual environment already exists, recreating..."
    rmdir /s /q "%VENV_DIR%"
)

python -m venv "%VENV_DIR%"
if errorlevel 1 (
    call :print_error "Failed to create virtual environment"
    pause
    exit /b 1
)

REM Activate virtual environment
call "%VENV_DIR%\Scripts\activate.bat"

REM Upgrade pip
python -m pip install --upgrade pip
call :print_status "Virtual environment created"
goto :eof

:install_dependencies
echo %BLUE%Installing Python dependencies...%NC%

REM Activate virtual environment
call "%VENV_DIR%\Scripts\activate.bat"

REM Install required packages
python -m pip install pyserial rich psutil pywin32
if errorlevel 1 (
    call :print_error "Failed to install core dependencies"
    pause
    exit /b 1
)

REM Install optional packages
python -m pip install matplotlib numpy pandas windrose
if errorlevel 1 (
    call :print_warning "Some optional packages failed to install"
)

call :print_status "Dependencies installed"
goto :eof

:create_launchers
echo %BLUE%Creating launcher scripts...%NC%

REM Main launcher
echo @echo off > "%INSTALL_DIR%run_trisonica.bat"
echo cd /d "%INSTALL_DIR%" >> "%INSTALL_DIR%run_trisonica.bat"
echo call venv\Scripts\activate.bat >> "%INSTALL_DIR%run_trisonica.bat"
echo python datalogger.py %%* >> "%INSTALL_DIR%run_trisonica.bat"
echo pause >> "%INSTALL_DIR%run_trisonica.bat"

REM Quick start launcher
echo @echo off > "%INSTALL_DIR%quick_start.bat"
echo cd /d "%INSTALL_DIR%" >> "%INSTALL_DIR%quick_start.bat"
echo call venv\Scripts\activate.bat >> "%INSTALL_DIR%quick_start.bat"
echo echo Starting Trisonica Logger with auto-detection... >> "%INSTALL_DIR%quick_start.bat"
echo python datalogger.py --port auto >> "%INSTALL_DIR%quick_start.bat"
echo pause >> "%INSTALL_DIR%quick_start.bat"

REM Data visualization launcher
echo @echo off > "%INSTALL_DIR%visualize.bat"
echo cd /d "%INSTALL_DIR%" >> "%INSTALL_DIR%visualize.bat"
echo call venv\Scripts\activate.bat >> "%INSTALL_DIR%visualize.bat"
echo echo Starting Data Visualization Tool... >> "%INSTALL_DIR%visualize.bat"
echo python DataVis.py --gui >> "%INSTALL_DIR%visualize.bat"
echo pause >> "%INSTALL_DIR%visualize.bat"

REM Log viewer
echo @echo off > "%INSTALL_DIR%view_logs.bat"
echo cd /d "%INSTALL_DIR%" >> "%INSTALL_DIR%view_logs.bat"
echo echo Recent log files: >> "%INSTALL_DIR%view_logs.bat"
echo dir /b /o-d "%LOG_DIR%\*.csv" 2^>nul ^| findstr /n "^" >> "%INSTALL_DIR%view_logs.bat"
echo echo. >> "%INSTALL_DIR%view_logs.bat"
echo echo Latest data sample: >> "%INSTALL_DIR%view_logs.bat"
echo for /f %%f in ('dir /b /o-d "%LOG_DIR%\TrisonicaData_*.csv" 2^>nul') do ( >> "%INSTALL_DIR%view_logs.bat"
echo   echo File: %%f >> "%INSTALL_DIR%view_logs.bat"
echo   echo Last 10 lines: >> "%INSTALL_DIR%view_logs.bat"
echo   powershell "Get-Content '%LOG_DIR%\%%f' -Tail 10" >> "%INSTALL_DIR%view_logs.bat"
echo   goto :done >> "%INSTALL_DIR%view_logs.bat"
echo ^) >> "%INSTALL_DIR%view_logs.bat"
echo :done >> "%INSTALL_DIR%view_logs.bat"
echo pause >> "%INSTALL_DIR%view_logs.bat"

REM System info
echo @echo off > "%INSTALL_DIR%system_info.bat"
echo echo System Information: >> "%INSTALL_DIR%system_info.bat"
echo echo OS: >> "%INSTALL_DIR%system_info.bat"
echo ver >> "%INSTALL_DIR%system_info.bat"
echo echo. >> "%INSTALL_DIR%system_info.bat"
echo echo Computer: %%COMPUTERNAME%% >> "%INSTALL_DIR%system_info.bat"
echo echo User: %%USERNAME%% >> "%INSTALL_DIR%system_info.bat"
echo echo. >> "%INSTALL_DIR%system_info.bat"
echo call venv\Scripts\activate.bat >> "%INSTALL_DIR%system_info.bat"
echo python --version >> "%INSTALL_DIR%system_info.bat"
echo echo. >> "%INSTALL_DIR%system_info.bat"
echo echo Disk Usage: >> "%INSTALL_DIR%system_info.bat"
echo dir "%LOG_DIR%" /-c >> "%INSTALL_DIR%system_info.bat"
echo echo. >> "%INSTALL_DIR%system_info.bat"
echo echo Serial Ports: >> "%INSTALL_DIR%system_info.bat"
echo python -c "import serial.tools.list_ports; [print(f'{p.device} - {p.description}') for p in serial.tools.list_ports.comports()]" >> "%INSTALL_DIR%system_info.bat"
echo pause >> "%INSTALL_DIR%system_info.bat"

call :print_status "Launcher scripts created"
goto :eof

:test_installation
echo %BLUE%Testing installation...%NC%

call "%VENV_DIR%\Scripts\activate.bat"

REM Test Python imports
python -c "import serial, rich, psutil; print('All imports successful')" 2>nul
if errorlevel 1 (
    call :print_error "Python dependencies test failed"
    pause
    exit /b 1
)
call :print_status "Python dependencies test passed"

REM Test script syntax
python -m py_compile datalogger.py
if errorlevel 1 (
    call :print_error "Script syntax test failed"
    pause
    exit /b 1
)
call :print_status "Script syntax test passed"

call :print_status "Installation test completed"
goto :eof

:main
echo %BLUE%Starting Windows installation...%NC%

call :check_windows
call :check_python
call :check_pip
call :create_directories
call :create_venv
call :install_dependencies
call :create_launchers
call :test_installation

echo.
echo %GREEN%Installation complete!%NC%
echo.
echo Usage:
echo   Quick start:       double-click quick_start.bat
echo   Command line:      run_trisonica.bat [options]
echo   Data visualization: visualize.bat
echo   View logs:         view_logs.bat
echo   System info:       system_info.bat
echo.
echo Files:
echo   Application:     %INSTALL_DIR%
echo   Logs:           %LOG_DIR%
echo   Virtual env:    %VENV_DIR%
echo.
echo Command line options:
echo   Auto-detect:     run_trisonica.bat
echo   Specific port:   run_trisonica.bat --port COM3
echo   Show raw data:   run_trisonica.bat --show-raw
echo   Disable sound:   run_trisonica.bat --no-sound
echo   Custom log dir:  run_trisonica.bat --log-dir C:\MyLogs
echo.
echo Ready to start logging your Trisonica data!
echo.
set /p "response=Would you like to run a quick test? (y/N): "
if /i "!response!"=="y" (
    echo %BLUE%Running quick test...%NC%
    call quick_start.bat --help
)

pause
endlocal
@echo off
setlocal enabledelayedexpansion

REM Move to the directory where the batch file itself resides
cd /d %~dp0

REM Check Python version
python --version

REM Create venv
python -m venv venv

REM Venv activation
call venv\Scripts\activate.bat

REM Display version selection menu
echo.
echo ===================================
echo  Streamnotify on Bluesky Setup
echo ===================================
echo.
echo Select version to install:
echo   1. v1 (Legacy)
echo   2. v2 (Stable)
echo   3. v3 (Latest) - Recommended
echo.
set /p VERSION="Enter choice (1-3): "

REM Validate and set version directory
if "%VERSION%"=="1" (
    set "VERSION_DIR=v1"
    set "VERSION_NAME=v1"
) else if "%VERSION%"=="2" (
    set "VERSION_DIR=v2"
    set "VERSION_NAME=v2"
) else if "%VERSION%"=="3" (
    set "VERSION_DIR=v3"
    set "VERSION_NAME=v3"
) else (
    echo Invalid choice. Using v3 (default).
    set "VERSION_DIR=v3"
    set "VERSION_NAME=v3"
)

REM Move to selected version directory and install required packages
cd !VERSION_DIR!
echo.
echo Installing packages for !VERSION_NAME!...
pip install -r requirements.txt

REM Send completion message
echo.
echo ===================================
echo Installation completed. !VERSION_NAME! is ready.
echo ===================================

REM Pause on exit
pause

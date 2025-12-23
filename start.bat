@if not "%~0"=="%~dp0.\%~nx0" start /min cmd /c,"%~dp0.\%~nx0" %* & goto :eof
setlocal enabledelayedexpansion

REM Move to the directory where this batch file exists
cd /d %~dp0

REM Check Python version
python --version

REM Activate venv
call venv\Scripts\activate.bat

REM Display version selection menu
echo.
echo ===================================
echo  Streamnotify on Bluesky Launcher
echo ===================================
echo.
echo Select version to launch:
echo   1. v1 (Legacy)
echo   2. v2 (Stable)
echo   3. v3 (Latest) - Recommended
echo.
set /p VERSION="Enter choice (1-3): "

REM Validate and set version directory and main script
if "%VERSION%"=="1" (
    set "VERSION_DIR=v1"
    set "VERSION_NAME=v1"
    set "MAIN_SCRIPT=main_v1.py"
) else if "%VERSION%"=="2" (
    set "VERSION_DIR=v2"
    set "VERSION_NAME=v2"
    set "MAIN_SCRIPT=main_v2.py"
) else if "%VERSION%"=="3" (
    set "VERSION_DIR=v3"
    set "VERSION_NAME=v3"
    set "MAIN_SCRIPT=main_v3.py"
) else (
    echo Invalid choice. Using v3 (default).
    set "VERSION_DIR=v3"
    set "VERSION_NAME=v3"
    set "MAIN_SCRIPT=main_v3.py"
)

REM Move to selected version directory and launch
cd !VERSION_DIR!
echo.
echo Starting !VERSION_NAME! application...
python !MAIN_SCRIPT!

REM Pause when finished
pause

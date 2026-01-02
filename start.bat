@echo off
cd /d %~dp0

call venv\Scripts\activate.bat

set /p VERSION="Select version (1=v1, 2=v2, 3=v3): "

if "%VERSION%"=="1" cd v1 & python main_v1.py
if "%VERSION%"=="2" cd v2 & python main_v2.py
if "%VERSION%"=="3" cd v3 & python main_v3.py
if not "%VERSION%"=="1" if not "%VERSION%"=="2" if not "%VERSION%"=="3" (
    cd v3
    python main_v3.py
)

pause

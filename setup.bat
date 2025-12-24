@echo off
cd /d %~dp0

python -m venv venv

call venv\Scripts\activate.bat

set /p VERSION="Select version (1=v1, 2=v2, 3=v3): "

if "%VERSION%"=="1" (
    cd v1
    pip install -r requirements.txt
    if not exist settings.env copy settings.env.example settings.env
)

if "%VERSION%"=="2" (
    cd v2
    pip install -r requirements.txt
    if not exist settings.env copy settings.env.example settings.env
)

if "%VERSION%"=="3" (
    cd v3
    pip install -r requirements.txt
    if not exist settings.env copy settings.env.example settings.env
)

if not "%VERSION%"=="1" if not "%VERSION%"=="2" if not "%VERSION%"=="3" (
    cd v3
    pip install -r requirements.txt
    if not exist settings.env copy settings.env.example settings.env
)

echo.
echo Setup complete.
pause

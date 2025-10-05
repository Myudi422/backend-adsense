@echo off
echo AdSense API Backend Setup Script
echo ================================

echo.
echo Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found in PATH. Trying alternative commands...
    py --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo ERROR: Python is not installed or not in PATH.
        echo Please install Python 3.8+ from python.org
        echo Or from Microsoft Store, then add it to PATH.
        pause
        exit /b 1
    ) else (
        set PYTHON_CMD=py
    )
) else (
    set PYTHON_CMD=python
)

echo Python found: %PYTHON_CMD%
%PYTHON_CMD% --version

echo.
echo Installing required packages...
%PYTHON_CMD% -m pip install --upgrade pip
%PYTHON_CMD% -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo ERROR: Failed to install packages
    pause
    exit /b 1
)

echo.
echo Setup completed successfully!
echo.
echo You can now run the server with:
echo   %PYTHON_CMD% start_server.py --mode dev
echo.
echo Or install and run in one command:
echo   %PYTHON_CMD% start_server.py --install --mode dev
echo.
pause
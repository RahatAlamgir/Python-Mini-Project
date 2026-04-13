@echo off
setlocal

echo ==============================
echo   FULL PYTHON AUTO SETUP
echo ==============================

:: Check if Python exists
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python not found. Downloading Python...

    set PYTHON_INSTALLER=python_installer.exe
    set PYTHON_URL=https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe

    :: Download Python installer
    powershell -Command "Invoke-WebRequest -Uri %PYTHON_URL% -OutFile %PYTHON_INSTALLER%"

    if not exist %PYTHON_INSTALLER% (
        echo Failed to download Python installer!
        pause
        exit /b
    )

    echo Installing Python silently...
    %PYTHON_INSTALLER% /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1

    echo Waiting for installation to complete...
    timeout /t 10 >nul
) else (
    echo Python already installed.
)

:: Refresh PATH (important after install)
set "PATH=%PATH%;%LocalAppData%\Programs\Python\Python312\Scripts;%LocalAppData%\Programs\Python\Python312"

:: Check pip
echo.
echo Checking pip...
python -m pip --version >nul 2>nul
if %errorlevel% neq 0 (
    echo pip missing. Fixing...
    python -m ensurepip --upgrade
)

:: Upgrade pip
echo.
echo Upgrading pip...
python -m pip install --upgrade pip

:: Install packages
echo.
echo Installing Pillow...
python -m pip install pillow

echo Installing tkinterdnd2...
python -m pip install tkinterdnd2

echo.
echo ==============================
echo   EVERYTHING DONE SUCCESSFULLY
echo ==============================
pause
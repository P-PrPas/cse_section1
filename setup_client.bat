@echo off
setlocal

cd /d "%~dp0"

echo =========================================
echo Exam Registration System Client Setup
echo =========================================
echo.

set PYTHON_EXE=

call :resolve_python
if not defined PYTHON_EXE (
    echo Python 3.12 was not found.
    echo Trying to install Python 3.12 with winget...
    echo.

    where winget >nul 2>nul
    if errorlevel 1 (
        echo Error: winget was not found.
        echo Install Python 3.12 x64 manually, then rerun setup_client.bat
        goto :error
    )

    winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements --silent
    if errorlevel 1 (
        echo Error: Automatic Python installation failed.
        echo Install Python 3.12 x64 manually, then rerun setup_client.bat
        goto :error
    )

    call :resolve_python
    if not defined PYTHON_EXE (
        echo Error: Python 3.12 still not found after winget install.
        echo Open a new terminal or verify Python was installed successfully.
        goto :error
    )
)

echo Using Python: %PYTHON_EXE%
echo.

echo 1. Creating virtual environment...
"%PYTHON_EXE%" -m venv venv
if errorlevel 1 (
    echo Error: Failed to create virtual environment.
    goto :error
)

echo.
echo 2. Upgrading pip...
venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 (
    echo Error: Failed to upgrade pip.
    goto :error
)

echo.
echo 3. Installing Python packages...
venv\Scripts\python.exe -m pip install -r requirements.txt python-dotenv
if errorlevel 1 (
    echo Error: Failed to install Python packages.
    goto :error
)

echo.
echo 4. Installing Playwright Chromium...
set PLAYWRIGHT_BROWSERS_PATH=%CD%\ms-playwright
venv\Scripts\python.exe -m playwright install chromium
if errorlevel 1 (
    echo Error: Failed to install Playwright Chromium.
    goto :error
)

echo.
echo 5. Verifying runtime...
venv\Scripts\python.exe -c "import PySide6, cv2, playwright, dotenv, paddleocr, paddle"
if errorlevel 1 (
    echo Error: Runtime verification failed.
    goto :error
)

echo.
echo Setup completed successfully.
echo Run the application with run.bat
goto :end

:resolve_python
set PYTHON_EXE=

where py >nul 2>nul
if not errorlevel 1 (
    py -3.12 -c "import sys" >nul 2>nul
    if not errorlevel 1 (
        set PYTHON_EXE=py -3.12
        goto :eof
    )
)

where python >nul 2>nul
if not errorlevel 1 (
    python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>nul
    if not errorlevel 1 (
        set PYTHON_EXE=python
        goto :eof
    )
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe
    goto :eof
)

goto :eof

:error
echo.
echo Setup failed.
pause
exit /b 1

:end
endlocal

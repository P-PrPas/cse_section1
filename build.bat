@echo off
setlocal enabledelayedexpansion

pushd "%~dp0"

echo =========================================
echo ExamRegistrationSystem Build Script
echo =========================================

set "APP_NAME=ExamRegistrationSystem"
set "APP_VERSION=1.0.0"
set "OUTPUT_DIR=%CD%\setup_output"
set "PORTABLE_ROOT=%OUTPUT_DIR%\%APP_NAME%_Portable_%APP_VERSION%"
set "PORTABLE_APP_DIR=%PORTABLE_ROOT%\%APP_NAME%"
set "PORTABLE_ZIP=%OUTPUT_DIR%\%APP_NAME%_Portable_%APP_VERSION%.zip"
set "PYTHON_EXE="
set "PLAYWRIGHT_BROWSERS_DIR=%LOCALAPPDATA%\ms-playwright"
set "PLAYWRIGHT_STAGE_DIR=%CD%\build_assets\ms-playwright"

REM --- Find Python ---
for %%I in (
    "%LOCALAPPDATA%\Programs\Python\Python312"
    "%LOCALAPPDATA%\Programs\Python\Python313"
    "%LOCALAPPDATA%\Programs\Python\Python311"
    "%LOCALAPPDATA%\Programs\Python\Python310"
) do (
    if exist "%%~fI\python.exe" if not defined PYTHON_EXE set "PYTHON_EXE=%%~fI\python.exe"
)

if not defined PYTHON_EXE (
    for /f "delims=" %%I in ('where python.exe 2^>nul') do (
        if not defined PYTHON_EXE set "PYTHON_EXE=%%I"
    )
)

if not defined PYTHON_EXE (
    echo ERROR: python.exe not found.
    echo Install Python 3.12+ first, then run this script again.
    popd
    pause
    exit /b 1
)

echo Using Python: %PYTHON_EXE%

REM --- Check dependencies ---
echo.
echo 1. Checking dependencies...
"%PYTHON_EXE%" -c "import PySide6, cv2, playwright, dotenv, PyInstaller" >nul 2>nul
if errorlevel 1 (
    echo Required packages missing. Installing from requirements.txt...
    "%PYTHON_EXE%" -m pip install -r requirements.txt pyinstaller
    if errorlevel 1 goto :build_failed
)

REM --- Clean old builds ---
echo.
echo 2. Cleaning old builds...
rmdir /s /q build dist 2>nul
rmdir /s /q build_assets 2>nul
if exist "%PORTABLE_ROOT%" rmdir /s /q "%PORTABLE_ROOT%"
if exist "%PORTABLE_ZIP%" del /q "%PORTABLE_ZIP%"

REM --- Validate Playwright Chromium ---
echo.
echo 3. Validating Playwright Chromium bundle...
echo Using: %PLAYWRIGHT_BROWSERS_DIR%
if not exist "%PLAYWRIGHT_BROWSERS_DIR%" (
    echo ERROR: Playwright browser files not found in "%PLAYWRIGHT_BROWSERS_DIR%".
    echo Run "playwright install chromium" on the build machine first.
    goto :build_failed
)

set "PLAYWRIGHT_BROWSERS_PATH=%PLAYWRIGHT_BROWSERS_DIR%"
"%PYTHON_EXE%" -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); b = p.chromium.launch(headless=True); b.close(); p.stop(); print('Playwright Chromium smoke test passed.')"
if errorlevel 1 (
    echo ERROR: Playwright Chromium launch test failed.
    echo Reinstall the browser bundle with: python -m playwright install chromium
    goto :build_failed
)

REM --- Stage Playwright browsers ---
echo.
echo 4. Staging Playwright browser files...
robocopy "%PLAYWRIGHT_BROWSERS_DIR%" "%PLAYWRIGHT_STAGE_DIR%" /MIR /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 (
    echo ERROR: Failed to copy Playwright browser files into staging.
    goto :build_failed
)

REM --- Build with PyInstaller ---
echo.
echo 5. Building executable with PyInstaller...
echo This may take a few minutes...
"%PYTHON_EXE%" -m PyInstaller --noconfirm --onedir --windowed ^
    --name "%APP_NAME%" ^
    --collect-all playwright ^
    --collect-all greenlet ^
    --add-data "config.json:." ^
    --add-data "%PLAYWRIGHT_STAGE_DIR%:ms-playwright" ^
    main.py
if errorlevel 1 goto :build_failed

if not exist "dist\%APP_NAME%\%APP_NAME%.exe" (
    echo ERROR: Executable not found after PyInstaller build.
    goto :build_failed
)

REM --- Package portable release ---
echo.
echo 6. Packaging portable release...
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"
mkdir "%PORTABLE_ROOT%"
robocopy "dist\%APP_NAME%" "%PORTABLE_APP_DIR%" /MIR /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 (
    echo ERROR: Failed to stage portable application files.
    goto :build_failed
)

if exist ".env" copy /y ".env" "%PORTABLE_APP_DIR%\" >nul

(
echo @echo off
echo pushd "%%~dp0%APP_NAME%"
echo start "" "%APP_NAME%.exe"
echo popd
) > "%PORTABLE_ROOT%\StartHere.bat"

(
echo %APP_NAME% Portable Package v%APP_VERSION%
echo ==================================================
echo 1. Extract this ZIP to a normal folder on the client machine.
echo 2. Open the extracted folder.
echo 3. Double-click StartHere.bat to launch the application.
echo 4. Do NOT run the application from inside the ZIP viewer.
echo.
echo Notes:
echo - No Python installation required on the client machine.
echo - Keep the %APP_NAME% folder structure unchanged.
echo - The output folder will be created automatically next to the exe.
) > "%PORTABLE_ROOT%\README_PORTABLE.txt"

REM --- Create ZIP ---
echo.
echo 7. Creating ZIP...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path '%PORTABLE_ROOT%\*' -DestinationPath '%PORTABLE_ZIP%' -Force"
if errorlevel 1 (
    echo ERROR: Failed to create portable ZIP package.
    goto :build_failed
)

echo.
echo =========================================
echo Build complete!
echo Portable folder: %PORTABLE_ROOT%
echo Portable ZIP:    %PORTABLE_ZIP%
echo =========================================
popd
pause
exit /b 0

:build_failed
echo.
echo =========================================
echo Build failed. Check the error messages above.
echo =========================================
popd
pause
exit /b 1

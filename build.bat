@echo off
setlocal enabledelayedexpansion

echo Starting portable runtime build for Exam Registration System...

set APP_NAME=ExamRegistrationSystem
set APP_VERSION=1.0.0
set OUTPUT_DIR=output\%APP_NAME%_Portable_%APP_VERSION%
set ZIP_FILE=%OUTPUT_DIR%.zip
set OUTPUT_DIR_ABS=%CD%\%OUTPUT_DIR%
set ZIP_FILE_ABS=%CD%\%ZIP_FILE%
set BUILD_VENV=.build-venv
set BROWSERS_PATH=%CD%\ms-playwright

set BASE_PYTHON=
set BASE_PYTHON_DIR=

for /d %%d in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
    if exist "%%d\python.exe" (
        set BASE_PYTHON=%%d\python.exe
        goto :found_python
    )
)

if "%BASE_PYTHON%"=="" if exist "%CD%\venv\Scripts\python.exe" (
    "%CD%\venv\Scripts\python.exe" -c "import sys" >nul 2>nul
    if not errorlevel 1 (
        set BASE_PYTHON=%CD%\venv\Scripts\python.exe
    )
)

:found_python
if "%BASE_PYTHON%"=="" (
    echo Error: Python executable not found.
    goto :error
)

set BASE_PREFIX_FILE=%TEMP%\%APP_NAME%_base_prefix.txt
if exist "%BASE_PREFIX_FILE%" del /q "%BASE_PREFIX_FILE%"
"%BASE_PYTHON%" -c "import sys, pathlib; pathlib.Path(r'%BASE_PREFIX_FILE%').write_text(sys.base_prefix, encoding='utf-8')"
if errorlevel 1 (
    echo Error: Failed to query base Python directory.
    goto :error
)
set /p BASE_PYTHON_DIR=<"%BASE_PREFIX_FILE%"
if exist "%BASE_PREFIX_FILE%" del /q "%BASE_PREFIX_FILE%"
if not defined BASE_PYTHON_DIR (
    echo Error: Failed to resolve base Python directory.
    goto :error
)

echo Using base Python: %BASE_PYTHON%
echo Using base Python dir: %BASE_PYTHON_DIR%

if not exist "%BUILD_VENV%\Scripts\python.exe" (
    echo Creating build virtualenv...
    call "%BASE_PYTHON%" -m venv "%BUILD_VENV%"
    if errorlevel 1 (
        echo Error: Failed to create build virtualenv.
        goto :error
    )
)

set PYTHON_EXE=%CD%\%BUILD_VENV%\Scripts\python.exe
"%PYTHON_EXE%" -c "import sys" >nul 2>nul
if errorlevel 1 (
    echo Error: Build virtualenv is invalid.
    goto :error
)

echo Using build Python: %PYTHON_EXE%

echo Installing dependencies...
"%PYTHON_EXE%" -m pip install --no-cache-dir --upgrade pip
if errorlevel 1 (
    echo Error: Failed to upgrade pip.
    goto :error
)

"%PYTHON_EXE%" -m pip install --no-cache-dir -r requirements.txt
if errorlevel 1 (
    echo Error: Failed to install dependencies.
    goto :error
)

"%PYTHON_EXE%" -c "import PySide6, cv2, playwright, dotenv" >nul 2>nul
if errorlevel 1 (
    echo Error: Missing dependencies required for runtime package.
    goto :error
)

if exist output rmdir /s /q output
mkdir output

set PLAYWRIGHT_BROWSERS_PATH=%BROWSERS_PATH%
"%PYTHON_EXE%" -m playwright install chromium
if errorlevel 1 (
    echo Error: Failed to install Playwright Chromium.
    goto :error
)

if not exist "%BROWSERS_PATH%" (
    echo Error: Playwright browsers not found.
    goto :error
)

echo Smoke testing Playwright in non-frozen mode...
set PLAYWRIGHT_BROWSERS_PATH=%BROWSERS_PATH%
"%PYTHON_EXE%" -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); b = p.chromium.launch(headless=True); b.close(); p.stop()"
if errorlevel 1 (
    echo Error: Playwright smoke test failed.
    goto :error
)

echo Creating portable runtime package...
mkdir "%OUTPUT_DIR%"
mkdir "%OUTPUT_DIR%\python"
mkdir "%OUTPUT_DIR%\python\Lib"
mkdir "%OUTPUT_DIR%\python\Lib\site-packages"

echo Copying application source...
xcopy "%CD%\core" "%OUTPUT_DIR%\core\" /e /i /h /y >nul
xcopy "%CD%\ui" "%OUTPUT_DIR%\ui\" /e /i /h /y >nul
xcopy "%CD%\utils" "%OUTPUT_DIR%\utils\" /e /i /h /y >nul
copy /y "%CD%\main.py" "%OUTPUT_DIR%\" >nul
copy /y "%CD%\config.json" "%OUTPUT_DIR%\" >nul
if exist "%CD%\pdf_qr.png" copy /y "%CD%\pdf_qr.png" "%OUTPUT_DIR%\" >nul
if exist "%CD%\qr_code_gen.py" copy /y "%CD%\qr_code_gen.py" "%OUTPUT_DIR%\" >nul

echo Copying bundled Python runtime...
xcopy "%BASE_PYTHON_DIR%\*" "%OUTPUT_DIR%\python\" /e /i /h /y >nul
if errorlevel 1 (
    echo Error: Failed to copy base Python runtime.
    goto :error
)

if exist "%BASE_PYTHON_DIR%\pyvenv.cfg" (
    copy /y "%BASE_PYTHON_DIR%\pyvenv.cfg" "%OUTPUT_DIR%\python\" >nul
)

if not exist "%OUTPUT_DIR%\python\pyvenv.cfg" (
    (
        echo home = %BASE_PYTHON_DIR%
        echo include-system-site-packages = false
        echo version = 3.12
    ) > "%OUTPUT_DIR%\python\pyvenv.cfg"
)

echo Copying installed packages...
xcopy "%CD%\%BUILD_VENV%\Lib\site-packages\*" "%OUTPUT_DIR%\python\Lib\site-packages\" /e /i /h /y >nul
if errorlevel 1 (
    echo Error: Failed to copy Python packages.
    goto :error
)

echo Copying Playwright browsers...
xcopy "%BROWSERS_PATH%\*" "%OUTPUT_DIR%\ms-playwright\" /e /i /h /y >nul
if errorlevel 1 (
    echo Error: Failed to copy Playwright browsers.
    goto :error
)

dir /b "%OUTPUT_DIR%\ms-playwright\chromium-*" >nul 2>nul
if errorlevel 1 (
    echo Error: Chromium bundle not found in portable package.
    goto :error
)

echo Creating launcher...
echo @echo off > "%OUTPUT_DIR%\Run_%APP_NAME%.bat"
echo setlocal >> "%OUTPUT_DIR%\Run_%APP_NAME%.bat"
echo cd /d "%%~dp0" >> "%OUTPUT_DIR%\Run_%APP_NAME%.bat"
echo set PY_HOME=%%~dp0python >> "%OUTPUT_DIR%\Run_%APP_NAME%.bat"
echo set PATH=%%PY_HOME%%;%%PY_HOME%%\Scripts;%%PATH%% >> "%OUTPUT_DIR%\Run_%APP_NAME%.bat"
echo set PYTHONHOME=%%PY_HOME%% >> "%OUTPUT_DIR%\Run_%APP_NAME%.bat"
echo set PYTHONPATH=%%~dp0;%%PY_HOME%%\Lib;%%PY_HOME%%\Lib\site-packages >> "%OUTPUT_DIR%\Run_%APP_NAME%.bat"
echo set PLAYWRIGHT_BROWSERS_PATH=%%~dp0ms-playwright >> "%OUTPUT_DIR%\Run_%APP_NAME%.bat"
echo start "" "%%PY_HOME%%\pythonw.exe" "%%~dp0main.py" >> "%OUTPUT_DIR%\Run_%APP_NAME%.bat"

echo Creating console launcher...
echo @echo off > "%OUTPUT_DIR%\Run_%APP_NAME%_Console.bat"
echo setlocal >> "%OUTPUT_DIR%\Run_%APP_NAME%_Console.bat"
echo cd /d "%%~dp0" >> "%OUTPUT_DIR%\Run_%APP_NAME%_Console.bat"
echo set PY_HOME=%%~dp0python >> "%OUTPUT_DIR%\Run_%APP_NAME%_Console.bat"
echo set PATH=%%PY_HOME%%;%%PY_HOME%%\Scripts;%%PATH%% >> "%OUTPUT_DIR%\Run_%APP_NAME%_Console.bat"
echo set PYTHONHOME=%%PY_HOME%% >> "%OUTPUT_DIR%\Run_%APP_NAME%_Console.bat"
echo set PYTHONPATH=%%~dp0;%%PY_HOME%%\Lib;%%PY_HOME%%\Lib\site-packages >> "%OUTPUT_DIR%\Run_%APP_NAME%_Console.bat"
echo set PLAYWRIGHT_BROWSERS_PATH=%%~dp0ms-playwright >> "%OUTPUT_DIR%\Run_%APP_NAME%_Console.bat"
echo "%%PY_HOME%%\python.exe" "%%~dp0main.py" >> "%OUTPUT_DIR%\Run_%APP_NAME%_Console.bat"

echo Creating README...
echo Exam Registration System Portable Runtime %APP_VERSION% > "%OUTPUT_DIR%\README_PORTABLE.txt"
echo. >> "%OUTPUT_DIR%\README_PORTABLE.txt"
echo This package includes Python runtime, application source code, and Playwright Chromium. >> "%OUTPUT_DIR%\README_PORTABLE.txt"
echo. >> "%OUTPUT_DIR%\README_PORTABLE.txt"
echo How to use: >> "%OUTPUT_DIR%\README_PORTABLE.txt"
echo 1. Extract this ZIP to a normal folder. >> "%OUTPUT_DIR%\README_PORTABLE.txt"
echo 2. Run Run_%APP_NAME%.bat >> "%OUTPUT_DIR%\README_PORTABLE.txt"
echo 3. If you need logs in a console window, run Run_%APP_NAME%_Console.bat >> "%OUTPUT_DIR%\README_PORTABLE.txt"
echo. >> "%OUTPUT_DIR%\README_PORTABLE.txt"
echo Do not run directly from ZIP. >> "%OUTPUT_DIR%\README_PORTABLE.txt"
echo Do not move files out of this folder. >> "%OUTPUT_DIR%\README_PORTABLE.txt"

echo Creating ZIP...
if exist "%ZIP_FILE%" del "%ZIP_FILE%"
where tar.exe >nul 2>nul
if not errorlevel 1 (
    tar.exe -a -c -f "%ZIP_FILE_ABS%" -C "%OUTPUT_DIR_ABS%" .
)

if not exist "%ZIP_FILE%" (
    powershell -NoProfile -Command "Compress-Archive -Path '%OUTPUT_DIR_ABS%\*' -DestinationPath '%ZIP_FILE_ABS%' -Force"
)

if not exist "%ZIP_FILE%" (
    echo Error: ZIP creation failed.
    goto :error
)

echo.
echo Portable runtime build completed successfully.
echo Portable folder: %OUTPUT_DIR%
echo ZIP file: %ZIP_FILE%
goto :end

:error
echo Build failed.
exit /b 1

:end
endlocal

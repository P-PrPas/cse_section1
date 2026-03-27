@echo off
setlocal

cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo Error: Virtual environment not found.
    echo Run setup_client.bat first.
    goto :error
)

set PLAYWRIGHT_BROWSERS_PATH=%CD%\ms-playwright
venv\Scripts\python.exe main.py
if errorlevel 1 (
    echo.
    echo Application exited with an error.
    goto :error
)

goto :end

:error
pause
exit /b 1

:end
endlocal

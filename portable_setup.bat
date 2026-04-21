@echo off
setlocal

cd /d "%~dp0"

echo =========================================
echo Portable Setup Package Builder
echo =========================================
echo.
echo This will build a portable ZIP package that can be extracted and run directly.
echo.

call build.bat
if errorlevel 1 (
    echo.
    echo Portable setup build failed.
    pause
    exit /b 1
)

echo.
echo Portable setup package is ready in the output folder.
echo Look for the ZIP file created by build.bat.
pause

endlocal

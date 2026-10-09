@echo off
setlocal
cd /d "%~dp0"
echo.
echo LitRadar updater
echo ----------------
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0update_litradar.ps1"
set "UPDATE_EXIT_CODE=%ERRORLEVEL%"
echo.
if "%UPDATE_EXIT_CODE%"=="0" echo Update and checks completed successfully.
if not "%UPDATE_EXIT_CODE%"=="0" echo Updater stopped or failed with exit code %UPDATE_EXIT_CODE%.
echo.
echo Read the message above. Press any key to close this window.
pause >nul
exit /b %UPDATE_EXIT_CODE%

@echo off
setlocal
cd /d "%~dp0"
echo.
echo LitRadar updater / dependency refresh
echo ------------------------------------
if not exist "%~dp0.git" goto zip_install

echo Git checkout detected. Pulling source and refreshing all dependencies...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0update_litradar.ps1"
set "UPDATE_EXIT_CODE=%ERRORLEVEL%"
goto finish

:zip_install
echo ZIP installation detected: source code cannot be pulled without .git.
echo Refreshing core, UI, dev, and LLM dependency sets instead...
call "%~dp0setup_litradar.bat"
if errorlevel 1 (
  set "UPDATE_EXIT_CODE=1"
  goto finish
)
echo Dependencies refreshed successfully; source files were NOT updated.
echo Apply the next LitRadar patch or full ZIP manually to update the code.
set "UPDATE_EXIT_CODE=2"

:finish
echo.
if "%UPDATE_EXIT_CODE%"=="0" echo Update, dependencies, and checks completed successfully.
if "%UPDATE_EXIT_CODE%"=="2" echo Dependency refresh completed, but source update still requires a release patch.
if not "%UPDATE_EXIT_CODE%"=="0" if not "%UPDATE_EXIT_CODE%"=="2" echo Updater stopped or failed with exit code %UPDATE_EXIT_CODE%.
echo.
echo Read the message above. Press any key to close this window.
pause >nul
exit /b %UPDATE_EXIT_CODE%

@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Please run run_litradar.bat once first to create the virtual environment.
  pause
  exit /b 2
)
echo Installing a daily paper scan at 12:30 local time...
.venv\Scripts\python.exe cli.py schedule install --job scan --frequency daily --time 12:30
if errorlevel 1 goto failed
echo.
echo Installing a weekly digest at 09:00 every Sunday...
.venv\Scripts\python.exe cli.py schedule install --job digest --frequency weekly --time 09:00
if errorlevel 1 goto failed
echo.
echo Daily scan and weekly digest tasks installed. Use: python cli.py schedule status --job all
goto done
:failed
echo Schedule installation failed. See the error above.
set "SCHEDULE_EXIT_CODE=1"
goto end
:done
set "SCHEDULE_EXIT_CODE=0"
:end
echo.
echo Press any key to close this window.
pause >nul
exit /b %SCHEDULE_EXIT_CODE%

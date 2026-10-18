@echo off
setlocal
cd /d "%~dp0"
call "%~dp0setup_litbeacon.bat"
if errorlevel 1 goto failed
set "PYTHON=%~dp0.venv\Scripts\python.exe"
echo.
echo LitBeacon Telegram command listener
echo Keep this window open to receive Telegram commands and inline-button actions.
echo Scheduled digests still work independently via Windows Task Scheduler.
echo Press Ctrl+C to stop the listener.
echo.
"%PYTHON%" cli.py telegram-run
set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo Telegram listener exited with code %EXIT_CODE%.
pause
endlocal & exit /b %EXIT_CODE%

:failed
echo LitBeacon setup could not be completed.
pause
endlocal & exit /b 1

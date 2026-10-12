@echo off
setlocal
cd /d "%~dp0"
call "%~dp0setup_litradar.bat"
if errorlevel 1 goto failed
"%~dp0.venv\Scripts\python.exe" cli.py web %*
set "WEB_EXIT_CODE=%ERRORLEVEL%"
echo.
echo LitBeacon web workspace stopped with exit code %WEB_EXIT_CODE%.
pause >nul
exit /b %WEB_EXIT_CODE%
:failed
echo LitBeacon setup failed; see the messages above.
pause >nul
exit /b 1

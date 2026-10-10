@echo off
setlocal
cd /d "%~dp0"
call "%~dp0setup_litradar.bat"
if errorlevel 1 goto failed
set "PYTHON=%~dp0.venv\Scripts\python.exe"
if "%~1"=="" goto run_ui
"%PYTHON%" cli.py %*
set "EXIT_CODE=%ERRORLEVEL%"
endlocal & exit /b %EXIT_CODE%

:run_ui
"%PYTHON%" cli.py ui
set "EXIT_CODE=%ERRORLEVEL%"
endlocal & exit /b %EXIT_CODE%

:failed
echo LitRadar setup could not be completed.
pause
endlocal & exit /b 1

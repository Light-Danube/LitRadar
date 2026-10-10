@echo off
setlocal
cd /d "%~dp0"
call "%~dp0setup_litradar.bat"
if errorlevel 1 goto failed
call "%~dp0.venv\Scripts\activate.bat"
echo.
echo LitRadar CLI session
echo Project: %CD%
echo Examples: python cli.py --help ^| python cli.py search "context attribution" ^| python cli.py digest --period weekly
echo Type 'exit' to close this CLI session.
echo.
cmd /k
endlocal
exit /b 0

:failed
echo LitRadar setup could not be completed.
pause
endlocal & exit /b 1

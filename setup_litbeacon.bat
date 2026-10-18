@echo off
setlocal
cd /d "%~dp0"
set "VENV=%~dp0.venv"
set "PYTHON=%VENV%\Scripts\python.exe"
set "MARKER=%VENV%\.litbeacon-deps-1.0.0-local"

if not exist "%PYTHON%" (
  py -3.12 --version >nul 2>nul
  if errorlevel 1 (
    py -3.11 --version >nul 2>nul
    if errorlevel 1 goto missing_python
    py -3.11 -m venv "%VENV%"
  ) else (
    py -3.12 -m venv "%VENV%"
  )
  if errorlevel 1 goto venv_failed
)

"%PYTHON%" -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
if errorlevel 1 goto old_python

if not exist "%MARKER%" (
  echo Installing LitBeacon web, TUI and file-import dependencies...
  "%PYTHON%" -m pip install ".[web,ui,annotations]"
  if errorlevel 1 goto failed
  "%PYTHON%" -m pip check
  if errorlevel 1 goto failed
  echo ready>"%MARKER%"
)

"%PYTHON%" cli.py init
if errorlevel 1 goto failed
endlocal & exit /b 0

:missing_python
echo Python 3.12 or 3.11 was not found by the Windows py launcher.
echo Install Python 3.12 from python.org, reopen this window, then retry.
goto failed

:venv_failed
echo Python could not create .venv in this folder. Check the error above and folder permissions.
goto failed

:old_python
echo The existing .venv uses an older Python:
"%PYTHON%" --version
echo LitBeacon needs Python 3.11 or newer; Python 3.12 is recommended.
echo In a fresh extracted source folder, remove only its .venv after installing Python 3.12, then retry.
goto failed

:failed
echo.
echo LitBeacon setup failed. Read the first pip error above.
echo Python 3.12 is recommended. In a fresh source ZIP folder, retry after checking internet access.
echo No local database or offline papers were deleted.
echo Press any key to close this window.
pause >nul
endlocal & exit /b 1

@echo off
setlocal
cd /d "%~dp0"
set "VENV=%~dp0.venv"
set "PYTHON=%VENV%\Scripts\python.exe"
set "BACKUP=%~dp0.venv-before-python312"
set "MARKER=%VENV%\.litbeacon-deps-1.0.0-local"

if exist "%PYTHON%" goto check_existing
if exist "%VENV%" goto replace_existing
goto choose_python

:check_existing
"%PYTHON%" -c "import sys; sys.exit(0 if sys.version_info[:2] in ((3, 11), (3, 12)) else 1)" >nul 2>nul
if errorlevel 1 goto replace_existing
goto install

:replace_existing
echo The existing .venv cannot run this setup with Python 3.11 or 3.12.
echo It will be kept as .venv-before-python312; library data is separate.
if exist "%BACKUP%" goto backup_exists
if exist "%VENV%" goto choose_python
goto choose_python

:choose_python
py -3.12 --version >nul 2>nul
if not errorlevel 1 (
  set "PY_VERSION=3.12"
  goto create_venv
)
py -3.11 --version >nul 2>nul
if errorlevel 1 goto missing_python
set "PY_VERSION=3.11"

:create_venv
if exist "%VENV%" (
  move "%VENV%" "%BACKUP%" >nul
  if errorlevel 1 goto backup_failed
  echo Kept the old environment in .venv-before-python312.
)
echo Creating a fresh .venv with Python %PY_VERSION%...
py -%PY_VERSION% -m venv "%VENV%"
if errorlevel 1 goto venv_failed

:install
"%PYTHON%" --version
if not exist "%MARKER%" (
  echo Installing LitBeacon web and TUI dependencies...
  "%PYTHON%" -m pip install ".[web,ui]"
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

:backup_exists
echo .venv-before-python312 already exists. Rename it manually before retrying.
echo The current .venv and your library have not been changed.
goto failed

:backup_failed
echo Could not move .venv; close LitBeacon and other programs using it, then retry.
goto failed

:venv_failed
echo Python could not create .venv in this folder. Check the error above and folder permissions.
echo The previous environment remains in .venv-before-python312 if one was moved.
goto failed

:failed
echo.
echo LitBeacon setup failed. Read the first pip error above.
echo Python 3.12 is recommended. Check internet access if pip failed.
echo No local database or offline papers were deleted.
echo Press any key to close this window.
pause >nul
endlocal & exit /b 1

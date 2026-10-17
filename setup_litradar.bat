@echo off
setlocal
cd /d "%~dp0"
set "VENV=%~dp0.venv"
set "PYTHON=%VENV%\Scripts\python.exe"
set "MARKER=%VENV%\.litbeacon-deps-1.0.0-full"

if not exist "%PYTHON%" (
  where py >nul 2>nul
  if errorlevel 1 (
    python -m venv "%VENV%"
  ) else (
    py -3 -m venv "%VENV%"
  )
  if errorlevel 1 goto failed
)

if not exist "%MARKER%" (
  echo Installing LitBeacon core, UI, development, LLM and web workspace dependencies...
  "%PYTHON%" -m pip install --upgrade pip
  if errorlevel 1 goto failed
  "%PYTHON%" -m pip install -r requirements.txt -r requirements-ui.txt -r requirements-dev.txt -r requirements-llm.txt -r requirements-web.txt -r requirements-annotations.txt -r requirements-semantic.txt -r requirements-browser-tests.txt
  if errorlevel 1 goto failed
  echo ready>"%MARKER%"
)

"%PYTHON%" cli.py init
if errorlevel 1 goto failed
endlocal & exit /b 0

:failed
echo.
echo LitBeacon setup failed. Read the error above and check Python/internet access.
echo No local database or offline papers were deleted.
endlocal & exit /b 1

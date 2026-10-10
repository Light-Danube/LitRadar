@echo off
setlocal
cd /d "%~dp0"
set "VENV=%~dp0.venv"
set "PYTHON=%VENV%\Scripts\python.exe"
set "MARKER=%VENV%\.litradar-deps-0.7.1-full"

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
  echo Installing LitRadar core, UI, development, and LLM dependencies...
  "%PYTHON%" -m pip install --upgrade pip
  if errorlevel 1 goto failed
  "%PYTHON%" -m pip install -r requirements.txt -r requirements-ui.txt -r requirements-dev.txt -r requirements-llm.txt
  if errorlevel 1 goto failed
  echo ready>"%MARKER%"
)

"%PYTHON%" cli.py init
if errorlevel 1 goto failed
endlocal & exit /b 0

:failed
echo.
echo LitRadar setup failed. Read the error above and check Python/internet access.
echo No local database or offline papers were deleted.
endlocal & exit /b 1

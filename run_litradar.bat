@echo off
setlocal
cd /d "%~dp0"
set "VENV=%~dp0.venv"
if not exist "%VENV%\Scripts\python.exe" (
  where py >nul 2>nul
  if errorlevel 1 (
    python -m venv "%VENV%"
  ) else (
    py -3 -m venv "%VENV%"
  )
  if errorlevel 1 exit /b 1
)
if not exist "%VENV%\.litradar-deps-0.6.0" (
  "%VENV%\Scripts\python.exe" -m pip install --upgrade pip
  if errorlevel 1 exit /b 1
  "%VENV%\Scripts\python.exe" -m pip install -r requirements.txt -r requirements-ui.txt -r requirements-llm.txt -r requirements-dev.txt
  if errorlevel 1 exit /b 1
  echo ready>"%VENV%\.litradar-deps-0.6.0"
)
if "%~1"=="" (
  "%VENV%\Scripts\python.exe" cli.py ui
) else (
  "%VENV%\Scripts\python.exe" cli.py %*
)
exit /b %errorlevel%

@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0update_litradar.ps1"
exit /b %errorlevel%

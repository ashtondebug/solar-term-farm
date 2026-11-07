@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."

set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"

"%PY%" tools\build_web.py
if errorlevel 1 exit /b 1

echo Starting AgriVerse simulator on http://127.0.0.1:8080
"%PY%" tools\devserver.py --port 8080 --open
endlocal

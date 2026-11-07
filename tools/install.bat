@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."

echo === AgriVerse host setup ===
where python >nul 2>nul
if errorlevel 1 (
  echo Python 3 was not found on PATH. Install Python 3.10+ first.
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating .venv ...
  python -m venv .venv
  if errorlevel 1 exit /b 1
)

echo Installing host tools ...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt
if errorlevel 1 exit /b 1

echo.
echo Done. Next: start.bat
endlocal

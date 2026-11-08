@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."
python tools\provision_wifi.py --port COM10 %*
endlocal

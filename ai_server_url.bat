@echo off
chcp 65001 >nul
cd /d "%~dp0"
python ai_server_url.py
if errorlevel 1 python3 ai_server_url.py
echo.
pause

@echo off
chcp 65001 >nul
cd /d "%~dp0"
python ai_debug.py
if errorlevel 1 python3 ai_debug.py
echo.
pause

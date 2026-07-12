@echo off
chcp 65001 >nul
cd /d "%~dp0"
python ai_translate.py
if errorlevel 1 python3 ai_translate.py
echo.
pause

@echo off
chcp 65001 >nul
cd /d "%~dp0"
python compose_translate.py
if errorlevel 1 python3 compose_translate.py
echo.
pause

@echo off
chcp 65001 >nul
cd /d "%~dp0"
python label_format.py
if errorlevel 1 python3 label_format.py
echo.
pause

@echo off
chcp 65001 >nul
cd /d "%~dp0"
python translate_fixes.py
if errorlevel 1 python3 translate_fixes.py
echo.
pause

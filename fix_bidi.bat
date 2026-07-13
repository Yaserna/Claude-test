@echo off
chcp 65001 >nul
cd /d "%~dp0"
python fix_bidi.py
if errorlevel 1 python3 fix_bidi.py
echo.
pause

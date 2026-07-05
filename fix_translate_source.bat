@echo off
chcp 65001 >nul
cd /d "%~dp0"
python fix_translate_source.py
if errorlevel 1 python3 fix_translate_source.py
echo.
pause

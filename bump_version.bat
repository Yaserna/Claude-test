@echo off
chcp 65001 >nul
cd /d "%~dp0"
python bump_version.py
if errorlevel 1 python3 bump_version.py
echo.
pause

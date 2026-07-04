@echo off
chcp 65001 >nul
cd /d "%~dp0"
python rebrand.py
if errorlevel 1 python3 rebrand.py
echo.
pause

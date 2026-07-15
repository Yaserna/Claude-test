@echo off
chcp 65001 >nul
cd /d "%~dp0"
python snapshot.py save
if errorlevel 1 python3 snapshot.py save
echo.
pause

@echo off
chcp 65001 >nul
cd /d "%~dp0"
python inapp_rollback.py
if errorlevel 1 python3 inapp_rollback.py
echo.
pause

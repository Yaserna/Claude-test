@echo off
chcp 65001 >nul
cd /d "%~dp0"
python sleep_accounts.py
if errorlevel 1 python3 sleep_accounts.py
echo.
pause

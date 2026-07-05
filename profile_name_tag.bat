@echo off
chcp 65001 >nul
cd /d "%~dp0"
python profile_name_tag.py
if errorlevel 1 python3 profile_name_tag.py
echo.
pause

@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === YasTel update: refresh core + re-apply customizations ===
echo.
where git >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Git is not installed. Get it from: https://git-scm.com/download/win
  pause
  exit /b 1
)
python update.py
if errorlevel 1 python3 update.py
echo.
pause

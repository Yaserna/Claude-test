@echo off
chcp 65001 >nul
REM ------------------------------------------------------------
REM Startup-crash fix button -- just double-click this file.
REM ------------------------------------------------------------
cd /d "%~dp0"
echo.
echo Running fix_crash.py ...
echo.
python fix_crash.py
if errorlevel 1 (
  py fix_crash.py
)
echo.
echo Press any key to close this window.
pause >nul

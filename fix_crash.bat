@echo off
chcp 65001 >nul
REM ------------------------------------------------------------
REM دکمه‌ی رفع کرش باز شدن — کافی است این فایل را دابل‌کلیک کنی.
REM ------------------------------------------------------------
cd /d "%~dp0"
echo.
echo در حال اجرای fix_crash.py ...
echo.
python fix_crash.py
if errorlevel 1 (
  py fix_crash.py
)
echo.
echo برای بستن این پنجره یک دکمه بزن.
pause >nul

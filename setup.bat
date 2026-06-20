@echo off
setlocal enabledelayedexpansion
REM =====================================================================
REM  Custom Telegram Fork - Setup for Windows
REM  این اسکریپت سورس تلگرام را دانلود و تغییرات اختصاصی را اعمال می‌کند.
REM  پیش‌نیاز: Git و Python نصب باشند.
REM =====================================================================

echo === راه‌اندازی فورک اختصاصی تلگرام (ویندوز) ===
echo.

where git >nul 2>nul
if errorlevel 1 (
  echo [خطا] Git نصب نیست. از اینجا نصب کن: https://git-scm.com/download/win
  goto :fail
)

where python >nul 2>nul
if errorlevel 1 (
  echo [خطا] Python نصب نیست. از اینجا نصب کن: https://www.python.org/downloads/
  echo        هنگام نصب حتماً گزینه "Add Python to PATH" را تیک بزن.
  goto :fail
)

for /f "delims=" %%i in ('python -c "import json;print(json.load(open('build_config.json'))['upstream_repo'])"') do set REPO=%%i
for /f "delims=" %%i in ('python -c "import json;print(json.load(open('build_config.json'))['upstream_commit'])"') do set COMMIT=%%i

if exist Telegram (
  echo پوشه Telegram از قبل وجود دارد، از کلون رد می‌شویم.
) else (
  echo در حال دانلود سورس تلگرام... (حدود ۱ گیگابایت، کمی صبر کن)
  git clone %REPO% Telegram
  if errorlevel 1 (
    echo [خطا] دانلود سورس ناموفق بود.
    goto :fail
  )
)

echo در حال تنظیم روی نسخه‌ی ثابت‌شده %COMMIT% ...
git -C Telegram checkout %COMMIT%
if errorlevel 1 (
  echo [خطا] تنظیم نسخه ناموفق بود.
  goto :fail
)

echo در حال اعمال تغییرات اختصاصی...
python apply_mods.py
if errorlevel 1 (
  echo [خطا] اعمال تغییرات ناموفق بود.
  goto :fail
)

echo.
echo === تمام شد! ===
echo حالا پوشه‌ی "Telegram" را در Android Studio باز کن و Build بزن.
echo راهنمای کامل: فایل BUILD-GUIDE-FA.md را بخوان.
goto :end

:fail
echo.
echo راه‌اندازی متوقف شد. خطای بالا را برطرف کن و دوباره اجرا کن.
exit /b 1

:end
endlocal

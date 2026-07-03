@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
REM =====================================================================
REM  Custom Telegram Fork - Setup for Windows
REM  Downloads the Telegram source and applies our custom modifications.
REM  Requires: Git and Python.
REM =====================================================================

echo === Custom Telegram fork setup (Windows) ===
echo.

where git >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Git is not installed. Get it from: https://git-scm.com/download/win
  goto :fail
)

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python is not installed. Get it from: https://www.python.org/downloads/
  echo         During install, be sure to check "Add Python to PATH".
  goto :fail
)

for /f "delims=" %%i in ('python -c "import json;print(json.load(open('build_config.json'))['upstream_repo'])"') do set REPO=%%i
for /f "delims=" %%i in ('python -c "import json;print(json.load(open('build_config.json'))['upstream_commit'])"') do set COMMIT=%%i

if exist Telegram (
  echo Telegram folder already exists, skipping clone.
) else (
  echo Downloading the Telegram source... (about 1 GB, please wait)
  git clone %REPO% Telegram
  if errorlevel 1 (
    echo [ERROR] Source download failed.
    goto :fail
  )
)

echo Checking out the pinned commit %COMMIT% ...
git -C Telegram checkout %COMMIT%
if errorlevel 1 (
  echo [ERROR] Checkout failed.
  goto :fail
)

echo Applying custom modifications...
python apply_mods.py
if errorlevel 1 (
  echo [ERROR] Applying modifications failed.
  goto :fail
)

echo.
echo === Done! ===
echo Now open the "Telegram" folder in Android Studio and Build.
echo Full guide: see BUILD-GUIDE-FA.md
goto :end

:fail
echo.
echo Setup stopped. Fix the error above and run again.
exit /b 1

:end
endlocal

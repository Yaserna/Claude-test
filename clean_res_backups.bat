@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
REM Deletes leftover backup files (*.bak*) inside the res folder.
REM Such files (e.g. strings.xml.bak7) break the Android resource merger.
REM No Python needed. Double-click to run.

set CLEANED=0
for %%D in ("%~dp0Telegram\TMessagesProj\src\main\res" "%~dp0TMessagesProj\src\main\res" "%~dp0..\TMessagesProj\src\main\res" "C:\Users\Arbab\Desktop\Claude-test\Coding\Telegram-App\Telegram\TMessagesProj\src\main\res") do (
  if exist "%%~D" (
    echo Cleaning backups under: %%~D
    del /s /q "%%~D\*.bak*" 2>nul
    set CLEANED=1
    echo.
    echo Remaining .bak files ^(should list nothing^):
    dir /s /b "%%~D\*.bak*" 2>nul
    goto :done
  )
)
:done
if "%CLEANED%"=="0" (
  echo [ERROR] res folder not found. Put this file next to the Telegram folder and run again.
) else (
  echo.
  echo Done. Now build again in Android Studio.
)
echo.
pause

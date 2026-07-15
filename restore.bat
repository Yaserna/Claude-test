@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo This restores the NEWEST saved snapshot (undo the last changes).
echo Close Android Studio first.
set /p ok=Type Y to continue: 
if /I not "%ok%"=="Y" goto :eof
python snapshot.py restore
if errorlevel 1 python3 snapshot.py restore
echo.
pause

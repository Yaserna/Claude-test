@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Running phone_labels.py ...
python phone_labels.py
if errorlevel 1 (
  echo.
  echo Script finished with an error. Read the messages above.
)
echo.
pause

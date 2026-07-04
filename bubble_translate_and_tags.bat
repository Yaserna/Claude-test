@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Running bubble_translate_and_tags.py ...
python bubble_translate_and_tags.py
if errorlevel 1 (
  echo.
  echo Script finished with an error. Read the messages above.
)
echo.
pause

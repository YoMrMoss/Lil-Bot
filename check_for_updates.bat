@echo off
setlocal
cd /d "%~dp0"
py check_for_updates.py --download
echo.
pause


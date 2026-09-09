@echo off
setlocal
title Lil Bot Companion 1.11.0
cd /d "%~dp0"
echo Starting Lil Bot build 1.11.0...
py github_updater.py
if errorlevel 1 echo Update check was skipped; starting the installed version.
py -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Could not install Lil Bot requirements.
  pause
  exit /b 1
)
py companion.py
if errorlevel 1 (
  echo.
  echo If port 8765 is already in use, close the older Lil Bot command window
  echo and run this file again.
  pause
)

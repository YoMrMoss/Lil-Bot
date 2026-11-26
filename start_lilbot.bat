@echo off
setlocal
title Lil Bot Companion
cd /d "%~dp0"
echo Checking Lil Bot updates...
py github_updater.py
if errorlevel 1 echo Update check was skipped; starting the installed version.
py -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Could not install Lil Bot requirements.
  pause
  exit /b 1
)

if not exist "%~dp0companion.py" (
  echo Could not find companion.py in this folder.
  pause
  exit /b 1
)

py stop_lilbot.py
if errorlevel 1 exit /b 1
wscript.exe "%~dp0start_background.vbs"
echo Lil-Bot is running. Use its tray icon to restart or quit.
exit /b 0

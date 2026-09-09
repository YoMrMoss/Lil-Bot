@echo off
setlocal
title Lil Bot - GitHub Sync, Flash, and Start
cd /d "%~dp0"

echo ============================================================
echo   Lil Bot: GitHub update ^> firmware flash ^> companion
echo ============================================================
echo.
echo Close any other Lil Bot window and PlatformIO Serial Monitor.
echo Keep the display connected by USB.
echo.

py github_updater.py
if errorlevel 1 goto :failed

set "PIO=%USERPROFILE%\.platformio\penv\Scripts\platformio.exe"
if not exist "%PIO%" (
  echo PlatformIO was not found. Installing it for your Python account...
  py -m pip install platformio
  if errorlevel 1 goto :failed
  set "PIO=%USERPROFILE%\.platformio\penv\Scripts\platformio.exe"
)

echo.
echo Building and flashing the connected Lil Bot display...
"%PIO%" run --project-dir "%~dp0firmware" --target upload
if errorlevel 1 goto :failed

echo.
echo Firmware upload succeeded. Starting the companion...
call "%~dp0start_lilbot.bat"
exit /b %errorlevel%

:failed
echo.
echo Lil Bot update or flash did not complete. The existing firmware is safe.
echo Check that COM5 is not open in Serial Monitor, then try again.
pause
exit /b 1

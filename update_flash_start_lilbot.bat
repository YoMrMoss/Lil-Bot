@echo off
setlocal
title Lil Bot - GitHub Sync, Flash, and Start
cd /d "%~dp0"

echo ============================================================
echo   Lil Bot: GitHub update ^> firmware flash ^> companion
echo ============================================================
echo.
echo Quit Lil Bot from the system tray and close PlatformIO Serial Monitor.
echo Keep the display connected by USB.
echo.

py github_updater.py
if errorlevel 1 goto :failed

set "PIO=%USERPROFILE%\.platformio\penv\Scripts\platformio.exe"
echo.
echo Building and flashing the connected Lil Bot display...
if exist "%PIO%" (
  "%PIO%" run --project-dir "%~dp0firmware" --target upload
) else (
  py -m platformio --version >nul 2>&1
  if errorlevel 1 (
    echo Installing PlatformIO for your Python account...
    py -m pip install platformio
    if errorlevel 1 goto :failed
  )
  py -m platformio run --project-dir "%~dp0firmware" --target upload
)
if errorlevel 1 goto :failed

echo.
echo Firmware upload succeeded. Starting the companion...
call "%~dp0start_lilbot.bat"
exit /b %errorlevel%

:failed
echo.
echo Lil Bot update or flash did not complete.
echo Quit Lil Bot from the system tray and close Serial Monitor.
echo If the COM port disappeared, hold BOOT, tap RST, then release BOOT.
echo Check Device Manager for the board's bootloader COM port.
echo To select that port, open Command Prompt here and run:
echo   set "PLATFORMIO_UPLOAD_PORT=COM7"
echo   update_flash_start_lilbot.bat
echo Replace COM7 with the port shown in Device Manager.
pause
exit /b 1

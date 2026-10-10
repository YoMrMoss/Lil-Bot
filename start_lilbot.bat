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

rem Pass the folder through the environment to preserve spaces and apostrophes.
set "LILBOT_START_DIR=%~dp0"
rem Resolve the same Python used by py, then detach it with a hidden window.
rem Per-launch logs preserve errors without leaving a console open.
powershell.exe -NoLogo -NoProfile -NonInteractive -Command "$ErrorActionPreference='Stop'; try { $root=$env:LILBOT_START_DIR; $python=(& py -c 'import sys; print(sys.executable)'); if ($LASTEXITCODE -ne 0 -or -not $python) { throw 'Could not locate Python.' }; $python=($python | Select-Object -Last 1).Trim(); $logs=Join-Path $root 'logs'; New-Item -ItemType Directory -Force -Path $logs | Out-Null; $stamp=Get-Date -Format 'yyyyMMdd-HHmmss-fff'; $out=Join-Path $logs ('companion-'+$stamp+'.out.log'); $err=Join-Path $logs ('companion-'+$stamp+'.err.log'); $process=Start-Process -FilePath $python -ArgumentList @('-u','companion.py') -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err -PassThru; Write-Host ('Lil Bot launched in the background. PID: '+$process.Id); Write-Host ('Logs: '+$logs); exit 0 } catch { Write-Host ('Lil Bot launch failed: '+$_.Exception.Message); exit 1 }"
if errorlevel 1 (
  pause
  exit /b 1
)
exit /b 0

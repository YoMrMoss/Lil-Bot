@echo off
cd /d "%~dp0"
py stop_lilbot.py
if errorlevel 1 pause

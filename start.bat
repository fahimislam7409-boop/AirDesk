@echo off
title AirDesk Remote Desktop Server
cd /d "%~dp0"

echo ======================================================
echo    Starting AirDesk Server...
echo ======================================================
echo.

python server.py
pause

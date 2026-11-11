@echo off
title AetherDesk Remote Desktop Server
cd /d "%~dp0"

echo ======================================================
echo    Starting AetherDesk Server...
echo ======================================================
echo.

python server.py
pause

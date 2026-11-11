@echo off
title Stop AirDesk Server
cd /d "%~dp0"

echo Stopping AirDesk Server...

if exist "%~dp0airdesk.pid" (
    set /p PID=<"%~dp0airdesk.pid"
    if defined PID (
        taskkill /f /pid %PID% >nul 2>&1
    )
    del "%~dp0airdesk.pid" >nul 2>&1
)
if exist "%~dp0aetherdesk.pid" (
    del "%~dp0aetherdesk.pid" >nul 2>&1
)

taskkill /f /im AirDesk.exe >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /f /pid %%a >nul 2>&1
)

echo AirDesk Server is stopped.

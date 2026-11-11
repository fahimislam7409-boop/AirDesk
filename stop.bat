@echo off
title Stop AetherDesk Server
cd /d "%~dp0"

echo Stopping AetherDesk Server...

if exist "%~dp0aetherdesk.pid" (
    set /p PID=<"%~dp0aetherdesk.pid"
    if defined PID (
        taskkill /f /pid %PID% >nul 2>&1
    )
    del "%~dp0aetherdesk.pid" >nul 2>&1
)

for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /f /pid %%a >nul 2>&1
)

echo AetherDesk Server is stopped.

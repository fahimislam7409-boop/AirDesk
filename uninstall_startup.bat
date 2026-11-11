@echo off
setlocal enabledelayedexpansion
title Uninstall AirDesk Auto-Startup
cd /d "%~dp0"

:: Self-elevation to Administrator to clean up Firewall & Task Scheduler
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd.exe -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

echo ======================================================
echo    Uninstalling AirDesk Auto-Startup...
echo ======================================================
echo.

set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_FOLDER%\AirDesk.lnk"

echo [1/4] Removing Windows Firewall rules...
netsh advfirewall firewall delete rule name="AetherDesk" >nul 2>&1
netsh advfirewall firewall delete rule name="AetherDesk TCP" >nul 2>&1
netsh advfirewall firewall delete rule name="AetherDesk UDP Discovery" >nul 2>&1
netsh advfirewall firewall delete rule name="AirDesk" >nul 2>&1
netsh advfirewall firewall delete rule name="AirDesk TCP" >nul 2>&1
netsh advfirewall firewall delete rule name="AirDesk UDP Discovery" >nul 2>&1
echo       [OK] Firewall rules removed.

echo.
echo [2/4] Removing Scheduled Task...
schtasks /delete /tn "AetherDesk_Remote" /f >nul 2>&1
schtasks /delete /tn "AirDesk_Remote" /f >nul 2>&1
echo       [OK] Task Scheduler job deleted.

echo.
echo [3/4] Removing Windows Registry & Startup shortcut...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "AetherDesk_Remote" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "AirDesk_Remote" /f >nul 2>&1
if exist "%SHORTCUT_PATH%" del /f /q "%SHORTCUT_PATH%" >nul 2>&1
if exist "%STARTUP_FOLDER%\AetherDesk.lnk" del /f /q "%STARTUP_FOLDER%\AetherDesk.lnk" >nul 2>&1
echo       [OK] Startup entries cleaned!

echo.
echo [4/4] Stopping any running background instances...
call "%~dp0stop.bat"

echo.
echo ======================================================
echo  AirDesk has been completely uninstalled and stopped.
echo ======================================================
pause

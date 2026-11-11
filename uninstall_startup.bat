@echo off
setlocal enabledelayedexpansion
title Uninstall AirDesk Auto-Startup
cd /d "%~dp0"

echo ======================================================
echo    Uninstalling AirDesk Auto-Startup...
echo ======================================================
echo.

set "SCRIPT_DIR=%~dp0"
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

echo [1/4] Removing Windows Firewall rules...
netsh advfirewall firewall delete rule name="AetherDesk" >nul 2>&1
netsh advfirewall firewall delete rule name="AetherDesk TCP" >nul 2>&1
netsh advfirewall firewall delete rule name="AetherDesk UDP Discovery" >nul 2>&1
netsh advfirewall firewall delete rule name="AirDesk" >nul 2>&1
netsh advfirewall firewall delete rule name="AirDesk TCP" >nul 2>&1
netsh advfirewall firewall delete rule name="AirDesk UDP Discovery" >nul 2>&1
echo       [OK] Firewall rules removed.

echo.
echo [2/4] Removing Scheduled Tasks...
schtasks /delete /tn "AetherDesk_Remote" /f >nul 2>&1
schtasks /delete /tn "AirDesk_Remote" /f >nul 2>&1
echo       [OK] Task Scheduler jobs removed.

echo.
echo [3/4] Purging Registry and Startup shortcuts...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "AetherDesk_Remote" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "AirDesk_Remote" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "AirDesk" /f >nul 2>&1
reg delete "HKLM\Software\Microsoft\Windows\CurrentVersion\Run" /v "AetherDesk_Remote" /f >nul 2>&1
reg delete "HKLM\Software\Microsoft\Windows\CurrentVersion\Run" /v "AirDesk_Remote" /f >nul 2>&1

if exist "%STARTUP_FOLDER%\AirDesk.lnk" del /f /q "%STARTUP_FOLDER%\AirDesk.lnk" >nul 2>&1
if exist "%STARTUP_FOLDER%\AetherDesk.lnk" del /f /q "%STARTUP_FOLDER%\AetherDesk.lnk" >nul 2>&1
if exist "%STARTUP_FOLDER%\run_background.vbs" del /f /q "%STARTUP_FOLDER%\run_background.vbs" >nul 2>&1
if exist "%ALLUSERSPROFILE%\Microsoft\Windows\Start Menu\Programs\Startup\AirDesk.lnk" del /f /q "%ALLUSERSPROFILE%\Microsoft\Windows\Start Menu\Programs\Startup\AirDesk.lnk" >nul 2>&1
if exist "%ALLUSERSPROFILE%\Microsoft\Windows\Start Menu\Programs\Startup\AetherDesk.lnk" del /f /q "%ALLUSERSPROFILE%\Microsoft\Windows\Start Menu\Programs\Startup\AetherDesk.lnk" >nul 2>&1
if exist "%ALLUSERSPROFILE%\Microsoft\Windows\Start Menu\Programs\Startup\run_background.vbs" del /f /q "%ALLUSERSPROFILE%\Microsoft\Windows\Start Menu\Programs\Startup\run_background.vbs" >nul 2>&1
echo       [OK] All startup shortcuts and registry keys removed!

echo.
echo [4/4] Stopping any running background instances...
call "%SCRIPT_DIR%stop.bat"

echo.
echo ======================================================
echo  AirDesk has been completely uninstalled and stopped.
echo ======================================================
pause

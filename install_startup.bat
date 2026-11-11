@echo off
setlocal enabledelayedexpansion
title AirDesk Auto-Startup Installer
cd /d "%~dp0"

:: Self-elevation to Administrator for Firewall & Task Scheduler
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [i] Requesting Administrator privileges to configure Windows Firewall...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd.exe -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

echo ======================================================
echo    AirDesk Windows Auto-Startup Installer
echo ======================================================
echo.

set "SCRIPT_DIR=%~dp0"
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_FOLDER%\AirDesk.lnk"
set "PYTHONW_PATH=C:\Python312\pythonw.exe"

if not exist "!PYTHONW_PATH!" (
    for /f "tokens=*" %%i in ('where pythonw.exe 2^>nul') do set "PYTHONW_PATH=%%i"
)

echo [1/4] Configuring Windows Firewall for Port 8000 (TCP) & 8001 (UDP Discovery)...
netsh advfirewall firewall delete rule name="AetherDesk" >nul 2>&1
netsh advfirewall firewall delete rule name="AetherDesk TCP" >nul 2>&1
netsh advfirewall firewall delete rule name="AetherDesk UDP Discovery" >nul 2>&1
netsh advfirewall firewall delete rule name="AirDesk" >nul 2>&1
netsh advfirewall firewall delete rule name="AirDesk TCP" >nul 2>&1
netsh advfirewall firewall delete rule name="AirDesk UDP Discovery" >nul 2>&1
netsh advfirewall firewall add rule name="AirDesk TCP" dir=in action=allow protocol=TCP localport=8000 profile=any >nul 2>&1
netsh advfirewall firewall add rule name="AirDesk UDP Discovery" dir=in action=allow protocol=UDP localport=8001 profile=any >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo       [OK] Windows Firewall rules added (Port 8000 TCP and 8001 UDP allowed on Public & Private networks)!
) else (
    echo       [*] Firewall rule could not be set automatically.
)

echo.
echo [2/4] Registering Task Scheduler (Runs automatically at Windows Logon)...
schtasks /delete /tn "AetherDesk_Remote" /f >nul 2>&1
schtasks /delete /tn "AirDesk_Remote" /f >nul 2>&1
schtasks /create /tn "AirDesk_Remote" /tr "\"!PYTHONW_PATH!\" \"%SCRIPT_DIR%server.py\" --silent" /sc onlogon /rl highest /f >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo       [OK] Task Scheduler job registered with Highest Privileges!
) else (
    echo       [*] Standard auto-startup configured.
)

echo.
echo [3/4] Adding to Windows Registry & Startup folder...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "AetherDesk_Remote" /f >nul 2>&1
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "AirDesk_Remote" /t REG_SZ /d "\"!PYTHONW_PATH!\" \"%SCRIPT_DIR%server.py\" --silent" /f >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath = '!PYTHONW_PATH!'; $s.Arguments = '\"%SCRIPT_DIR%server.py\" --silent'; $s.WorkingDirectory = '%SCRIPT_DIR%'; $s.Save()" >nul 2>&1
echo       [OK] Registry and Startup shortcut created!

echo.
echo [4/4] Starting AirDesk Server in background...
call "%SCRIPT_DIR%stop.bat" >nul 2>&1
start "" "!PYTHONW_PATH!" "%SCRIPT_DIR%server.py" --silent

timeout /t 2 >nul 2>&1

for /f "tokens=*" %%i in ('powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias 'Wi-Fi*','Ethernet*' | Where-Object { $_.IPAddress -notlike '127*' -and $_.IPAddress -notlike '169*' } | Select-Object -First 1).IPAddress" 2^>nul') do set "LOCAL_IP=%%i"
if "%LOCAL_IP%"=="" set "LOCAL_IP=localhost"

echo.
echo ======================================================
echo    SUCCESS! AirDesk is now ACTIVE & RUNNING!
echo ======================================================
echo.
echo  1. The server is now running invisibly in the background.
echo  2. Open your Tablet or Phone browser or App:
echo     👉 http://%LOCAL_IP%:8000
echo  3. Default Security PIN: 123456
echo.
echo  Whenever you turn on your PC, AirDesk will 
echo  automatically start without doing anything!
echo ======================================================
echo.
pause

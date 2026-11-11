@echo off
setlocal enabledelayedexpansion
title AirDesk Auto-Startup Installer
cd /d "%~dp0"

echo ======================================================
echo    AirDesk Windows Auto-Startup Installer
echo ======================================================
echo.

set "SCRIPT_DIR=%~dp0"
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_FOLDER%\AirDesk.lnk"

:: Step 0: Aggressive Legacy Cleanup (Fix for "Can not find script file run_background.vbs")
echo [1/4] Deep cleaning any legacy or broken startup scripts...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "AetherDesk_Remote" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "AirDesk_Remote" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "AirDesk" /f >nul 2>&1
reg delete "HKLM\Software\Microsoft\Windows\CurrentVersion\Run" /v "AetherDesk_Remote" /f >nul 2>&1
reg delete "HKLM\Software\Microsoft\Windows\CurrentVersion\Run" /v "AirDesk_Remote" /f >nul 2>&1
schtasks /delete /tn "AetherDesk_Remote" /f >nul 2>&1
schtasks /delete /tn "AirDesk_Remote" /f >nul 2>&1

if exist "%STARTUP_FOLDER%\AetherDesk.lnk" del /f /q "%STARTUP_FOLDER%\AetherDesk.lnk" >nul 2>&1
if exist "%STARTUP_FOLDER%\run_background.vbs" del /f /q "%STARTUP_FOLDER%\run_background.vbs" >nul 2>&1
if exist "%SCRIPT_DIR%run_background.vbs" del /f /q "%SCRIPT_DIR%run_background.vbs" >nul 2>&1
if exist "%ALLUSERSPROFILE%\Microsoft\Windows\Start Menu\Programs\Startup\AetherDesk.lnk" del /f /q "%ALLUSERSPROFILE%\Microsoft\Windows\Start Menu\Programs\Startup\AetherDesk.lnk" >nul 2>&1
if exist "%ALLUSERSPROFILE%\Microsoft\Windows\Start Menu\Programs\Startup\run_background.vbs" del /f /q "%ALLUSERSPROFILE%\Microsoft\Windows\Start Menu\Programs\Startup\run_background.vbs" >nul 2>&1
echo       [OK] Legacy entries purged completely.

:: Step 1: Detect Standalone AirDesk.exe or Python environment
echo.
echo [2/4] Detecting runtime engine...
if exist "%SCRIPT_DIR%AirDesk.exe" (
    set "EXE_TARGET=%SCRIPT_DIR%AirDesk.exe"
    set "EXE_ARGS=--silent"
    set "ICON_TARGET=%SCRIPT_DIR%AirDesk.exe"
    echo       [OK] Found Standalone Desktop App: AirDesk.exe
) else (
    set "PYTHONW_PATH=C:\Python312\pythonw.exe"
    if not exist "!PYTHONW_PATH!" (
        for /f "tokens=*" %%i in ('where pythonw.exe 2^>nul') do set "PYTHONW_PATH=%%i"
    )
    set "EXE_TARGET=!PYTHONW_PATH!"
    set "EXE_ARGS=\"%SCRIPT_DIR%server.py\" --silent"
    set "ICON_TARGET=%SCRIPT_DIR%airdesk.ico"
    echo       [OK] Using Python runtime: !PYTHONW_PATH!
)

:: Step 2: Configure Windows Firewall
echo.
echo [3/4] Configuring Windows Firewall for Port 8000 & 8001...
netsh advfirewall firewall delete rule name="AetherDesk" >nul 2>&1
netsh advfirewall firewall delete rule name="AetherDesk TCP" >nul 2>&1
netsh advfirewall firewall delete rule name="AetherDesk UDP Discovery" >nul 2>&1
netsh advfirewall firewall delete rule name="AirDesk TCP" >nul 2>&1
netsh advfirewall firewall delete rule name="AirDesk UDP Discovery" >nul 2>&1
netsh advfirewall firewall add rule name="AirDesk TCP" dir=in action=allow protocol=TCP localport=8000 profile=any >nul 2>&1
netsh advfirewall firewall add rule name="AirDesk UDP Discovery" dir=in action=allow protocol=UDP localport=8001 profile=any >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo       [OK] Firewall rules configured successfully!
) else (
    echo       [*] Note: To enable external network access, run this installer as Administrator.
)

:: Step 3: Create Single Clean Auto-Startup Shortcut
echo.
echo [4/4] Creating Windows Startup shortcut...
if exist "%SHORTCUT_PATH%" del /f /q "%SHORTCUT_PATH%" >nul 2>&1

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath = '%EXE_TARGET%'; $s.Arguments = '%EXE_ARGS%'; $s.WorkingDirectory = '%SCRIPT_DIR%'; if (Test-Path '%ICON_TARGET%') { $s.IconLocation = '%ICON_TARGET%,0' }; $s.Description = 'AirDesk Personal Remote Desktop Auto-Starter'; $s.Save()" >nul 2>&1

echo       [OK] Auto-startup created at: %SHORTCUT_PATH%

:: Stop any old process and start background instance
call "%SCRIPT_DIR%stop.bat" >nul 2>&1
start "" "%EXE_TARGET%" %EXE_ARGS%

timeout /t 2 >nul 2>&1

for /f "tokens=*" %%i in ('powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias 'Wi-Fi*','Ethernet*' | Where-Object { $_.IPAddress -notlike '127*' -and $_.IPAddress -notlike '169*' } | Select-Object -First 1).IPAddress" 2^>nul') do set "LOCAL_IP=%%i"
if "%LOCAL_IP%"=="" set "LOCAL_IP=localhost"

echo.
echo ======================================================
echo    SUCCESS: AirDesk is now ACTIVE and RUNNING
echo ======================================================
echo.
echo  1. The server is now running invisibly in the background.
echo  2. Open your Tablet or Phone browser or App:
echo     --^> http://%LOCAL_IP%:8000
echo  3. Default Security PIN: 123456
echo.
echo  Whenever you turn on your PC, AirDesk will 
echo  automatically start cleanly without any popups.
echo ======================================================
echo.
pause

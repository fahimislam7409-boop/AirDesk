@echo off
setlocal enabledelayedexpansion
title AirDesk - Setup & Installer
cd /d "%~dp0"

:: Self-elevation to Administrator for Firewall
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [i] Requesting Administrator privileges for firewall setup...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd.exe -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

echo ============================================================
echo   ⚡ AirDesk - Universal One-Click Setup
echo ============================================================
echo.

:: Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to PATH.
    echo Please install Python 3.10 or newer from https://www.python.org/
    echo Remember to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo [1/3] Installing Python dependencies (requirements.txt)...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r "%~dp0requirements.txt"
if %errorlevel% neq 0 (
    echo [!] Retrying pip install with user flag...
    pip install -r "%~dp0requirements.txt" --user
)
echo       [OK] Dependencies installed successfully!
echo.

echo [2/3] Configuring Windows Defender Firewall (TCP 8000 & UDP 8001)...
netsh advfirewall firewall delete rule name="AetherDesk" >nul 2>&1
netsh advfirewall firewall delete rule name="AetherDesk TCP" >nul 2>&1
netsh advfirewall firewall delete rule name="AetherDesk UDP Discovery" >nul 2>&1
netsh advfirewall firewall delete rule name="AirDesk" >nul 2>&1
netsh advfirewall firewall delete rule name="AirDesk TCP" >nul 2>&1
netsh advfirewall firewall delete rule name="AirDesk UDP Discovery" >nul 2>&1
netsh advfirewall firewall add rule name="AirDesk TCP" dir=in action=allow protocol=TCP localport=8000 profile=any >nul 2>&1
netsh advfirewall firewall add rule name="AirDesk UDP Discovery" dir=in action=allow protocol=UDP localport=8001 profile=any >nul 2>&1
echo       [OK] Firewall rules configured for local streaming and LAN auto-discovery!
echo.

echo [3/3] Creating default configuration...
if not exist "%~dp0config.json" (
    echo { "host": "0.0.0.0", "port": 8000, "pin": "123456", "fps": 30, "quality": 75, "scale": 1.0, "default_mode": "touchpad" } > "%~dp0config.json"
    echo       [OK] config.json created with default PIN 123456.
) else (
    echo       [OK] config.json already exists.
)
echo.

echo ============================================================
echo   🎉 SETUP COMPLETED SUCCESSFULLY!
echo ============================================================
echo.
echo   • To run now in terminal with QR code : start.bat
echo   • To enable automatic startup with PC : install_startup.bat
echo   • Install on your Tablet / Phone      : AirDesk.apk
echo.

set /p LAUNCH="Would you like to start AirDesk now? (Y/N): "
if /i "!LAUNCH!"=="Y" (
    start "" "%~dp0start.bat"
)


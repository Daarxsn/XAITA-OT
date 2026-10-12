@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_windows.ps1"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" echo Setup failed. Read the message above and logs\setup-install.log if it exists.
pause
exit /b %RC%

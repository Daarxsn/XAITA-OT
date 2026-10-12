@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch_windows.ps1"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo Dashboard failed. Check logs\dashboard-stderr.log and logs\dashboard-stdout.log.
  pause
)
exit /b %RC%

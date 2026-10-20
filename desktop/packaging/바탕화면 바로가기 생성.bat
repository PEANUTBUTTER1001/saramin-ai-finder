@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0create_shortcut.ps1"
set "SHORTCUT_RESULT=%ERRORLEVEL%"
pause
exit /b %SHORTCUT_RESULT%

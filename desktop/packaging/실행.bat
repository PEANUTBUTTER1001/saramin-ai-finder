@echo off
setlocal
set "APP_HOME=%~dp0"
if not exist "%APP_HOME%runtime\pythonw.exe" (
  echo Python runtime is missing. Please restore the complete app folder.
  pause
  exit /b 1
)
start "" "%APP_HOME%runtime\pythonw.exe" -m saramin_finder.main
exit /b 0

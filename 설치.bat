@echo off
chcp 65001 >nul
setlocal
rem 사람인 공고 관리 PC 앱을 준비하고 바탕화면 바로가기를 만든 뒤 실행한다.
set "APP_HOME=%~dp0desktop\dist\SaraminFinder"

set "PY="
py -3 -c "import sys, pip; sys.exit(sys.version_info < (3, 9))" >nul 2>&1 && set "PY=py -3"
if not defined PY python -c "import sys, pip; sys.exit(sys.version_info < (3, 9))" >nul 2>&1 && set "PY=python"

rem Python이 없으면 저장소 안에만 쓰는 공식 내장용 Python과 pip를 받는다. 시스템에는 설치하지 않는다.
rem 경로에 괄호가 있어도 깨지지 않도록 괄호 블록 대신 한 줄 조건문을 쓴다.
rem 내장용 Python 버전과 파일명은 desktop\packaging\build_portable.py와 맞춘다.
set "CACHE=%~dp0desktop\.cache"
set "BOOT=%CACHE%\python-boot"
set "EMBED=%CACHE%\python-3.12.10-embed-amd64.zip"
set "EMBED_URL=https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip"
set "PIP_URL=https://bootstrap.pypa.io/pip/zipapp/pip-26.2.2.pyz"
set "NEED_BOOT="
if not defined PY if not exist "%BOOT%\pip.pyz" set "NEED_BOOT=1"
if defined NEED_BOOT echo [0/3] Python이 없어 앱 준비용 Python을 내려받습니다. 시스템에는 설치하지 않습니다.
if defined NEED_BOOT if exist "%BOOT%" rd /s /q "%BOOT%"
if defined NEED_BOOT mkdir "%BOOT%"
if defined NEED_BOOT if not exist "%EMBED%" curl -fsSL --retry 2 -o "%EMBED%.part" "%EMBED_URL%" && move /y "%EMBED%.part" "%EMBED%" >nul
if defined NEED_BOOT if exist "%EMBED%" tar -xf "%EMBED%" -C "%BOOT%"
if defined NEED_BOOT if exist "%BOOT%\python.exe" >"%BOOT%\python312._pth" echo python312.zip
if defined NEED_BOOT if exist "%BOOT%\python.exe" >>"%BOOT%\python312._pth" echo .
if defined NEED_BOOT if exist "%BOOT%\python.exe" >>"%BOOT%\python312._pth" echo pip.pyz
if defined NEED_BOOT if exist "%BOOT%\python.exe" >>"%BOOT%\python312._pth" echo import site
if defined NEED_BOOT if exist "%BOOT%\python.exe" curl -fsSL --retry 2 -o "%BOOT%\pip.pyz.part" "%PIP_URL%" && move /y "%BOOT%\pip.pyz.part" "%BOOT%\pip.pyz" >nul
if not defined PY if exist "%BOOT%\pip.pyz" set PY="%BOOT%\python.exe"
if not defined PY (
  echo 앱 준비용 Python을 내려받지 못했습니다. 인터넷 연결을 확인한 뒤 다시 실행해 주세요.
  pause
  exit /b 1
)

echo [1/3] 앱을 준비합니다. 처음에는 내려받기 때문에 몇 분 걸릴 수 있습니다.
%PY% "%~dp0desktop\packaging\build_portable.py"
if errorlevel 1 (
  echo.
  echo 준비하지 못했습니다. 위 메시지를 확인해 주세요.
  pause
  exit /b 1
)

echo [2/3] 바탕화면 바로가기를 만듭니다.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$d = $env:APP_HOME; $s = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) '사람인 공고 관리.lnk')); $s.TargetPath = (Join-Path $d 'runtime\pythonw.exe'); $s.Arguments = '-m saramin_finder.main'; $s.WorkingDirectory = $d; $s.IconLocation = \"$env:SystemRoot\System32\shell32.dll,22\"; $s.Description = '사람인 공고 관리'; $s.Save()"
if errorlevel 1 (
  echo 바로가기를 만들지 못했습니다. desktop\dist\SaraminFinder\실행.bat 로 실행할 수 있습니다.
  pause
)

echo [3/3] 앱을 실행합니다.
start "" "%APP_HOME%\runtime\pythonw.exe" -m saramin_finder.main
echo 완료되었습니다. 다음부터는 바탕화면의 "사람인 공고 관리"를 더블클릭하세요.
timeout /t 5 >nul
exit /b 0

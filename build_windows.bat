@echo off
setlocal
cd /d "%~dp0"
title Inferno Bin - Build EXE
echo === Inferno Bin by Mohammed El-Shayeb - building InfernoBin.exe ===
set "PY="
py -3 -c "import sys" >nul 2>&1 && set "PY=py -3"
if not defined PY python -c "import sys" >nul 2>&1 && set "PY=python"
if not defined PY (
  echo [X] Python not found. Install it from https://www.python.org/downloads/
  echo     and tick "Add python.exe to PATH".
  pause
  exit /b 1
)
%PY% -m pip install --upgrade -r requirements.txt pyinstaller || goto :err
%PY% inferno_bin.py --export-icon icon.ico || goto :err
%PY% -m PyInstaller --noconfirm --clean --onefile --windowed --name InfernoBin --icon icon.ico --version-file version_info.txt --add-data "assets;assets" inferno_bin.py || goto :err
echo.
echo [OK] Done:  %~dp0dist\InfernoBin.exe
explorer "%~dp0dist"
pause
exit /b 0
:err
echo [X] Build failed - see the messages above.
pause
exit /b 1

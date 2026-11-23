@echo off
setlocal
cd /d "%~dp0"
title Inferno Bin - by Mohammed El-Shayeb
echo.
echo   =============================================
echo      INFERNO BIN  -  by Mohammed El-Shayeb
echo   =============================================
echo.

set "PY="
py -3 -c "import sys" >nul 2>&1 && set "PY=py -3"
if not defined PY python -c "import sys" >nul 2>&1 && set "PY=python"
set "PYLOCAL=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY if exist "%PYLOCAL%" set "PY="%PYLOCAL%""
if not defined PY (
  echo [..] Python is not installed - installing it automatically now...
  echo      This happens only once and may take 1-3 minutes. Please wait.
  echo.
  winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements
  if exist "%PYLOCAL%" set "PY="%PYLOCAL%""
)
if not defined PY (
  echo.
  echo [X] Automatic install did not work. Please install Python manually:
  echo     1. Download it from:  https://www.python.org/downloads/
  echo     2. During setup, TICK the box:  "Add python.exe to PATH"
  echo     3. Then run start.bat again.
  echo.
  start "" https://www.python.org/downloads/
  pause
  exit /b 1
)
echo [OK] Python found:  %PY%
%PY% --version

%PY% -c "import PyQt6.QtWidgets, send2trash" >nul 2>&1
if errorlevel 1 (
  echo [..] Installing required libraries - first time only, please wait...
  %PY% -m pip install --upgrade -r requirements.txt
  if errorlevel 1 (
    echo [X] Library installation failed. Check your internet connection.
    pause
    exit /b 1
  )
)
echo [OK] Libraries ready.
echo [..] Starting Inferno Bin...  look at the bottom-right corner of your screen.
echo.
%PY% inferno_bin.py
if errorlevel 1 (
  echo.
  echo [X] Inferno Bin stopped with an error - see the message above.
  echo     A copy is saved in:  %APPDATA%\InfernoBin\error_log.txt
  pause
)

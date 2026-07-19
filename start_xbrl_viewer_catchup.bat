@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set XBRL_DATA_ROOT=C:\Users\onok\Desktop\XBRL_Data

cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_xbrl_viewer_catchup.ps1"
if /i not "%~1"=="silent" pause

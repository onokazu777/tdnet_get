@echo off
setlocal
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set PYTHONUNBUFFERED=1

cd /d "%~dp0"
python -u run_auto_local.py %*
exit /b %ERRORLEVEL%

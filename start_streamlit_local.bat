@echo off
setlocal
chcp 65001 >nul

cd /d "%~dp0"

set "APP_FILE=keyword_search_app.py"
set "PORT=8501"
set "HOST=127.0.0.1"

if not exist "%APP_FILE%" (
  echo [ERROR] %APP_FILE% が見つかりません。
  echo 実行フォルダ: %CD%
  pause
  exit /b 1
)

if exist ".venv\Scripts\python.exe" (
  set "PY_EXE=.venv\Scripts\python.exe"
) else (
  set "PY_EXE=python"
)

echo [INFO] Streamlit を起動します...
echo [INFO] URL: http://localhost:%PORT%

start "TDnet Streamlit Local" /MIN cmd /c ""%PY_EXE%" -m streamlit run "%APP_FILE%" --server.address %HOST% --server.port %PORT%"

endlocal
exit /b 0

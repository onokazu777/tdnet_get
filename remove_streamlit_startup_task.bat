@echo off
setlocal
chcp 65001 >nul

set "TASK_NAME=TDnet_Streamlit_Localhost_8501"

schtasks /Query /TN "%TASK_NAME%" >nul 2>&1
if not %errorlevel%==0 (
  echo [INFO] タスクは未登録です: %TASK_NAME%
  endlocal
  exit /b 0
)

schtasks /Delete /TN "%TASK_NAME%" /F
if errorlevel 1 (
  echo [ERROR] タスク削除に失敗しました。
  pause
  endlocal
  exit /b 1
)

echo [OK] タスクを削除しました: %TASK_NAME%

endlocal
exit /b 0

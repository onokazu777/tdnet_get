@echo off
setlocal
chcp 65001 >nul

cd /d "%~dp0"

set "TASK_NAME=TDnet_Streamlit_Localhost_8501"
set "RUN_BAT=%~dp0start_streamlit_local.bat"

if not exist "%RUN_BAT%" (
  echo [ERROR] 起動バッチが見つかりません:
  echo %RUN_BAT%
  pause
  exit /b 1
)

schtasks /Query /TN "%TASK_NAME%" >nul 2>&1
if %errorlevel%==0 (
  echo [INFO] 既存タスクを削除して再登録します: %TASK_NAME%
  schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1
)

schtasks /Create /TN "%TASK_NAME%" /SC ONLOGON /TR "\"%RUN_BAT%\"" /RL LIMITED /F
if errorlevel 1 (
  echo [ERROR] タスク登録に失敗しました。
  echo 管理者権限のPowerShell/CMDで再実行してください。
  pause
  exit /b 1
)

echo [OK] タスク登録が完了しました: %TASK_NAME%
echo [INFO] 今すぐ起動する場合:
echo schtasks /Run /TN "%TASK_NAME%"
echo [INFO] 次回ログオン時から自動起動します。

endlocal
exit /b 0

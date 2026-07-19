$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$DailyTaskName = "TDnet_Daily_Auto_Local"
$CatchupTaskName = "TDnet_Catchup_OnLogon"

$BatPath = Join-Path $ProjectRoot "auto_local.bat"
if (-not (Test-Path -LiteralPath $BatPath)) {
  throw "auto_local.bat が見つかりません: $BatPath"
}

$CatchupPath = Join-Path $ProjectRoot "tdnet_catchup.ps1"
if (-not (Test-Path -LiteralPath $CatchupPath)) {
  throw "tdnet_catchup.ps1 が見つかりません: $CatchupPath"
}

# 実行アクション（cmd経由でbat起動）
$DailyAction = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$BatPath`"" -WorkingDirectory $ProjectRoot
$CatchupAction = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$CatchupPath`"" -WorkingDirectory $ProjectRoot

# トリガ: 毎日固定時刻（スリープ復帰あり）
$DailyTime = "06:10"
$TriggerDaily = New-ScheduledTaskTrigger -Daily -At ([DateTime]::ParseExact($DailyTime, "HH:mm", $null))
$TriggerLogon = New-ScheduledTaskTrigger -AtLogOn

# 設定（スリープ中でも回るように）
$Settings = New-ScheduledTaskSettingsSet `
  -StartWhenAvailable `
  -WakeToRun `
  -MultipleInstances IgnoreNew `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -ExecutionTimeLimit (New-TimeSpan -Hours 6)

# 既存があれば更新
foreach ($name in @($DailyTaskName, $CatchupTaskName)) {
  try { Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue | Out-Null } catch {}
}

Register-ScheduledTask `
  -TaskName $DailyTaskName `
  -Action $DailyAction `
  -Trigger $TriggerDaily `
  -Settings $Settings `
  -Description "TDnet日次取得（WakeToRun + StartWhenAvailable）" `
  | Out-Null

Register-ScheduledTask `
  -TaskName $CatchupTaskName `
  -Action $CatchupAction `
  -Trigger $TriggerLogon `
  -Settings $Settings `
  -Description "TDnet取りこぼし補完（ログオン時に不足日を埋める）" `
  | Out-Null

Write-Host "[OK] タスク登録完了: $DailyTaskName / $CatchupTaskName"
Write-Host "[INFO] 毎日 $DailyTime に実行（WakeToRun）+ ログオン時に取りこぼしを補完します"
Write-Host "[INFO] すぐ実行する場合:"
Write-Host "  schtasks /Run /TN `"$DailyTaskName`""
Write-Host "  schtasks /Run /TN `"$CatchupTaskName`""


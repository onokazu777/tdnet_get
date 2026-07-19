$ErrorActionPreference = "Stop"

$TaskNames = @(
  "TDnet_Daily_Auto_Local",
  "TDnet_Catchup_OnLogon"
)

foreach ($name in $TaskNames) {
  try {
    Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction Stop | Out-Null
    Write-Host "[OK] タスクを削除しました: $name"
  } catch {
    Write-Host "[INFO] タスクは未登録です: $name"
  }
}


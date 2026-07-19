# XBRL Viewer: 前の平日分を取りこぼしていたら Streamlit を起動する
# タスク スケジューラで「ログオン時」に実行する想定（固定時刻にPCが起きていなくても補える）

$ErrorActionPreference = "Stop"

$ProjectRoot = "C:\Users\onok\Desktop\開発\tdnet_get"
$MarkerPath  = Join-Path $ProjectRoot ".last_xbrl_viewer_run"
$LogPath     = Join-Path $ProjectRoot ".xbrl_viewer_catchup.log"

$env:PYTHONIOENCODING = "utf-8"
$env:XBRL_DATA_ROOT   = "C:\Users\onok\Desktop\XBRL_Data"

function Get-PrevWeekday([DateTime]$dt) {
    $d = $dt.Date.AddDays(-1)
    while ($d.DayOfWeek -eq [DayOfWeek]::Saturday -or $d.DayOfWeek -eq [DayOfWeek]::Sunday) {
        $d = $d.AddDays(-1)
    }
    return $d
}

function Is-Weekday([DateTime]$dt) {
    return $dt.DayOfWeek -ne [DayOfWeek]::Saturday -and $dt.DayOfWeek -ne [DayOfWeek]::Sunday
}

$today = (Get-Date).Date
$todayKey = $today.ToString("yyyyMMdd")
$prevW = Get-PrevWeekday $today
$prevWKey = $prevW.ToString("yyyyMMdd")

$lastKey = ""
if (Test-Path $MarkerPath) {
    $lastKey = (Get-Content -LiteralPath $MarkerPath -Raw -Encoding UTF8).Trim()
}

$need = $false
$reason = ""

if ($lastKey -eq "") {
    $need = $true
    $reason = "初回（記録なし）"
} elseif ($lastKey -lt $prevWKey) {
    $need = $true
    $reason = "直前の平日 ($prevWKey) より前までしか実行記録がない"
} elseif ((Is-Weekday $today) -and ($lastKey -lt $todayKey)) {
    $need = $true
    $reason = "今日 ($todayKey) はまだこのスクリプトから起動していない（平日）"
}

$ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
if (-not $need) {
    $msg = "[$ts] SKIP last=$lastKey today=$todayKey prevWeekday=$prevWKey"
    Add-Content -LiteralPath $LogPath -Value $msg -Encoding UTF8
    Write-Host $msg
    exit 0
}

$msg = "[$ts] START ($reason) → Streamlit 起動"
Add-Content -LiteralPath $LogPath -Value $msg -Encoding UTF8
Write-Host $msg

Set-Content -LiteralPath $MarkerPath -Value $todayKey -Encoding UTF8

Set-Location -LiteralPath $ProjectRoot
Start-Process -FilePath "python" -ArgumentList @(
    "-m", "streamlit", "run", "④_xbrl_viewer.py"
) -WorkingDirectory $ProjectRoot

exit 0

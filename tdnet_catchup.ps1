$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$MarkerPath  = Join-Path $ProjectRoot ".last_tdnet_run"
$LogDir      = Join-Path $ProjectRoot "logs"
$LogPath     = Join-Path $LogDir "tdnet_catchup.log"

$BatPath     = Join-Path $ProjectRoot "auto_local.bat"
if (-not (Test-Path -LiteralPath $BatPath)) {
  throw "auto_local.bat が見つかりません: $BatPath"
}

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

$SaveRoot = "G:\マイドライブ\TDnet_Downloads"

function Key([DateTime]$d) { $d.ToString("yyyyMMdd") }

function PrevDay([DateTime]$d) { $d.Date.AddDays(-1) }

function ExistsOutputs([string]$k) {
  $p1 = Join-Path $SaveRoot "TDnet_Sorted_$k.csv"
  $p2 = Join-Path $SaveRoot "Analysis_Hits_free_word_$k.csv"
  $p3 = Join-Path $SaveRoot "PDF_Search_Result_Distribution_free_word_${k}_sh.csv"
  return (Test-Path -LiteralPath $p1) -and (Test-Path -LiteralPath $p2) -and (Test-Path -LiteralPath $p3)
}

# ログ書き込み（たまに他プロセスがロックしても落ちないようリトライ）
function WriteLog([string]$msg) {
  for ($i = 0; $i -lt 5; $i++) {
    try {
      Add-Content -LiteralPath $LogPath -Value $msg -Encoding UTF8
      return
    } catch {
      Start-Sleep -Milliseconds (200 * ($i + 1))
    }
  }
}

# 最低限「昨日」が欠けていれば埋める。マーカーが古ければ最大7日分まで追いかける。
$today = (Get-Date).Date
$yesterday = PrevDay $today

$lastKey = ""
if (Test-Path -LiteralPath $MarkerPath) {
  $lastKey = (Get-Content -LiteralPath $MarkerPath -Raw -Encoding UTF8).Trim()
}

$start = $yesterday
if ($lastKey -match '^\d{8}$') {
  $lastDt = [DateTime]::ParseExact($lastKey, "yyyyMMdd", $null)
  if ($lastDt -lt $yesterday) {
    $start = $lastDt.AddDays(1)
  }
}

$dates = @()
for ($d = $start; $d -le $today; $d = $d.AddDays(1)) {
  $dates += $d
  if ($dates.Count -ge 7) { break }
}

$ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
WriteLog "[$ts] CHECK last=$lastKey range=$(Key $dates[0])..$(Key $dates[-1])"

$ranAny = $false
foreach ($d in $dates) {
  $k = Key $d
  if (ExistsOutputs $k) { continue }

  $ts2 = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  WriteLog "[$ts2] RUN $k (missing outputs)"

  # batに日付を渡して実行（標準出力は bat 側で logs/ に追記）
  & cmd.exe /c "`"$BatPath`" $k" | Out-Null

  $ranAny = $true
  if (-not (ExistsOutputs $k)) {
    $ts3 = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    WriteLog "[$ts3] WARN $k still missing outputs after run"
  } else {
    Set-Content -LiteralPath $MarkerPath -Value $k -Encoding UTF8
  }
}

if (-not $ranAny) {
  $ts4 = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  WriteLog "[$ts4] SKIP (nothing to catch up)"
}


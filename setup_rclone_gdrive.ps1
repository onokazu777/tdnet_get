# Google Drive 用 rclone 設定を作り、GitHub Actions 用 Secret の中身を表示する。
# 初回のみ PC で実行。以降の日次取得は Actions が Drive へ直接アップロードする。

$ErrorActionPreference = "Stop"

$RemoteName = "gdrive"
$DrivePathHint = "TDnet_Downloads  （G:\マイドライブ\TDnet_Downloads と同じ場所）"

Write-Host ""
Write-Host "=== rclone + Google Drive セットアップ ===" -ForegroundColor Cyan
Write-Host "目的: Actions から PDF/CSV を個人の Google Drive へ保存できるようにする"
Write-Host "保存先イメージ: $DrivePathHint"
Write-Host ""

# rclone があるか確認
$rclone = Get-Command rclone -ErrorAction SilentlyContinue
if (-not $rclone) {
  Write-Host "[INFO] rclone が見つかりません。winget でインストールします..." -ForegroundColor Yellow
  winget install --id Rclone.Rclone -e --accept-source-agreements --accept-package-agreements
  $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
              [System.Environment]::GetEnvironmentVariable("Path", "User")
  $rclone = Get-Command rclone -ErrorAction SilentlyContinue
  if (-not $rclone) {
    throw "rclone のインストール後も PATH に見つかりません。ターミナルを開き直して再実行してください。"
  }
}

Write-Host "[OK] rclone: $($rclone.Source)"
Write-Host ""
Write-Host "次の対話設定で Google Drive を連携します。" -ForegroundColor Cyan
Write-Host "  n) New remote"
Write-Host "  name> $RemoteName"
Write-Host "  Storage> Google Drive を選択（番号は表示に従う）"
Write-Host "  client_id / client_secret> 空 Enter でOK（個人用）"
Write-Host "  scope> 1 (Full access) 推奨"
Write-Host "  root_folder_id / service_account> 空 Enter"
Write-Host "  Edit advanced?> n"
Write-Host "  Use auto config?> y  → ブラウザで Google ログイン"
Write-Host "  Configure as Shared Drive?> n（マイドライブの場合）"
Write-Host "  Keep this remote?> y"
Write-Host "  q) Quit"
Write-Host ""
Pause

rclone config

# 設定ファイルの場所
$configPath = Join-Path $env:APPDATA "rclone\rclone.conf"
if (-not (Test-Path -LiteralPath $configPath)) {
  # 一部環境は別パス
  $alt = Join-Path $env:USERPROFILE ".config\rclone\rclone.conf"
  if (Test-Path -LiteralPath $alt) { $configPath = $alt }
}

if (-not (Test-Path -LiteralPath $configPath)) {
  throw "rclone.conf が見つかりません。設定が完了したか確認してください。"
}

Write-Host ""
Write-Host "[OK] 設定ファイル: $configPath" -ForegroundColor Green

# 接続テスト（フォルダ一覧の先頭だけ）
Write-Host ""
Write-Host "接続テスト: rclone lsd ${RemoteName}:" -ForegroundColor Cyan
rclone lsd "${RemoteName}:" | Select-Object -First 10

Write-Host ""
Write-Host "=== GitHub Secrets 登録 ===" -ForegroundColor Cyan
Write-Host "1. https://github.com/onokazu777/tdnet_get/settings/secrets/actions"
Write-Host "2. New repository secret"
Write-Host "3. Name: RCLONE_CONFIG"
Write-Host "4. Value: 下に表示する rclone.conf の全文をそのまま貼り付け"
Write-Host ""
Write-Host "----- ここからコピー（RCLONE_CONFIG） -----" -ForegroundColor Yellow
Get-Content -LiteralPath $configPath -Raw
Write-Host "----- ここまで -----" -ForegroundColor Yellow
Write-Host ""
Write-Host "登録後、Actions の Daily XBRL Update を手動実行すれば Drive へ上がります。"
Write-Host "任意の Secret 名は RCLONE_CONFIG 固定（workflow 側が参照）。"
Write-Host ""

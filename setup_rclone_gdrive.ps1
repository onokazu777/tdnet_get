# Google Drive rclone setup for GitHub Actions (RCLONE_CONFIG secret)
# Run once on PC:
#   powershell.exe -ExecutionPolicy Bypass -File ".\setup_rclone_gdrive.ps1"

$ErrorActionPreference = "Stop"

$RemoteName = "gdrive"

Write-Host ""
Write-Host "=== rclone + Google Drive setup ===" -ForegroundColor Cyan
Write-Host "Goal: Actions can upload PDF/CSV to your Google Drive"
Write-Host "Target folder: My Drive / TDnet_Downloads"
Write-Host "  (same as G:\マイドライブ\TDnet_Downloads)"
Write-Host ""

$rclone = Get-Command rclone -ErrorAction SilentlyContinue
if (-not $rclone) {
  Write-Host "[INFO] rclone not found. Installing via winget..." -ForegroundColor Yellow
  winget install --id Rclone.Rclone -e --accept-source-agreements --accept-package-agreements
  $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
              [System.Environment]::GetEnvironmentVariable("Path", "User")
  $rclone = Get-Command rclone -ErrorAction SilentlyContinue
  if (-not $rclone) {
    throw "rclone still not found in PATH. Close this window, open a new PowerShell, and run again."
  }
}

Write-Host "[OK] rclone: $($rclone.Source)"
Write-Host ""
Write-Host "Next: interactive rclone config. Answer like this:" -ForegroundColor Cyan
Write-Host '  n) New remote'
Write-Host ("  name> {0}" -f $RemoteName)
Write-Host "  Storage> choose Google Drive (follow the number shown)"
Write-Host "  client_id / client_secret> press Enter (empty is OK)"
Write-Host "  scope> 1  (Full access)"
Write-Host "  root_folder_id / service_account> press Enter"
Write-Host "  Edit advanced config?> n"
Write-Host "  Use auto config?> y   then login in the browser"
Write-Host "  Configure this as a Shared Drive / Team Drive?> n"
Write-Host "  Keep this remote?> y"
Write-Host "  q) Quit"
Write-Host ""
Write-Host "Press Enter to start rclone config..."
[void][System.Console]::ReadLine()

rclone config

$configPath = Join-Path $env:APPDATA "rclone\rclone.conf"
if (-not (Test-Path -LiteralPath $configPath)) {
  $alt = Join-Path $env:USERPROFILE ".config\rclone\rclone.conf"
  if (Test-Path -LiteralPath $alt) {
    $configPath = $alt
  }
}

if (-not (Test-Path -LiteralPath $configPath)) {
  throw "rclone.conf not found. Did you finish rclone config?"
}

Write-Host ""
Write-Host ("[OK] config file: {0}" -f $configPath) -ForegroundColor Green

Write-Host ""
Write-Host ("Connection test: rclone lsd {0}:" -f $RemoteName) -ForegroundColor Cyan
rclone lsd ("{0}:" -f $RemoteName) | Select-Object -First 10

Write-Host ""
Write-Host "=== Register GitHub Secret ===" -ForegroundColor Cyan
Write-Host "1. Open: https://github.com/onokazu777/tdnet_get/settings/secrets/actions"
Write-Host "2. Click existing RCLONE_CONFIG -> Update  (or New repository secret)"
Write-Host "3. Name: RCLONE_CONFIG"
Write-Host "4. Secret: paste the FULL text below"
Write-Host ""
Write-Host "----- COPY FROM HERE (RCLONE_CONFIG) -----" -ForegroundColor Yellow
Get-Content -LiteralPath $configPath -Raw
Write-Host "----- COPY UNTIL HERE -----" -ForegroundColor Yellow
Write-Host ""
Write-Host "After saving the secret, run Daily XBRL Update again from Actions."
Write-Host ""

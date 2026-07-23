# 外部cronと同じ API で Daily XBRL Update を起動する（動作確認用）
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("1135", "1535", "1705", "2005", "2355", "manual")]
    [string]$Slot,

    [string]$TargetDate = "",

    [switch]$Force,

    [string]$Token = $env:TDNET_DISPATCH_TOKEN,
    [string]$Repo = "onokazu777/tdnet_get",
    [string]$Workflow = "daily_update.yml"
)

$ErrorActionPreference = "Stop"

if (-not $Token) {
    throw "Token がありません。`$env:TDNET_DISPATCH_TOKEN に GitHub PAT を設定するか -Token を指定してください。"
}

$bodyObj = @{
    ref = "main"
    inputs = @{
        slot = $Slot
        target_date = $TargetDate
        force = if ($Force) { "true" } else { "false" }
    }
}
$body = $bodyObj | ConvertTo-Json -Compress -Depth 5

$uri = "https://api.github.com/repos/$Repo/actions/workflows/$Workflow/dispatches"
$headers = @{
    Accept = "application/vnd.github+json"
    Authorization = "Bearer $Token"
    "X-GitHub-Api-Version" = "2022-11-28"
}

Write-Host "POST $uri"
Write-Host "body: $body"

try {
    Invoke-RestMethod -Method Post -Uri $uri -Headers $headers -Body $body -ContentType "application/json"
    Write-Host "[OK] dispatched slot=$Slot (HTTP 204 expected)"
} catch {
    Write-Host "[FAIL] $($_.Exception.Message)"
    if ($_.ErrorDetails.Message) { Write-Host $_.ErrorDetails.Message }
    throw
}

Write-Host "Actions: https://github.com/$Repo/actions"

# Restart Selenite (stop then start)
# Usage:
#   .\restart-selenite.ps1
#   .\restart-selenite.ps1 -BindIPOverride 0.0.0.0 -AdvertiseHosts "100.85.28.75,192.168.1.52"

param(
    [string]$BindIPOverride = "",
    [string[]]$AdvertiseHosts = @()
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repo

Write-Host "Restarting Selenite from $repo..." -ForegroundColor Cyan

try {
    & "$repo\stop-selenite.ps1"
} catch {
    Write-Host "Warning: stop-selenite.ps1 reported: $($_.Exception.Message)" -ForegroundColor Yellow
}

$defaultAdvertise = @("127.0.0.1", "192.168.1.52", "100.85.28.75")
if (-not $AdvertiseHosts -or $AdvertiseHosts.Count -eq 0) {
    $AdvertiseHosts = $defaultAdvertise
}

$advertiseArg = @()
if ($AdvertiseHosts -and $AdvertiseHosts.Count -gt 0) {
    $advertiseArg += "-AdvertiseHosts"
    $advertiseArg += $AdvertiseHosts
}

& "$repo\start-selenite.ps1" -BindIPOverride $BindIPOverride @advertiseArg

Write-Host "Restart complete." -ForegroundColor Green

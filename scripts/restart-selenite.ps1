# Restart Selenite (stop then start)
# Usage:
#   .\scripts\restart-selenite.ps1
#   .\scripts\restart-selenite.ps1 -BindIPOverride 0.0.0.0 -AdvertiseHosts "127.0.0.1,<LAN-IP>,<TAILSCALE-IP>"

param(
    [string]$BindIPOverride = "",
    [string[]]$AdvertiseHosts = @(),
    [switch]$AllowProdStart,
    [switch]$AllowProdWrites

)

$guardScript = Join-Path $PSScriptRoot 'workspace-guard.ps1'
if (Test-Path $guardScript) { . $guardScript }





$ErrorActionPreference = "Stop"
$repo = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $repo

$roleFile = Join-Path $repo '.workspace-role'
$workspaceRole = if (Test-Path $roleFile) { (Get-Content -Path $roleFile -ErrorAction Stop | Select-Object -First 1).Trim().ToLowerInvariant() } else { '' }
$isProd = $workspaceRole -eq 'prod'

if ($isProd) {
    if ($AllowProdWrites) { $env:SELENITE_ALLOW_PROD_WRITES = '1' }
    if ($AllowProdStart) { $env:SELENITE_ALLOW_PROD_START = '1' }

    # Prod restart only requires start consent; writes are optional for ancillary tasks.
    if ($env:SELENITE_AI_SESSION -eq '1' -and $env:SELENITE_ALLOW_PROD_START -ne '1') {
        throw "Prod restart blocked: set SELENITE_ALLOW_PROD_START=1 or pass -AllowProdStart after aligning ports/hosts."
    }
}

Write-Host "Restarting Selenite from $repo..." -ForegroundColor Cyan

try {
    & (Join-Path $repo 'scripts\stop-selenite.ps1')
} catch {
    Write-Host "Warning: stop-selenite.ps1 reported: $($_.Exception.Message)" -ForegroundColor Yellow
}

$defaultAdvertise = @("127.0.0.1")
if (-not $AdvertiseHosts -or $AdvertiseHosts.Count -eq 0) {
    $AdvertiseHosts = $defaultAdvertise
}

$advertiseArg = @()
if ($AdvertiseHosts -and $AdvertiseHosts.Count -gt 0) {
    $advertiseArg += "-AdvertiseHosts"
    $advertiseArg += $AdvertiseHosts
}

& (Join-Path $repo 'scripts\start-selenite.ps1') -BindIPOverride $BindIPOverride @advertiseArg

Write-Host "Restart complete." -ForegroundColor Green





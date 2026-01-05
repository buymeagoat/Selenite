#!/usr/bin/env pwsh
# Validate CORS headers for the configured LAN/Tailscale IP

param(
    [string]$HostIp
)

$guardScript = Join-Path $PSScriptRoot 'workspace-guard.ps1'
if (Test-Path $guardScript) { . $guardScript }






$BackendPort = if ($env:SELENITE_BACKEND_PORT) { [int]$env:SELENITE_BACKEND_PORT } else { 8100 }
$FrontendPort = if ($env:SELENITE_FRONTEND_PORT) { [int]$env:SELENITE_FRONTEND_PORT } else { 5173 }
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$backendDir = Join-Path $repoRoot 'backend'

function Get-DefaultHostIp {
    $candidates = Get-NetIPAddress -AddressFamily IPv4 -PrefixOrigin Manual,Dhcp |
        Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
        Select-Object -ExpandProperty IPAddress

    if (-not $candidates) {
        throw "No LAN/Tailscale IPv4 address found. Supply -HostIp explicitly."
    }

    return $candidates[0]
}

if (-not $HostIp -or $HostIp.Trim() -eq "") {
    $HostIp = Get-DefaultHostIp
}

$origin = "http://$HostIp:$FrontendPort"
$url = "http://$HostIp:$BackendPort/health"

Write-Host "`n=== Testing CORS Configuration ===" -ForegroundColor Cyan
Write-Host "Origin: $origin"
Write-Host "URL: $url`n"

try {
    $response = Invoke-WebRequest -Uri $url -Headers @{ 'Origin' = $origin } -UseBasicParsing -TimeoutSec 3

    Write-Host "Status: $($response.StatusCode)" -ForegroundColor Green

    $corsHeader = $response.Headers.'Access-Control-Allow-Origin'
    if ($corsHeader) {
        Write-Host "[OK] Access-Control-Allow-Origin: $corsHeader" -ForegroundColor Green
    } else {
        Write-Host "[WARN] No Access-Control-Allow-Origin header" -ForegroundColor Yellow
    }

    $allowCredentials = $response.Headers.'Access-Control-Allow-Credentials'
    if ($allowCredentials) {
        Write-Host "  Access-Control-Allow-Credentials: $allowCredentials"
    }
}
catch {
    Write-Host "[WARN] Request failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n=== backend/.env CORS snippet ===" -ForegroundColor Cyan
Push-Location $backendDir
if (Test-Path .env) {
    Get-Content .env | Select-String -Pattern "CORS"
} else {
    Write-Host "No backend/.env found." -ForegroundColor Yellow
}
Pop-Location

Write-Host "`nTip: after editing backend/.env, run .\scripts\start-selenite.ps1 so uvicorn reloads the new CORS list." -ForegroundColor Yellow






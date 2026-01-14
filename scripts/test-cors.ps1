#!/usr/bin/env pwsh
# Validate CORS headers for the configured LAN/Tailscale IP

param(
    [string]$HostIp
)

$guardScript = Join-Path $PSScriptRoot 'workspace-guard.ps1'
if (Test-Path $guardScript) { . $guardScript }






$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$backendDir = Join-Path $repoRoot 'backend'

$roleFile = Join-Path $repoRoot '.workspace-role'
$wsRole = if (Test-Path $roleFile) { (Get-Content -Path $roleFile -ErrorAction Stop | Select-Object -First 1).Trim().ToLowerInvariant() } else { '' }
$isProd = $wsRole -eq 'prod'

$envBackendPort = $null
$envFrontendPort = $null
$envFile = Join-Path $repoRoot '.env'
if (Test-Path $envFile) {
    $portMatch = Select-String -Path $envFile -Pattern '^\s*PORT\s*=\s*(\d+)' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($portMatch) { $envBackendPort = [int]$portMatch.Matches[0].Groups[1].Value }

    $frontendMatch = Select-String -Path $envFile -Pattern '^\s*FRONTEND_URL\s*=\s*.+:(\d+)' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($frontendMatch) { $envFrontendPort = [int]$frontendMatch.Matches[0].Groups[1].Value }
}

$BackendPort = if ($env:SELENITE_BACKEND_PORT) { [int]$env:SELENITE_BACKEND_PORT } elseif ($envBackendPort) { $envBackendPort } elseif ($isProd) { 8100 } else { 8201 }
$FrontendPort = if ($env:SELENITE_FRONTEND_PORT) { [int]$env:SELENITE_FRONTEND_PORT } elseif ($envFrontendPort) { $envFrontendPort } elseif ($isProd) { 5173 } else { 5174 }

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

Write-Host "`n=== .env CORS snippet ===" -ForegroundColor Cyan
if (Test-Path $envFile) {
    Get-Content $envFile | Select-String -Pattern "CORS"
} else {
    Write-Host "No .env found at repo root." -ForegroundColor Yellow
}

Write-Host "`nTip: after editing .env, run .\scripts\start-selenite.ps1 so uvicorn reloads the new CORS list." -ForegroundColor Yellow





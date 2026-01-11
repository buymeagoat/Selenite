
<#
.SYNOPSIS
    Test whether the Selenite backend is reachable from the LAN/Tailscale network.
#>


param()

$guardScript = Join-Path $PSScriptRoot 'workspace-guard.ps1'
if (Test-Path $guardScript) { . $guardScript }




$ErrorActionPreference = "Stop"

$BackendPort = if ($env:SELENITE_BACKEND_PORT) { [int]$env:SELENITE_BACKEND_PORT } else { 8201 }
$FrontendPort = if ($env:SELENITE_FRONTEND_PORT) { [int]$env:SELENITE_FRONTEND_PORT } else { 5174 }

Write-Host "=== Selenite Backend Network Test ===" -ForegroundColor Cyan

# Discover host IPs
$networkIPs = Get-NetIPAddress -AddressFamily IPv4 -PrefixOrigin Manual,Dhcp |
    Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
    Select-Object -ExpandProperty IPAddress

if (-not $networkIPs) {
    Write-Host "[FAIL] No LAN/Tailscale IPv4 address found." -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] Detected IP(s): $($networkIPs -join ', ')" -ForegroundColor Cyan
$testIP = $networkIPs[0]

# Check listener state
Write-Host "`nChecking if port $BackendPort is listening..." -ForegroundColor Cyan
$listener = Get-NetTCPConnection -LocalPort $BackendPort -State Listen -ErrorAction SilentlyContinue

if (-not $listener) {
    Write-Host "[FAIL] Port $BackendPort is NOT listening. Start with: .\scripts\start-selenite.ps1" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Port $BackendPort listening on $($listener.LocalAddress)" -ForegroundColor Green

if ($listener.LocalAddress -ne "0.0.0.0") {
    Write-Host "[WARN] Not bound to 0.0.0.0 (bound to $($listener.LocalAddress)). Remote devices may not reach it." -ForegroundColor Yellow
}

# Health from localhost
Write-Host "`nTesting http://127.0.0.1:$BackendPort/health" -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:$BackendPort/health" -UseBasicParsing -TimeoutSec 3
    Write-Host "[OK] Local health check returned $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] Local health check failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Health from LAN IP
Write-Host "`nTesting http://${testIP}:$BackendPort/health" -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://${testIP}:$BackendPort/health" -UseBasicParsing -TimeoutSec 3
    Write-Host "[OK] Network health check returned $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] Network health check failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Run .\allow-backend-port.ps1 as Administrator to open the firewall, then rerun this script." -ForegroundColor Yellow
}

# Firewall summary
Write-Host "`nChecking Windows Firewall profiles..." -ForegroundColor Cyan
try {
    $profiles = Get-NetFirewallProfile -ErrorAction SilentlyContinue | Where-Object { $_.Enabled }
    if ($profiles) {
        Write-Host "[WARN] Active firewall profiles: $($profiles.Name -join ', ')" -ForegroundColor Yellow
        Write-Host "If mobile devices still cannot connect, confirm the firewall rule allows port $BackendPort." -ForegroundColor Yellow
    } else {
        Write-Host "[OK] Windows Firewall disabled for all profiles." -ForegroundColor Green
    }
} catch {
    Write-Host "[WARN] Unable to query firewall status (admin rights may be required)." -ForegroundColor Yellow
}

# Share URLs with testers
Write-Host "`n=== Share with mobile tester ===" -ForegroundColor Cyan
Write-Host "Frontend UI : http://${testIP}:$FrontendPort/" -ForegroundColor Cyan
Write-Host "Health check: http://${testIP}:$BackendPort/health" -ForegroundColor Cyan
Write-Host ""
Write-Host "If the tester reports failures, capture the Technical Details drawer in the UI and review docs/application_documentation/USER_GUIDE.md under Troubleshooting." -ForegroundColor Yellow





# Start Selenite via bootstrap
# Adjust flags below as needed:
# -Dev: runs uvicorn with reload (development)
# -ResetAuth: clears frontend cached auth state
# -BindIP: set to 127.0.0.1 for local only, or 0.0.0.0 / your Tailscale IP for remote
# -AdvertiseHosts: comma-separated list of hosts/IPs to expose (e.g., 127.0.0.1,<LAN-IP>,<TAILSCALE-IP>)
# -Seed: add if you want to reseed the DB each start
# -ForceInstall: add if you want to reinstall node_modules each start

param(
    [string]$BindIPOverride = "",
    [string[]]$AdvertiseHosts = @()

)

$guardScript = Join-Path $PSScriptRoot 'workspace-guard.ps1'
if (Test-Path $guardScript) { . $guardScript }

$repo = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $repo

# Detect workspace role/state early to block dev-style starts in prod.
$roleFile = Join-Path $repo '.workspace-role'
$stateFile = Join-Path $repo '.workspace-state.json'
$wsRole = if (Test-Path $roleFile) { (Get-Content -Path $roleFile -ErrorAction Stop | Select-Object -First 1).Trim().ToLowerInvariant() } else { '' }
$wsState = $null
if (Test-Path $stateFile) {
    try { $wsState = Get-Content -Path $stateFile -Raw | ConvertFrom-Json } catch { $wsState = $null }
}
$isProd = $wsRole -eq 'prod'

if ($isProd -and $env:SELENITE_AI_SESSION -eq '1' -and $env:SELENITE_ALLOW_PROD_START -ne '1') {
    $stateLabel = if ($wsState) { $wsState.state } else { 'unknown' }
    throw "Prod start blocked (state=$stateLabel). Set SELENITE_ALLOW_PROD_START=1 after aligning ports/hosts per release runbook."
}

$envFile = Join-Path $repo '.env'
$envPort = $null
$envFrontendPort = $null
if (Test-Path $envFile) {
    $portMatch = Select-String -Path $envFile -Pattern '^\s*PORT\s*=\s*(\d+)' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($portMatch) { $envPort = $portMatch.Matches[0].Groups[1].Value }

    $frontendMatch = Select-String -Path $envFile -Pattern '^\s*FRONTEND_URL\s*=\s*.+:(\d+)' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($frontendMatch) { $envFrontendPort = $frontendMatch.Matches[0].Groups[1].Value }
}

if ($isProd) {
    if (-not $envPort -or -not $envFrontendPort) {
        throw "Prod start blocked: .env must define PORT and FRONTEND_URL with prod ports before starting."
    }
    # Prod always uses .env ports, ignoring any shell overrides.
    $env:SELENITE_BACKEND_PORT = $envPort
    $env:SELENITE_FRONTEND_PORT = $envFrontendPort
} else {
    $env:SELENITE_BACKEND_PORT = if ($env:SELENITE_BACKEND_PORT) { $env:SELENITE_BACKEND_PORT } elseif ($envPort) { $envPort } else { '8201' }
    $env:SELENITE_FRONTEND_PORT = if ($env:SELENITE_FRONTEND_PORT) { $env:SELENITE_FRONTEND_PORT } elseif ($envFrontendPort) { $envFrontendPort } else { '5174' }
}

$bind = $BindIPOverride
if (-not $bind -or $bind -eq "") {
    # Default to all interfaces so LAN/Tailscale clients can reach dev.
    $bind = "0.0.0.0"
}

if (-not $AdvertiseHosts -or $AdvertiseHosts.Count -eq 0) {
    $AdvertiseHosts = @()
}

# Proactively ensure any previous Selenite processes are stopped before starting fresh
try {
    $stopScript = Join-Path $repo 'scripts\stop-selenite.ps1'
    if (Test-Path $stopScript) {
        Write-Host "Ensuring a clean slate by stopping existing Selenite processes..." -ForegroundColor Yellow
        & $stopScript | Out-Null
    }
} catch {
    Write-Host "Warning: Failed to run stop-selenite.ps1: $_" -ForegroundColor Yellow
}

# Invoke bootstrap directly so parameters are passed safely
if ($isProd) {
    & (Join-Path $repo 'scripts\bootstrap.ps1') -BindPort ([int]$env:SELENITE_BACKEND_PORT) -FrontendPort ([int]$env:SELENITE_FRONTEND_PORT) -BindIP $bind -AdvertiseHosts $AdvertiseHosts
} else {
    & (Join-Path $repo 'scripts\bootstrap.ps1') -Dev -ResetAuth -BindPort ([int]$env:SELENITE_BACKEND_PORT) -FrontendPort ([int]$env:SELENITE_FRONTEND_PORT) -BindIP $bind -AdvertiseHosts $AdvertiseHosts
}

# Example usage for Task Scheduler Action:
# Program/script: pwsh
# Arguments: -NoLogo -NoProfile -Command "& '<REPO_ROOT>\scripts\start-selenite.ps1'"
# Start in: <REPO_ROOT>







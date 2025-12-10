# Start Selenite via bootstrap
# Adjust flags below as needed:
# -Dev: runs uvicorn with reload (development)
# -ResetAuth: clears frontend cached auth state
# -BindIP: set to 127.0.0.1 for local only, or 0.0.0.0 / your Tailscale IP for remote
# -AdvertiseHosts: comma-separated list of hosts/IPs to expose (e.g., 127.0.0.1,<LAN-IP>,100.x.x.x)
# -Seed: add if you want to reseed the DB each start
# -ForceInstall: add if you want to reinstall node_modules each start

param(
    [string]$BindIPOverride = "",
    [string[]]$AdvertiseHosts = @()
)

$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repo

$bind = $BindIPOverride
if (-not $bind -or $bind -eq "") {
    # Default to all interfaces so LAN/Tailscale clients can reach it
    $bind = "0.0.0.0"
}

$defaultAdvertise = @("127.0.0.1", "192.168.1.52", "100.85.28.75")
if (-not $AdvertiseHosts -or $AdvertiseHosts.Count -eq 0) {
    $AdvertiseHosts = $defaultAdvertise
}

# Proactively ensure any previous Selenite processes are stopped before starting fresh
try {
    $stopScript = Join-Path $repo 'stop-selenite.ps1'
    if (Test-Path $stopScript) {
        Write-Host "Ensuring a clean slate by stopping existing Selenite processes..." -ForegroundColor Yellow
        & $stopScript | Out-Null
    }
} catch {
    Write-Host "Warning: Failed to run stop-selenite.ps1: $_" -ForegroundColor Yellow
}

# Invoke bootstrap directly so parameters are passed safely
& "$repo/bootstrap.ps1" -Dev -ResetAuth -BindIP $bind -AdvertiseHosts $AdvertiseHosts

# Example usage for Task Scheduler Action:
# Program/script: pwsh
# Arguments: -NoLogo -NoProfile -Command "& 'D:\Dev\projects\Selenite\start-selenite.ps1'"
# Start in: D:\Dev\projects\Selenite

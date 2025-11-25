# Start Selenite via bootstrap
# Adjust flags below as needed:
# -Dev: runs uvicorn with reload (development)
# -ResetAuth: clears frontend cached auth state
# -BindIP: set to 127.0.0.1 for local only, or 0.0.0.0 / your Tailscale IP for remote
# -Seed: add if you want to reseed the DB each start
# -ForceInstall: add if you want to reinstall node_modules each start

param(
    [string]$BindIPOverride = ""
)

$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repo

$bind = $BindIPOverride
if (-not $bind -or $bind -eq "") {
    # Default to all interfaces so LAN/Tailscale clients can reach it
    $bind = "0.0.0.0"
}

pwsh -NoLogo -NoProfile -Command "& '$repo/bootstrap.ps1' -Dev -ResetAuth -BindIP $bind"

# Example usage for Task Scheduler Action:
# Program/script: pwsh
# Arguments: -NoLogo -NoProfile -Command "& 'D:\Dev\projects\Selenite\start-selenite.ps1'"
# Start in: D:\Dev\projects\Selenite

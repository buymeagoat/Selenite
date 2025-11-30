<#
.SYNOPSIS
  Watchdog script to perform full orchestrated restarts when `restart.flag` is present.
.DESCRIPTION
  Monitors the repository root for a sentinel file `restart.flag` created by the
  backend endpoint `/system/full-restart`. When detected it:
    1. Logs detection
    2. Removes the sentinel file
    3. Executes `./stop-selenite.ps1`
    4. Executes `./start-selenite.ps1`
  Runs indefinitely until terminated (Ctrl+C). Safe: does not execute arbitrary commands.
.PARAMETER IntervalSeconds
  Polling interval in seconds (default 5).
#>
param(
  [int]$IntervalSeconds = 5
)

$ErrorActionPreference = 'Stop'

function Write-Log {
  param([string]$Message)
  $timestamp = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
  Write-Host "[watch-restart] $timestamp $Message"
}

$root = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
Set-Location $root
Write-Log "Started watchdog in $root (interval=$IntervalSeconds sec)"

$sentinel = Join-Path $root 'restart.flag'

while ($true) {
  try {
    if (Test-Path $sentinel) {
      Write-Log "Detected restart flag. Initiating orchestrated restart."      
      $content = Get-Content $sentinel -ErrorAction SilentlyContinue | Out-String
      Remove-Item $sentinel -Force -ErrorAction SilentlyContinue
      Write-Log "Flag removed. Content: $content"

      Write-Log "Stopping existing processes..."
      ./stop-selenite.ps1

      Write-Log "Starting services..."
      ./start-selenite.ps1

      Write-Log "Restart cycle complete. Continuing to monitor."    
    }
  } catch {
    Write-Log "Error during restart cycle: $($_.Exception.Message)"
  }
  Start-Sleep -Seconds $IntervalSeconds
}

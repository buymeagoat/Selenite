<#
.SYNOPSIS
  Display the current workspace state.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$stateFile = Join-Path $repoRoot ".workspace-state.json"
$roleFile = Join-Path $repoRoot ".workspace-role"

if (-not (Test-Path $stateFile)) {
    Write-Host "Workspace state file missing: $stateFile" -ForegroundColor Yellow
    if (Test-Path $roleFile) {
        $role = (Get-Content -Path $roleFile -ErrorAction Stop | Select-Object -First 1).Trim()
        Write-Host "Workspace role: $role" -ForegroundColor Cyan
    }
    return
}

$state = Get-Content -Path $stateFile -Raw | ConvertFrom-Json
Write-Host "Workspace role: $($state.role)" -ForegroundColor Cyan
Write-Host "Workspace state: $($state.state)" -ForegroundColor Cyan
Write-Host "Canonical owner: $($state.canonical_owner)" -ForegroundColor Cyan
if ($state.note) {
    Write-Host "Note: $($state.note)" -ForegroundColor Gray
}
if ($state.updated_at) {
    Write-Host "Updated at: $($state.updated_at)" -ForegroundColor Gray
}

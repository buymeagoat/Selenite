<#
.SYNOPSIS
  Guard against editing the wrong workspace (prod vs dev).

.DESCRIPTION
  Reads .workspace-role from repo root. If role is "prod", requires
  explicit acknowledgment via SELENITE_ALLOW_PROD_WRITES=1 before
  proceeding. This prevents accidental edits in production.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$roleFile = Join-Path $repoRoot ".workspace-role"
$stateFile = Join-Path $repoRoot ".workspace-state.json"

if (-not (Test-Path $roleFile)) {
    Write-Host "[guard] Missing .workspace-role (expected 'prod' or 'dev')." -ForegroundColor Yellow
    return
}

$role = (Get-Content -Path $roleFile -ErrorAction Stop | Select-Object -First 1).Trim().ToLowerInvariant()
if ($role -notin @("prod", "dev")) {
    throw "[guard] Invalid .workspace-role value '$role'. Use 'prod' or 'dev'."
}

$state = $null
if (Test-Path $stateFile) {
    try {
        $state = Get-Content -Path $stateFile -Raw | ConvertFrom-Json
    } catch {
        $state = $null
    }
}

if ($state -and $state.role) {
    $stateRole = $state.role.ToString().Trim().ToLowerInvariant()
    if ($stateRole -and $stateRole -ne $role) {
        throw "[guard] Workspace role mismatch between .workspace-role ($role) and .workspace-state.json ($stateRole)."
    }
}

Write-Host "[guard] Workspace role: $role" -ForegroundColor Cyan
Write-Host "[guard] Repo root: $repoRoot" -ForegroundColor Cyan

$aiSession = $env:SELENITE_AI_SESSION -eq "1"
if ($aiSession -and $state -and $state.state) {
    $stateValue = $state.state.ToString().Trim().ToLowerInvariant()
    if ($stateValue -in @("canonical", "provisional") -and $env:SELENITE_ALLOW_COMMIT_GATES -ne "1") {
        throw "[guard] AI changes blocked in $stateValue state. Set SELENITE_ALLOW_COMMIT_GATES=1 for commit gates."
    }
}

if ($aiSession -and $role -eq "prod" -and $env:SELENITE_ALLOW_PROD_WRITES -ne "1") {
    throw "[guard] Production edits blocked. Set SELENITE_ALLOW_PROD_WRITES=1 to acknowledge."
}


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

if (-not (Test-Path $roleFile)) {
    Write-Host "[guard] Missing .workspace-role (expected 'prod' or 'dev')." -ForegroundColor Yellow
    return
}

$role = (Get-Content -Path $roleFile -ErrorAction Stop | Select-Object -First 1).Trim().ToLowerInvariant()
if ($role -notin @("prod", "dev")) {
    throw "[guard] Invalid .workspace-role value '$role'. Use 'prod' or 'dev'."
}

Write-Host "[guard] Workspace role: $role" -ForegroundColor Cyan
Write-Host "[guard] Repo root: $repoRoot" -ForegroundColor Cyan

if ($role -eq "prod" -and $env:SELENITE_ALLOW_PROD_WRITES -ne "1") {
    throw "[guard] Production edits blocked. Set SELENITE_ALLOW_PROD_WRITES=1 to acknowledge."
}

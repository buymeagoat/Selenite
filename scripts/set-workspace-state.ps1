<#
.SYNOPSIS
  Update the workspace state file that governs AI behavior.
#>
[CmdletBinding()]
param(
    [ValidateSet("dev", "prod")]
    [string]$Role = "",
    [ValidateSet("writeable", "provisional", "canonical")]
    [string]$State,
    [ValidateSet("dev", "prod")]
    [string]$CanonicalOwner = "",
    [string]$Note = ""
)

$ErrorActionPreference = "Stop"

if ($env:SELENITE_AI_SESSION -eq "1" -and $env:SELENITE_ALLOW_STATE_CHANGES -ne "1") {
    throw "AI state changes blocked. Set SELENITE_ALLOW_STATE_CHANGES=1 to proceed."
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$stateFile = Join-Path $repoRoot ".workspace-state.json"
$roleFile = Join-Path $repoRoot ".workspace-role"

$existing = $null
if (Test-Path $stateFile) {
    try {
        $existing = Get-Content -Path $stateFile -Raw | ConvertFrom-Json
    } catch {
        $existing = $null
    }
}

if (-not $Role) {
    if ($existing -and $existing.role) {
        $Role = $existing.role
    } elseif (Test-Path $roleFile) {
        $Role = (Get-Content -Path $roleFile -ErrorAction Stop | Select-Object -First 1).Trim().ToLowerInvariant()
    } else {
        throw "Role is required when no .workspace-role or .workspace-state.json is present."
    }
}

if (-not $CanonicalOwner) {
    if ($State -eq "canonical") {
        $CanonicalOwner = $Role
    } elseif ($existing -and $existing.canonical_owner) {
        $CanonicalOwner = $existing.canonical_owner
    } else {
        $CanonicalOwner = $Role
    }
}

if (-not $Note -and $existing -and $existing.note) {
    $Note = $existing.note
}

$updatedAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$payload = [ordered]@{
    role = $Role
    state = $State
    canonical_owner = $CanonicalOwner
    note = $Note
    updated_at = $updatedAt
}

$payload | ConvertTo-Json -Depth 4 | Set-Content -Path $stateFile -Encoding UTF8
Set-Content -Path $roleFile -Value $Role -Encoding UTF8

Write-Host "Workspace state updated: role=$Role state=$State canonical_owner=$CanonicalOwner" -ForegroundColor Green

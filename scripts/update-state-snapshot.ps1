<#
.SYNOPSIS
  Update the workspace state snapshot for audit trail.

.DESCRIPTION
  Writes docs/application_documentation/STATE_SNAPSHOT.md with current
  repo state, git info, and last test run stamp. Preserves manual notes
  between markers if present.
#>
[CmdletBinding()]
param(
  [string]$Note = ""
)

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$snapshotPath = Join-Path $repoRoot "docs/application_documentation/STATE_SNAPSHOT.md"
$roleFile = Join-Path $repoRoot ".workspace-role"
$stateFile = Join-Path $repoRoot ".workspace-state.json"
$testsStamp = Join-Path $repoRoot ".last_tests_run"

$role = if (Test-Path $roleFile) { (Get-Content -Path $roleFile | Select-Object -First 1).Trim() } else { "unknown" }
$state = $null
if (Test-Path $stateFile) {
  try { $state = Get-Content -Path $stateFile -Raw | ConvertFrom-Json } catch { $state = $null }
}
$stateValue = if ($state -and $state.state) { $state.state } else { "unknown" }
$canonicalOwner = if ($state -and $state.canonical_owner) { $state.canonical_owner } else { "unknown" }

$branch = "unknown"
$commit = "unknown"
$statusLine = "unknown"
try {
  $branch = (git -C $repoRoot rev-parse --abbrev-ref HEAD).Trim()
  $commit = (git -C $repoRoot rev-parse HEAD).Trim()
  $statusLine = (git -C $repoRoot status -sb | Select-Object -First 1).Trim()
} catch {
  $branch = "unknown"
  $commit = "unknown"
  $statusLine = "unknown"
}

$lastTests = if (Test-Path $testsStamp) { (Get-Content -Path $testsStamp | Select-Object -First 1).Trim() } else { "unknown" }

$manualNotes = "- (none recorded)"
if (Test-Path $snapshotPath) {
  $existing = Get-Content -Path $snapshotPath -Raw
  if ($existing -match "(?s)<!-- MANUAL_NOTES_START -->(.*?)<!-- MANUAL_NOTES_END -->") {
    $manualNotes = $Matches[1].Trim()
    if ([string]::IsNullOrWhiteSpace($manualNotes)) {
      $manualNotes = "- (none recorded)"
    }
  }
}

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$noteLine = if ([string]::IsNullOrWhiteSpace($Note)) { "none" } else { $Note }

$content = @"
# State Snapshot (Living)

Last updated: $timestamp
Repo root: $repoRoot
Workspace role: $role
Workspace state: $stateValue
Canonical owner: $canonicalOwner
Git branch: $branch
Git commit: $commit
Working tree: $statusLine
Last tests run: $lastTests
Run note: $noteLine

## Manual Notes
<!-- MANUAL_NOTES_START -->
$manualNotes
<!-- MANUAL_NOTES_END -->

## Known Drift
- (record intentional dev/prod differences here)
"@

Set-Content -Path $snapshotPath -Value $content -Encoding ascii
Write-Host "State snapshot updated: $snapshotPath" -ForegroundColor Green

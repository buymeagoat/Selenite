# Guardrail helper to ensure untracked cleanup never touches memorialization/models/log roots.
[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$ForceProtected
)

$guardScript = Join-Path $PSScriptRoot 'workspace-guard.ps1'
if (Test-Path $guardScript) { . $guardScript }






Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot ".." )).Path
$protectedRelative = @(
    "docs/memorialization",
    "models",
    "backend/models",
    "logs",
    "backend/logs",
    "storage",
    "scratch"
)
$protectedFull = $protectedRelative | ForEach-Object {
    [System.IO.Path]::GetFullPath((Join-Path $repoRoot $_))
}

$preview = git -C $repoRoot clean -fdn
if ($LASTEXITCODE -ne 0) {
    throw "git clean preview failed"
}

$targets = @()
foreach ($line in $preview) {
    if ($line -match '^Would remove\s+(?<path>.+)$') {
        $relative = $Matches.path.Trim()
        $full = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $relative))
        $targets += [PSCustomObject]@{ Relative = $relative; Full = $full }
    }
}

if (-not $targets) {
    Write-Host "[protected-clean] Nothing to remove."
    return
}

if (-not $ForceProtected) {
    $danger = @()
    foreach ($target in $targets) {
        foreach ($protected in $protectedFull) {
            if ($target.Full.StartsWith($protected, [System.StringComparison]::OrdinalIgnoreCase)) {
                $danger += $target
                break
            }
        }
    }

    if ($danger) {
        $blocked = ($danger | Select-Object -ExpandProperty Relative | Sort-Object -Unique) -join [Environment]::NewLine
        throw "[protected-clean] Refusing to delete protected paths. Review and rerun with explicit instructions: `n$blocked"
    }
}

if ($DryRun) {
    Write-Host "[protected-clean] Dry run. Would remove:" -ForegroundColor Yellow
    $targets.Relative | Sort-Object | ForEach-Object { Write-Host "  $_" }
    return
}

Write-Host "[protected-clean] Removing:" -ForegroundColor Yellow
$targets.Relative | Sort-Object | ForEach-Object { Write-Host "  $_" }

$null = git -C $repoRoot clean -fd
if ($LASTEXITCODE -ne 0) {
    throw "git clean failed"
}

Write-Host "[protected-clean] Complete." -ForegroundColor Green





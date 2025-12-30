param(
    [Parameter(Mandatory = $true)][string]$BackupPath,
    [string]$TargetRoot,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..") | Select-Object -ExpandProperty Path
if (-not $TargetRoot) {
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $TargetRoot = Join-Path $repoRoot ("scratch\\restore-" + $timestamp)
}

$scratchRoot = Join-Path $repoRoot "scratch"
$targetFull = [System.IO.Path]::GetFullPath($TargetRoot)
$scratchFull = [System.IO.Path]::GetFullPath($scratchRoot)
if (-not $targetFull.StartsWith($scratchFull, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "TargetRoot must be inside '$scratchRoot' to avoid overwriting production assets."
}

if (Test-Path $TargetRoot) {
    if (-not $Force) {
        throw "TargetRoot '$TargetRoot' already exists. Use -Force to overwrite."
    }
    Remove-Item -Recurse -Force $TargetRoot
}

New-Item -ItemType Directory -Path $TargetRoot -Force | Out-Null

$backupResolved = Resolve-Path $BackupPath | Select-Object -ExpandProperty Path
$dbSource = Join-Path $backupResolved "database\\selenite.db"
if (Test-Path $dbSource) {
    Copy-Item -Path $dbSource -Destination (Join-Path $TargetRoot "selenite.db") -Force
}

$storageSource = Join-Path $backupResolved "storage"
if (Test-Path $storageSource) {
    Copy-Item -Path $storageSource -Destination (Join-Path $TargetRoot "storage") -Recurse -Force
}

$logsSource = Join-Path $backupResolved "logs"
if (Test-Path $logsSource) {
    Copy-Item -Path $logsSource -Destination (Join-Path $TargetRoot "logs") -Recurse -Force
}

$modelsSource = Join-Path $backupResolved "backend\\models"
if (Test-Path $modelsSource) {
    $modelsDest = Join-Path $TargetRoot "backend\\models"
    Copy-Item -Path $modelsSource -Destination $modelsDest -Recurse -Force
}

Write-Host "Restore complete: $TargetRoot" -ForegroundColor Green
Write-Output $TargetRoot

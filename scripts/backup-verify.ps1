param(
    [string]$BackupRoot,
    [string]$Tag = (Get-Date -Format "yyyyMMdd-HHmmss")
,
    [switch]$IncludeLogs,
    [switch]$IncludeModels,
    [switch]$IncludeTestStorage,
    [string]$RestoreRoot
)

$guardScript = Join-Path $PSScriptRoot 'workspace-guard.ps1'
if (Test-Path $guardScript) { . $guardScript }





$ErrorActionPreference = "Stop"

$backupScript = Join-Path $PSScriptRoot "backup-system.ps1"
$restoreScript = Join-Path $PSScriptRoot "restore-system.ps1"
$verifyScript = Join-Path $PSScriptRoot "verify-backup.ps1"

$backupPath = & $backupScript -BackupRoot $BackupRoot -Tag $Tag -IncludeLogs:$IncludeLogs -IncludeModels:$IncludeModels -IncludeTestStorage:$IncludeTestStorage

if (-not $RestoreRoot) {
    $repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..") | Select-Object -ExpandProperty Path
    $RestoreRoot = Join-Path $repoRoot ("scratch\\restore-" + $Tag)
}

$restoredPath = & $restoreScript -BackupPath $backupPath -TargetRoot $RestoreRoot -Force
& $verifyScript -BackupPath $backupPath -TargetRoot $restoredPath

Write-Host "Backup and restore verification complete." -ForegroundColor Green





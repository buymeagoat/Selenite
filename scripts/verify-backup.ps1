param(
    [Parameter(Mandatory = $true)
][string]$BackupPath,
    [Parameter(Mandatory = $true)][string]$TargetRoot
)

$guardScript = Join-Path $PSScriptRoot 'workspace-guard.ps1'
if (Test-Path $guardScript) { . $guardScript }





$ErrorActionPreference = "Stop"

$backupResolved = Resolve-Path $BackupPath | Select-Object -ExpandProperty Path
$manifestPath = Join-Path $backupResolved "manifest.csv"
if (-not (Test-Path $manifestPath)) {
    throw "Manifest not found at '$manifestPath'."
}

$entries = Import-Csv -Path $manifestPath
$missing = @()
$mismatch = @()

foreach ($entry in $entries) {
    $relative = $entry.Path -replace "/", "\\"
    $targetPath = Join-Path $TargetRoot $relative
    if (-not (Test-Path $targetPath)) {
        $missing += $entry.Path
        continue
    }

    $hash = (Get-FileHash -Algorithm SHA256 -Path $targetPath).Hash
    if ($hash -ne $entry.Hash) {
        $mismatch += $entry.Path
    }
}

if ($missing.Count -gt 0 -or $mismatch.Count -gt 0) {
    Write-Host "Backup verification failed." -ForegroundColor Red
    if ($missing.Count -gt 0) {
        Write-Host "Missing files:" -ForegroundColor Red
        $missing | ForEach-Object { Write-Host " - $_" }
    }
    if ($mismatch.Count -gt 0) {
        Write-Host "Hash mismatches:" -ForegroundColor Red
        $mismatch | ForEach-Object { Write-Host " - $_" }
    }
    exit 1
}

Write-Host "Backup verification passed." -ForegroundColor Green





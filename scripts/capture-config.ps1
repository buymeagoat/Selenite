<#
.SYNOPSIS
  Capture configuration files for promotion rollback safety.

.DESCRIPTION
  Copies .env* files into scratch/config/<timestamp>/ and prints the path.
#>
[CmdletBinding()]
param(
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$outputRoot = if ($OutputDir) { $OutputDir } else { Join-Path $repoRoot "scratch\\config" }
$timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd-HHmmss")
$targetDir = Join-Path $outputRoot $timestamp

New-Item -ItemType Directory -Force -Path $targetDir | Out-Null

$envFiles = Get-ChildItem -Path $repoRoot -Filter ".env*" -File -ErrorAction SilentlyContinue
if (-not $envFiles) {
    Write-Host "No .env* files found at repo root." -ForegroundColor Yellow
}

foreach ($file in $envFiles) {
    Copy-Item -Path $file.FullName -Destination (Join-Path $targetDir $file.Name) -Force
}

Write-Host "Config capture saved: $targetDir" -ForegroundColor Green

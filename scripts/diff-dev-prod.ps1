<#
.SYNOPSIS
  Compare dev and prod repositories to identify promotion deltas.

.DESCRIPTION
  Lists files that are added, modified, or missing between the dev repo
  (current repo) and the prod repo (default sibling "Selenite").

.PARAMETER ProdPath
  Path to the prod repo. Defaults to sibling directory "Selenite".

.PARAMETER IncludeUntracked
  Include untracked dev files in the report.
#>
[CmdletBinding()]
param(
    [string]$ProdPath = "",
    [switch]$IncludeUntracked
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$devRoot = Resolve-Path (Join-Path $scriptRoot '..')

if (-not $ProdPath -or $ProdPath.Trim().Length -eq 0) {
    $ProdPath = Join-Path (Split-Path $devRoot -Parent) 'Selenite'
}

if (-not (Test-Path $ProdPath)) {
    throw "Prod repo not found at $ProdPath. Use -ProdPath to override."
}

function Get-TrackedFiles {
    param([string]$Repo)
    return @((git -C $Repo ls-files) | Where-Object { $_ -and $_.Trim().Length -gt 0 })
}

function Get-UntrackedFiles {
    param([string]$Repo)
    return @((git -C $Repo ls-files --others --exclude-standard) | Where-Object { $_ -and $_.Trim().Length -gt 0 })
}

function Get-TrackedFileHashes {
    param([string]$Repo)
    $files = @(Get-TrackedFiles -Repo $Repo)
    $hashes = @{}
    if (-not $files -or $files.Count -eq 0) {
        return @{ Files = @(); Hashes = $hashes }
    }
    $hashList = $files | git -C $Repo hash-object --stdin-paths
    for ($i = 0; $i -lt $files.Count; $i++) {
        $hashes[$files[$i]] = $hashList[$i]
    }
    return @{ Files = $files; Hashes = $hashes }
}

$devSnapshot = Get-TrackedFileHashes -Repo $devRoot
$prodSnapshot = Get-TrackedFileHashes -Repo $ProdPath
$devFiles = $devSnapshot.Files
$prodFiles = $prodSnapshot.Files
$devHashes = $devSnapshot.Hashes
$prodHashes = $prodSnapshot.Hashes

$devSet = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
$prodSet = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
$devFiles | ForEach-Object { [void]$devSet.Add($_) }
$prodFiles | ForEach-Object { [void]$prodSet.Add($_) }

$onlyInDev = [System.Collections.Generic.List[string]]::new()
$onlyInProd = [System.Collections.Generic.List[string]]::new()
$modified = [System.Collections.Generic.List[string]]::new()

foreach ($file in $devFiles) {
    if (-not $prodSet.Contains($file)) {
        $onlyInDev.Add($file)
        continue
    }
    $devHash = $devHashes[$file]
    $prodHash = $prodHashes[$file]
    if ($devHash -ne $prodHash) {
        $modified.Add($file)
    }
}

foreach ($file in $prodFiles) {
    if (-not $devSet.Contains($file)) {
        $onlyInProd.Add($file)
    }
}

$untracked = @()
if ($IncludeUntracked) {
    $untracked = Get-UntrackedFiles -Repo $devRoot
}

Write-Host "=== Dev/Prod Diff ===" -ForegroundColor Cyan
Write-Host ("Dev:  {0}" -f $devRoot) -ForegroundColor DarkGray
Write-Host ("Prod: {0}" -f (Resolve-Path $ProdPath)) -ForegroundColor DarkGray
Write-Host ""

Write-Host ("Added in dev ({0})" -f $onlyInDev.Count) -ForegroundColor Yellow
$onlyInDev | Sort-Object | ForEach-Object { Write-Host " + $_" }
Write-Host ""

Write-Host ("Modified in dev ({0})" -f $modified.Count) -ForegroundColor Yellow
$modified | Sort-Object | ForEach-Object { Write-Host " ~ $_" }
Write-Host ""

Write-Host ("Missing in dev ({0})" -f $onlyInProd.Count) -ForegroundColor Yellow
$onlyInProd | Sort-Object | ForEach-Object { Write-Host " - $_" }
Write-Host ""

if ($IncludeUntracked) {
    Write-Host ("Untracked in dev ({0})" -f @($untracked).Count) -ForegroundColor Yellow
    @($untracked) | Sort-Object | ForEach-Object { Write-Host " ? $_" }
    Write-Host ""
}

Write-Host "Done." -ForegroundColor Green

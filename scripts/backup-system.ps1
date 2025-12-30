param(
    [string]$BackupRoot,
    [string]$Tag = (Get-Date -Format "yyyyMMdd-HHmmss"),
    [switch]$IncludeLogs,
    [switch]$IncludeModels,
    [switch]$IncludeTestStorage,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..") | Select-Object -ExpandProperty Path
$storageRoot = Join-Path $repoRoot "storage"
$backupRootResolved = if ($BackupRoot) { $BackupRoot } else { Join-Path $storageRoot "backups" }
$backupDir = Join-Path $backupRootResolved ("system-" + $Tag)

function Get-DatabaseUrl {
    if ($env:DATABASE_URL) {
        return $env:DATABASE_URL
    }

    $envPath = Join-Path $repoRoot ".env"
    if (Test-Path $envPath) {
        $line = Get-Content $envPath | Where-Object { $_ -match "^\s*DATABASE_URL\s*=" } | Select-Object -First 1
        if ($line) {
            $value = $line -replace "^\s*DATABASE_URL\s*=\s*", ""
            return $value.Trim("`"'", " ")
        }
    }

    return "sqlite+aiosqlite:///./selenite.db"
}

function Resolve-SqlitePath {
    param([string]$DatabaseUrl)

    if (-not $DatabaseUrl) {
        return $null
    }

    if ($DatabaseUrl -notmatch "^sqlite") {
        return $null
    }

    $pathPart = $DatabaseUrl -replace "^sqlite(\\+aiosqlite)?:///+", ""
    $pathPart = $pathPart -replace "\\?.*$", ""
    if (-not $pathPart) {
        return $null
    }

    if ([System.IO.Path]::IsPathRooted($pathPart)) {
        return $pathPart
    }

    return (Join-Path $repoRoot $pathPart)
}

function Should-ExcludeStoragePath {
    param([string]$FullPath)

    $excludedRoots = @(
        (Join-Path $storageRoot "backups")
    )

    if (-not $IncludeTestStorage) {
        $excludedRoots += (Join-Path $storageRoot "test-media")
        $excludedRoots += (Join-Path $storageRoot "test-transcripts")
    }

    foreach ($excluded in $excludedRoots) {
        if ($FullPath.StartsWith($excluded, [System.StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }

    return $false
}

if (-not $DryRun) {
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
}

$manifest = @()
$dbUrl = Get-DatabaseUrl
$dbPath = Resolve-SqlitePath -DatabaseUrl $dbUrl
if (-not $dbPath) {
    throw "Database URL '$dbUrl' is not sqlite or could not be resolved. Provide a sqlite DATABASE_URL before backing up."
}

if (-not (Test-Path $dbPath)) {
    throw "Database file not found at '$dbPath'."
}

$dbDest = Join-Path $backupDir "database"
if (-not $DryRun) {
    New-Item -ItemType Directory -Path $dbDest -Force | Out-Null
    Copy-Item -Path $dbPath -Destination (Join-Path $dbDest "selenite.db") -Force
}

$dbHash = (Get-FileHash -Algorithm SHA256 -Path $dbPath).Hash
$manifest += [pscustomobject]@{
    Path = "database/selenite.db"
    Hash = $dbHash
    Size = (Get-Item $dbPath).Length
}

if (Test-Path $storageRoot) {
    $storageFiles = Get-ChildItem -Path $storageRoot -Recurse -File | Where-Object { -not (Should-ExcludeStoragePath -FullPath $_.FullName) }
    foreach ($file in $storageFiles) {
        $relative = $file.FullName.Substring($storageRoot.Length + 1)
        $dest = Join-Path $backupDir (Join-Path "storage" $relative)
        if (-not $DryRun) {
            New-Item -ItemType Directory -Path (Split-Path $dest) -Force | Out-Null
            Copy-Item -Path $file.FullName -Destination $dest -Force
        }

        $hash = (Get-FileHash -Algorithm SHA256 -Path $file.FullName).Hash
        $manifest += [pscustomobject]@{
            Path = ("storage/" + $relative).Replace("\\", "/")
            Hash = $hash
            Size = $file.Length
        }
    }
}

if ($IncludeLogs) {
    $logsRoot = Join-Path $repoRoot "logs"
    if (Test-Path $logsRoot) {
        $logFiles = Get-ChildItem -Path $logsRoot -Recurse -File
        foreach ($file in $logFiles) {
            $relative = $file.FullName.Substring($logsRoot.Length + 1)
            $dest = Join-Path $backupDir (Join-Path "logs" $relative)
            if (-not $DryRun) {
                New-Item -ItemType Directory -Path (Split-Path $dest) -Force | Out-Null
                Copy-Item -Path $file.FullName -Destination $dest -Force
            }

            $hash = (Get-FileHash -Algorithm SHA256 -Path $file.FullName).Hash
            $manifest += [pscustomobject]@{
                Path = ("logs/" + $relative).Replace("\\", "/")
                Hash = $hash
                Size = $file.Length
            }
        }
    }
}

if ($IncludeModels) {
    $modelsRoot = Join-Path $repoRoot "backend\\models"
    if (Test-Path $modelsRoot) {
        $modelFiles = Get-ChildItem -Path $modelsRoot -Recurse -File
        foreach ($file in $modelFiles) {
            $relative = $file.FullName.Substring($modelsRoot.Length + 1)
            $dest = Join-Path $backupDir (Join-Path "backend\\models" $relative)
            if (-not $DryRun) {
                New-Item -ItemType Directory -Path (Split-Path $dest) -Force | Out-Null
                Copy-Item -Path $file.FullName -Destination $dest -Force
            }

            $hash = (Get-FileHash -Algorithm SHA256 -Path $file.FullName).Hash
            $manifest += [pscustomobject]@{
                Path = ("backend/models/" + $relative).Replace("\\", "/")
                Hash = $hash
                Size = $file.Length
            }
        }
    }
}

if (-not $DryRun) {
    $manifestPath = Join-Path $backupDir "manifest.csv"
    $manifest | Export-Csv -Path $manifestPath -NoTypeInformation

    $metadata = [pscustomobject]@{
        created_at = (Get-Date).ToString("o")
        repo_root = $repoRoot
        database_url = $dbUrl
        database_path = $dbPath
        include_logs = [bool]$IncludeLogs
        include_models = [bool]$IncludeModels
        include_test_storage = [bool]$IncludeTestStorage
    }
    $metadata | ConvertTo-Json -Depth 4 | Set-Content -Path (Join-Path $backupDir "backup.json") -Encoding utf8
}

Write-Host "Backup complete: $backupDir" -ForegroundColor Green
Write-Output $backupDir

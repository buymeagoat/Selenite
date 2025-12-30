param(
    [string]$BackupRoot,
    [string]$Tag = (Get-Date -Format "yyyyMMdd-HHmmss"),
    [switch]$IncludeLogs,
    [switch]$IncludeModels,
    [switch]$IncludeTestStorage,
    [switch]$DryRun,
    [switch]$SelfTest
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..") | Select-Object -ExpandProperty Path
$storageRoot = Join-Path $repoRoot "storage"
$backupRootResolved = if ($BackupRoot) { $BackupRoot } else { Join-Path $storageRoot "backups" }
$backupDir = Join-Path $backupRootResolved ("system-" + $Tag)

function Normalize-EnvValue {
    param([string]$Value)

    if ($null -eq $Value) {
        return $null
    }

    $trimmed = $Value.Trim()
    if ($trimmed.Length -ge 2) {
        if (
            ($trimmed.StartsWith('"') -and $trimmed.EndsWith('"')) -or
            ($trimmed.StartsWith("'") -and $trimmed.EndsWith("'"))
        ) {
            $trimmed = $trimmed.Substring(1, $trimmed.Length - 2)
        }
    }

    return $trimmed
}

function Get-SqlitePathPart {
    param([string]$DatabaseUrl)

    $normalizedUrl = Normalize-EnvValue -Value $DatabaseUrl
    if (-not $normalizedUrl) {
        return $null
    }

    $prefixes = @(
        "sqlite+aiosqlite:///",
        "sqlite:///"
    )

    foreach ($prefix in $prefixes) {
        if ($normalizedUrl.StartsWith($prefix)) {
            $pathPart = $normalizedUrl.Substring($prefix.Length)
            if ([string]::IsNullOrWhiteSpace($pathPart) -or $pathPart -eq "." -or $pathPart -eq "./") {
                return $null
            }
            return $pathPart
        }
    }

    return $null
}

function Invoke-SelfTest {
    $cases = @(
        @{ Input = 'sqlite+aiosqlite:///./selenite.db'; Expected = 'sqlite+aiosqlite:///./selenite.db' },
        @{ Input = ' "sqlite+aiosqlite:///./selenite.db" '; Expected = 'sqlite+aiosqlite:///./selenite.db' },
        @{ Input = " 'sqlite+aiosqlite:///./selenite.db' "; Expected = 'sqlite+aiosqlite:///./selenite.db' }
    )

    foreach ($case in $cases) {
        $actual = Normalize-EnvValue -Value $case.Input
        if ($actual -ne $case.Expected) {
            throw "SelfTest failed for input '$($case.Input)'. Expected '$($case.Expected)', got '$actual'."
        }
    }

    $pathPart = Get-SqlitePathPart -DatabaseUrl 'sqlite+aiosqlite:///./backend/selenite.db'
    if ($pathPart -ne './backend/selenite.db') {
        throw "SelfTest failed: sqlite path parse returned '$pathPart'."
    }

    Write-Host "backup-system self-test passed." -ForegroundColor Green
}

function Get-DatabaseUrl {
    if ($env:DATABASE_URL) {
        return $env:DATABASE_URL
    }

    $envPath = Join-Path $repoRoot ".env"
    if (Test-Path $envPath) {
        $line = Get-Content $envPath | Where-Object { $_ -match "^\s*DATABASE_URL\s*=" } | Select-Object -First 1
        if ($line) {
            $value = $line -replace "^\s*DATABASE_URL\s*=\s*", ""
            return (Normalize-EnvValue -Value $value)
        }
    }

    return "sqlite+aiosqlite:///./selenite.db"
}

function Resolve-SqlitePath {
    param([string]$DatabaseUrl)

    $pathPart = Get-SqlitePathPart -DatabaseUrl $DatabaseUrl
    if (-not $pathPart) {
        return $null
    }

    $pathPart = $pathPart -replace "\?.*$", ""

    if ([System.IO.Path]::IsPathRooted($pathPart)) {
        return $pathPart
    }

    $relativePart = $pathPart
    if ($relativePart.StartsWith("./")) {
        $relativePart = $relativePart.Substring(2)
    } elseif ($relativePart.StartsWith(".\\")) {
        $relativePart = $relativePart.Substring(2)
    }

    if ([string]::IsNullOrWhiteSpace($relativePart)) {
        return $null
    }

    $joinedPath = Join-Path $repoRoot $relativePart
    if ($env:BACKUP_DEBUG) {
        Write-Host "DEBUG: repoRoot=$repoRoot"
        Write-Host "DEBUG: relativePart=$relativePart"
        Write-Host "DEBUG: joinedPath=$joinedPath"
    }
    return $joinedPath
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

function Get-SharedFileHash {
    param([string]$Path)

    $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
    try {
        return (Get-FileHash -Algorithm SHA256 -InputStream $stream).Hash
    } finally {
        $stream.Dispose()
    }
}

if ($SelfTest) {
    Invoke-SelfTest
    return
}

if (-not $DryRun) {
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
}

$manifest = @()
$dbUrl = Get-DatabaseUrl
$dbPath = Resolve-SqlitePath -DatabaseUrl $dbUrl
if ($env:BACKUP_DEBUG) {
    $normalizedUrl = Normalize-EnvValue -Value $dbUrl
    $pathPart = Get-SqlitePathPart -DatabaseUrl $dbUrl
    Write-Host "DEBUG: dbUrl=$dbUrl"
    Write-Host "DEBUG: normalizedUrl=$normalizedUrl"
    Write-Host "DEBUG: pathPart=$pathPart"
    Write-Host "DEBUG: dbPath=$dbPath"
}
if (-not $dbPath) {
    throw "Database URL '$dbUrl' is not sqlite or could not be resolved. Provide a sqlite DATABASE_URL before backing up."
}

if (-not (Test-Path -Path $dbPath -PathType Leaf)) {
    throw "Database file not found at '$dbPath'."
}

$dbDest = Join-Path $backupDir "database"
$dbBackupPath = Join-Path $dbDest "selenite.db"
if (-not $DryRun) {
    New-Item -ItemType Directory -Path $dbDest -Force | Out-Null
    Copy-Item -Path $dbPath -Destination $dbBackupPath -Force
}

$dbHashPath = if ($DryRun) { $dbPath } else { $dbBackupPath }
$dbHash = Get-SharedFileHash -Path $dbHashPath
$manifest += [pscustomobject]@{
    Path = "database/selenite.db"
    Hash = $dbHash
    Size = (Get-Item $dbHashPath).Length
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

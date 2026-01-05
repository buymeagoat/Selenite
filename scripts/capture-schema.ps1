<#
.SYNOPSIS
  Capture a SQLite schema snapshot for promotion logs.

.DESCRIPTION
  Writes a schema snapshot to scratch/schema/<timestamp>-<label>.sql by default.
#>
[CmdletBinding()]
param(
    [string]$DatabasePath = "",
    [string]$Label = "schema",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$defaultDb = Join-Path $repoRoot "backend\\selenite.db"
$dbPath = if ($DatabasePath) { $DatabasePath } else { $defaultDb }

if (-not (Test-Path $dbPath)) {
    throw "Database not found at $dbPath"
}

$outputRoot = if ($OutputDir) { $OutputDir } else { Join-Path $repoRoot "scratch\\schema" }
New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null

$timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd-HHmmss")
$safeLabel = ($Label -replace '[^A-Za-z0-9_-]', '_')
$outFile = Join-Path $outputRoot "$timestamp-$safeLabel.sql"

$sqlite = Get-Command sqlite3 -ErrorAction SilentlyContinue
if ($sqlite) {
    & $sqlite.Path $dbPath ".schema" | Out-File -FilePath $outFile -Encoding UTF8
    Write-Host "Schema snapshot saved: $outFile" -ForegroundColor Green
    return
}

$py = @"
import sqlite3
import sys

db_path = r"${dbPath}"
out_path = r"${outFile}"
conn = sqlite3.connect(db_path)
rows = conn.execute("select sql from sqlite_master where sql is not null order by type, name").fetchall()
conn.close()
with open(out_path, "w", encoding="utf-8") as f:
    for row in rows:
        f.write(row[0].strip() + ";\n")
"@

$py | python - | Out-Null
Write-Host "Schema snapshot saved (python fallback): $outFile" -ForegroundColor Green

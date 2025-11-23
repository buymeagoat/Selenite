<#
    Bootstrap script for Selenite.
    Executes the same steps documented in BOOTSTRAP.md.
    Run from a PowerShell prompt:  .\bootstrap.ps1
#>

param(
    [switch]$SkipPreflight,
    [switch]$Dev,            # Use uvicorn reload; ENVIRONMENT=development
    [switch]$Seed,           # Run app.seed
    [switch]$ForceInstall    # Force npm install even if node_modules exists
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$BackendDir = Join-Path $Root 'backend'
$FrontendDir = Join-Path $Root 'frontend'
$MediaDir = Join-Path $Root 'storage\media'
$TranscriptDir = Join-Path $Root 'storage\transcripts'
New-Item -ItemType Directory -Force -Path $MediaDir | Out-Null
New-Item -ItemType Directory -Force -Path $TranscriptDir | Out-Null

function Write-Section($Message) {
    Write-Host ""
    Write-Host "=== $Message ===" -ForegroundColor Cyan
}

function Invoke-Step {
    param(
        [string]$Message,
        [scriptblock]$Action
    )
    Write-Section $Message
    try {
        & $Action
    } catch {
        Write-Host "Step failed: $Message" -ForegroundColor Red
        Write-Host $_ -ForegroundColor Red
        exit 1
    }
}

if (-not $SkipPreflight) {
    Invoke-Step "Pre-flight cleanup" {
        $logRoot = Join-Path $Root 'logs'
        Get-ChildItem -Path $logRoot -Filter *.log -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
            $_.IsReadOnly = $false
        }
        Get-Process python,node -ErrorAction SilentlyContinue | Stop-Process -Force
    }
}

Invoke-Step "Backend virtualenv" {
    Set-Location $BackendDir
    if (-not (Test-Path .\.venv\Scripts\python.exe)) {
        Write-Host "Creating virtual environment..."
        python -m venv .venv
    }
}

Invoke-Step "Backend dependencies" {
    Set-Location $BackendDir
    .\.venv\Scripts\python.exe -m pip install --upgrade pip
    .\.venv\Scripts\python.exe -m pip install -r requirements-minimal.txt
}

Invoke-Step "Database migrations (and seed if requested)" {
    Set-Location $BackendDir
    if (Test-Path .\alembic.ini) {
        .\.venv\Scripts\python.exe -m alembic upgrade head
    }
    if ($Seed) {
        .\.venv\Scripts\python.exe -m app.seed
    }
}

Invoke-Step "Frontend dependencies" {
    Set-Location $FrontendDir
    if ((Test-Path .\node_modules) -and (-not $ForceInstall)) {
        Write-Host "node_modules exists; skipping npm install (use -ForceInstall to reinstall)."
    } else {
        attrib -R /S /D node_modules | Out-Null
        npm install
    }
}

Invoke-Step "Start backend API (new window)" {
    $envBlock = @"
`$env:DISABLE_FILE_LOGS = '1'
`$env:ENVIRONMENT = '$([bool]$Dev -eq $true ? 'development' : 'production')'
`$env:ALLOW_LOCALHOST_CORS = '1'
`$env:MEDIA_STORAGE_PATH = '$MediaDir'
`$env:TRANSCRIPT_STORAGE_PATH = '$TranscriptDir'
"@
    $uvicornArgs = $Dev ? "--reload" : ""
$backendCmd = @"
cd "$BackendDir"
$envBlock
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8100 --app-dir app $uvicornArgs
"@
    Start-Process -FilePath "pwsh" -ArgumentList "-NoExit", "-Command", $backendCmd
    Write-Host "Backend starting on http://127.0.0.1:8100 (check new window)." -ForegroundColor Green
}

Invoke-Step "Start frontend production preview (new window)" {
    $frontendCmd = @"
cd "$FrontendDir"
npm run start:prod
"@
    Start-Process -FilePath "pwsh" -ArgumentList "-NoExit", "-Command", $frontendCmd
    Write-Host "Frontend starting on http://127.0.0.1:5173 (check new window)." -ForegroundColor Green
}

Invoke-Step "Verify backend via smoke test" {
    Set-Location $Root
    $pythonExe = Join-Path $BackendDir '.venv\Scripts\python.exe'
    $smokeScript = Join-Path $Root 'scripts\smoke_test.py'
    & $pythonExe $smokeScript --base-url http://127.0.0.1:8100 --health-timeout 90
}

Write-Section "All done"
Write-Host "Backend and frontend processes have been launched in separate PowerShell windows."
Write-Host "If either window reports an error, resolve it before proceeding." -ForegroundColor Yellow

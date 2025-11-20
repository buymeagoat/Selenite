<#
    Bootstrap script for Selenite.
    Executes the same steps documented in BOOTSTRAP.md.
    Run from a PowerShell prompt:  .\bootstrap.ps1
#>

param(
    [switch]$SkipPreflight
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$BackendDir = Join-Path $Root 'backend'
$FrontendDir = Join-Path $Root 'frontend'

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
    & $Action
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

Invoke-Step "Frontend dependencies" {
    Set-Location $FrontendDir
    if (Test-Path .\node_modules) {
        attrib -R /S /D node_modules | Out-Null
    }
    npm install
}

Invoke-Step "Start backend API (new window)" {
    $backendCmd = @"
cd "$BackendDir"
$env:DISABLE_FILE_LOGS = '1'
$env:ENVIRONMENT = 'production'
$env:ALLOW_LOCALHOST_CORS = '1'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8100 --app-dir app
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

Write-Section "All done"
Write-Host "Backend and frontend processes have been launched in separate PowerShell windows."
Write-Host "If either window reports an error, resolve it before proceeding." -ForegroundColor Yellow

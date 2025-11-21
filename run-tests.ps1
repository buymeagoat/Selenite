<#
.SYNOPSIS
    Single entry point for running Selenite's automated test suites.

.DESCRIPTION
    - Ensures backend virtualenv and frontend node_modules exist (unless skipped).
    - Executes backend pytest with coverage, frontend Vitest coverage, and Playwright E2E tests.
    - Mirrors the commands documented in docs/build/testing/TESTING_PROTOCOL.md so humans and AIs can
      run the entire battery with one PowerShell command.

.PARAMETER SkipBackend
    Skips backend dependency checks and pytest run.

.PARAMETER SkipFrontend
    Skips frontend dependency checks and Vitest coverage run.

.PARAMETER SkipE2E
    Skips Playwright end-to-end tests.

.PARAMETER ForceBackendInstall
    Forces backend pip install even if .venv already exists.

.PARAMETER ForceFrontendInstall
    Forces `npm install` even if node_modules already exists.
#>

[CmdletBinding()]
param(
    [switch]$SkipBackend,
    [switch]$SkipFrontend,
    [switch]$SkipE2E,
    [switch]$ForceBackendInstall,
    [switch]$ForceFrontendInstall
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot
$BackendDir = Join-Path $RepoRoot "backend"
$FrontendDir = Join-Path $RepoRoot "frontend"

function Get-BackendPythonPath {
    if ($IsWindows) {
        return Join-Path $BackendDir ".venv\Scripts\python.exe"
    }
    else {
        return Join-Path $BackendDir ".venv/bin/python"
    }
}

$script:BackendPython = Get-BackendPythonPath

$MemorialRoot = Join-Path $RepoRoot "docs/memorialization/test-runs"
if (-not (Test-Path $MemorialRoot)) {
    New-Item -ItemType Directory -Force -Path $MemorialRoot | Out-Null
}
$runParts = @()
if (-not $SkipBackend) { $runParts += "backend" }
if (-not $SkipFrontend) { $runParts += "frontend" }
if (-not $SkipE2E) { $runParts += "e2e" }
if ($runParts.Count -eq 0) { $runParts += "notes" }
$RunStamp = Get-Date -Format "yyyyMMdd-HHmmss"
$RunDirName = "$RunStamp-" + ($runParts -join "+")
$RunDir = Join-Path $MemorialRoot $RunDirName
New-Item -ItemType Directory -Force -Path $RunDir | Out-Null
$TranscriptPath = Join-Path $RunDir "run-tests.log"
Start-Transcript -Path $TranscriptPath | Out-Null

function Write-Section {
    param([string]$Message)
    Write-Host "`n=== $Message ===" -ForegroundColor Cyan
}

function Get-SystemPython {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        $python = Get-Command python3 -ErrorAction SilentlyContinue
    }
    if (-not $python) {
        throw "Python is not installed or not on PATH."
    }
    return $python.Path
}

function Ensure-BackendEnv {
    param([switch]$Force)
    Push-Location $BackendDir
    try {
        $script:BackendPython = Get-BackendPythonPath
        if (-not (Test-Path $script:BackendPython)) {
            Write-Host "Creating backend virtualenv (.venv)..." -ForegroundColor Yellow
            $pythonExe = Get-SystemPython
            & $pythonExe -m venv .venv
            $Force = $true
            $script:BackendPython = Get-BackendPythonPath
        }

        if ($Force) {
            Write-Host "Installing backend dependencies..." -ForegroundColor Yellow
            & $script:BackendPython -m pip install --upgrade pip
            & $script:BackendPython -m pip install -r requirements-minimal.txt
        } else {
            Write-Host "Backend dependencies already present. Use -ForceBackendInstall to reinstall." -ForegroundColor DarkGray
        }
    }
    finally {
        Pop-Location
    }
}

function Run-BackendTests {
    Write-Section "Running backend pytest suite"
    Push-Location $BackendDir
    try {
        & $script:BackendPython -m pytest --maxfail=1 --disable-warnings --cov=app --cov-report=term
    }
    finally {
        Pop-Location
    }
}

function Ensure-FrontendDeps {
    param([switch]$Force)
    Push-Location $FrontendDir
    try {
        if ($Force -or -not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
            Write-Host "Installing frontend dependencies (npm install)..." -ForegroundColor Yellow
            npm install
        } else {
            Write-Host "Frontend node_modules already present. Use -ForceFrontendInstall to reinstall." -ForegroundColor DarkGray
        }
    }
    finally {
        Pop-Location
    }
}

function Run-FrontendTests {
    Write-Section "Running frontend Vitest coverage"
    Push-Location $FrontendDir
    try {
        npm run test:coverage
        npm run coverage:summary
    }
    finally {
        Pop-Location
    }
}

function Run-E2E {
    Write-Section "Running Playwright E2E suite"
    Push-Location $FrontendDir
    try {
        npm run e2e:full
    }
    finally {
        Pop-Location
    }
}

# --- Main execution ---
try {
    if (-not $SkipBackend) {
        Ensure-BackendEnv -Force:$ForceBackendInstall
        Run-BackendTests
    } else {
        Write-Host "Skipping backend tests (-SkipBackend set)." -ForegroundColor Yellow
    }

    if (-not $SkipFrontend) {
        Ensure-FrontendDeps -Force:$ForceFrontendInstall
        Run-FrontendTests
    } else {
        Write-Host "Skipping frontend tests (-SkipFrontend set)." -ForegroundColor Yellow
    }

    if (-not $SkipE2E) {
        Run-E2E
    } else {
        Write-Host "Skipping Playwright E2E (-SkipE2E set)." -ForegroundColor Yellow
    }

    Write-Section "All requested test suites completed"
}
finally {
    try { Stop-Transcript | Out-Null } catch {}

    if (-not $SkipBackend) {
        $backendCov = Join-Path $BackendDir ".coverage"
        if (Test-Path $backendCov) {
            Copy-Item $backendCov (Join-Path $RunDir "backend.coverage") -Force
        }
    }

    if (-not $SkipFrontend) {
        $frontendSummary = Join-Path $FrontendDir "coverage/coverage-summary.json"
        if (Test-Path $frontendSummary) {
            Copy-Item $frontendSummary (Join-Path $RunDir "frontend-coverage-summary.json") -Force
        }
    }

    if (-not $SkipE2E) {
        $playwrightReport = Join-Path $FrontendDir "playwright-report"
        if (Test-Path $playwrightReport) {
            $dest = Join-Path $RunDir "playwright-report"
            Copy-Item $playwrightReport $dest -Recurse -Force
        }
        $playwrightResults = Join-Path $FrontendDir "test-results"
        if (Test-Path $playwrightResults) {
            $destResults = Join-Path $RunDir "playwright-test-results"
            Copy-Item $playwrightResults $destResults -Recurse -Force
        }
    }
}

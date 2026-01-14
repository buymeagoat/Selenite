<#
.SYNOPSIS
    Single entry point for running Selenite's automated test suites.

.DESCRIPTION
    - Ensures backend virtualenv and frontend node_modules exist (unless skipped).
    - Executes backend pytest with coverage, frontend Vitest coverage, and Playwright E2E tests.
    - Runs the entire test battery with one PowerShell command.

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

$guardScript = Join-Path $PSScriptRoot 'workspace-guard.ps1'
if (Test-Path $guardScript) { . $guardScript }






$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $RepoRoot
$BackendDir = Join-Path $RepoRoot "backend"
$FrontendDir = Join-Path $RepoRoot "frontend"

$roleFile = Join-Path $RepoRoot '.workspace-role'
$wsRole = if (Test-Path $roleFile) { (Get-Content -Path $roleFile -ErrorAction Stop | Select-Object -First 1).Trim().ToLowerInvariant() } else { '' }
$isProd = $wsRole -eq 'prod'

$envBackendPort = $null
$envFrontendPort = $null
$envFile = Join-Path $RepoRoot '.env'
if (Test-Path $envFile) {
    $portMatch = Select-String -Path $envFile -Pattern '^\s*PORT\s*=\s*(\d+)' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($portMatch) { $envBackendPort = [int]$portMatch.Matches[0].Groups[1].Value }

    $frontendMatch = Select-String -Path $envFile -Pattern '^\s*FRONTEND_URL\s*=\s*.+:(\d+)' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($frontendMatch) { $envFrontendPort = [int]$frontendMatch.Matches[0].Groups[1].Value }
}

$BackendPort = if ($env:SELENITE_BACKEND_PORT) { [int]$env:SELENITE_BACKEND_PORT } elseif ($envBackendPort) { $envBackendPort } elseif ($isProd) { 8100 } else { 8201 }
$FrontendPort = if ($env:SELENITE_FRONTEND_PORT) { [int]$env:SELENITE_FRONTEND_PORT } elseif ($envFrontendPort) { $envFrontendPort } elseif ($isProd) { 5173 } else { 5174 }

function Get-BackendPythonPath {
    if ($IsWindows) {
        return Join-Path $BackendDir ".venv\Scripts\python.exe"
    }
    else {
        return Join-Path $BackendDir ".venv/bin/python"
    }
}

$script:BackendPython = Get-BackendPythonPath

function Convert-ToSqliteUrl {
    param([string]$PathValue)
    $normalized = $PathValue -replace '\\', '/'
    return "sqlite+aiosqlite:///$normalized"
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

$script:TestSummary = New-Object System.Collections.Generic.List[psobject]

$TestWorkspace = Join-Path $RepoRoot "scratch/tests"
New-Item -ItemType Directory -Force -Path $TestWorkspace | Out-Null
$TestDbPath = Join-Path $TestWorkspace "selenite.test.db"
$TestMediaPath = Join-Path $TestWorkspace "media"
$TestTranscriptPath = Join-Path $TestWorkspace "transcripts"

$OriginalEnv = @{
    ENVIRONMENT = $env:ENVIRONMENT
    DATABASE_URL = $env:DATABASE_URL
    MEDIA_STORAGE_PATH = $env:MEDIA_STORAGE_PATH
    TRANSCRIPT_STORAGE_PATH = $env:TRANSCRIPT_STORAGE_PATH
}

$env:ENVIRONMENT = "testing"
$env:DATABASE_URL = Convert-ToSqliteUrl $TestDbPath
$env:MEDIA_STORAGE_PATH = $TestMediaPath
$env:TRANSCRIPT_STORAGE_PATH = $TestTranscriptPath
Write-Host "Preparing scratch test workspace at $TestWorkspace..." -ForegroundColor DarkGray
foreach ($path in @($TestDbPath, $TestMediaPath, $TestTranscriptPath)) {
    if (Test-Path $path) {
        Remove-Item $path -Recurse -Force
    }
}
foreach ($dir in @($TestMediaPath, $TestTranscriptPath)) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }
}
Write-Host "Scratch test workspace ready." -ForegroundColor DarkGray

Write-Host "Ensuring SQLite database resides under backend/selenite.db..." -ForegroundColor DarkGray
try {
    $pythonExe = Get-SystemPython
    $sqliteGuard = Join-Path $RepoRoot "scripts/sqlite_guard.py"
    if (Test-Path $sqliteGuard) {
        & $pythonExe $sqliteGuard --repo-root $RepoRoot --enforce | Write-Host
    } else {
        Write-Host "sqlite_guard.py not found; skipping auto-remediation." -ForegroundColor Yellow
    }
} catch {
    Write-Warning "SQLite guard failed: $_"
}
# Fast-fail parity: ensure only backend/selenite.db exists in repo root
$ExpectedDb = Join-Path $BackendDir "selenite.db"
$dbs = Get-ChildItem -Path $RepoRoot -Filter "selenite.db" -Recurse -ErrorAction SilentlyContinue
$rogueDbs = @()
$backupRoot = Join-Path $RepoRoot "storage\\backups"
$scratchRoot = Join-Path $RepoRoot "scratch"
foreach ($db in $dbs) {
    $fullPath = $db.FullName
    $normalizedPath = $fullPath -replace '/', '\\'
    if ($normalizedPath -match "\\storage\\backups\\") {
        continue
    }
    if ($normalizedPath -match "\\scratch\\") {
        continue
    }
    if ($fullPath -ne (Resolve-Path $ExpectedDb).Path) {
        $rogueDbs += $db
    }
}
if ($rogueDbs.Count -gt 0) {
    Write-Host "Detected unexpected SQLite database(s); tests require single DB at $ExpectedDb" -ForegroundColor Red
    foreach ($db in $rogueDbs) { Write-Host " - $($db.FullName)" -ForegroundColor Red }
    throw "Resolve duplicate databases before running tests."
}

function Write-Section {
    param([string]$Message)
    Write-Host "`n=== $Message ===" -ForegroundColor Cyan
}

function Throw-OnError {
    param(
        [string]$Context
    )
    if ($LASTEXITCODE -ne 0) {
        throw "$Context failed (exit code $LASTEXITCODE)"
    }
}

function Stop-PortListener {
    param(
        [int]$Port
    )
    try {
        if ($IsWindows) {
            $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
            foreach ($connection in $connections) {
                $procId = $connection.OwningProcess
                if ($procId) {
                    Write-Host "Stopping process $procId using port $Port..." -ForegroundColor Yellow
                    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
                }
            }
        } else {
            $pids = & bash -lc "lsof -ti tcp:$Port -s tcp:listen 2>/dev/null"
            if ($pids) {
                foreach ($pid in $pids -split "`n") {
                    if ($pid.Trim()) {
                        Write-Host "Stopping process $pid using port $Port..." -ForegroundColor Yellow
                        & bash -lc "kill -9 $pid" | Out-Null
                    }
                }
            }
        }
    } catch {
        Write-Warning "Unable to free port ${Port}: $_"
    }
}

function Add-Summary {
    param(
        [string]$Suite,
        [string]$Status,
        [string]$Details
    )
    $script:TestSummary.Add([pscustomobject]@{
        Suite   = $Suite
        Status  = $Status
        Details = $Details
    })
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
            Throw-OnError "python -m venv .venv"
            $Force = $true
            $script:BackendPython = Get-BackendPythonPath
        }

        if ($Force) {
            Write-Host "Installing backend dependencies..." -ForegroundColor Yellow
            & $script:BackendPython -m pip install --upgrade pip
            Throw-OnError "pip install --upgrade pip"
            & $script:BackendPython -m pip install -r requirements-minimal.txt
            Throw-OnError "pip install -r requirements-minimal.txt"
        } else {
            Write-Host "Backend dependencies already present. Use -ForceBackendInstall to reinstall." -ForegroundColor DarkGray
        }
    }
    finally {
        Pop-Location
    }
}

function ConvertTo-AsciiSafe {
    param([string]$Text)
    return ([regex]'[^\u0000-\u007F]').Replace($Text, '?')
}

function Run-BackendTests {
    Write-Section "Running backend pytest suite"
    $logPath = Join-Path $RunDir "backend.pytest.log"
    Push-Location $BackendDir
    try {
        & $script:BackendPython -m pytest --maxfail=1 --disable-warnings --cov=app --cov-report=term *> $logPath
        $exit = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }
    if ($exit -ne 0) {
        Write-Host "Backend pytest failed. See $logPath for full details." -ForegroundColor Red
        if (Test-Path $logPath) {
            Write-Host "--- Last 40 lines (ASCII-safe) ---" -ForegroundColor Yellow
            $tail = Get-Content $logPath -Tail 40
            foreach ($line in $tail) {
                Write-Host (ConvertTo-AsciiSafe $line)
            }
            Write-Host "---------------------------------" -ForegroundColor Yellow
        }
        throw "pytest failed (exit code $exit)"
    } else {
        Write-Host "Backend pytest output saved to $logPath" -ForegroundColor DarkGray
    }
}

function Run-AlignmentCheck {
    Write-Section "Alignment drift check"
    $checkerPath = Join-Path $RepoRoot "scripts/check_alignment.py"
    if (-not (Test-Path $checkerPath)) {
        Write-Host "Alignment checker script not found; skipping." -ForegroundColor Yellow
        return
    }
    $alignmentDbPath = Join-Path $TestWorkspace "selenite.alignment.db"
    $alignmentDbUrl = Convert-ToSqliteUrl $alignmentDbPath
    $previousDbUrl = $env:DATABASE_URL
    if (Test-Path $alignmentDbPath) {
        Remove-Item $alignmentDbPath -Force
    }
    $env:DATABASE_URL = $alignmentDbUrl
    Push-Location $RepoRoot
    try {
        & $script:BackendPython $checkerPath
        $exit = $LASTEXITCODE
    }
    finally {
        Pop-Location
        $env:DATABASE_URL = $previousDbUrl
    }
    if ($exit -ne 0) {
        throw "Alignment checker reported drift (exit code $exit)"
    }
}

function Ensure-FrontendDeps {
    param([switch]$Force)
    Push-Location $FrontendDir
    try {
        if ($Force -or -not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
            Write-Host "Installing frontend dependencies (npm install)..." -ForegroundColor Yellow
            npm install
            Throw-OnError "npm install"
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
        Throw-OnError "npm run test:coverage"
        npm run coverage:summary
        Throw-OnError "npm run coverage:summary"
    }
    finally {
        Pop-Location
    }
}

function Run-E2E {
    Write-Section "Running Playwright E2E suite"
    Push-Location $FrontendDir
    try {
        foreach ($port in $BackendPort, $FrontendPort) {
            Stop-PortListener -Port $port
        }
        npm run e2e:full
        Throw-OnError "npm run e2e:full"
    }
    finally {
        Pop-Location
    }
}

# --- Main execution ---
$script:StoredError = $null
try {
    if (-not $SkipBackend) {
        try {
            Ensure-BackendEnv -Force:$ForceBackendInstall
            Run-BackendTests
            Run-AlignmentCheck
            Add-Summary -Suite "Backend" -Status "PASS" -Details "pytest --cov=app + alignment"
        } catch {
            Add-Summary -Suite "Backend" -Status "FAIL" -Details $_.Exception.Message
            throw
        }
    } else {
        Write-Host "Skipping backend tests (-SkipBackend set)." -ForegroundColor Yellow
        Add-Summary -Suite "Backend" -Status "SKIPPED" -Details "-SkipBackend flag"
    }

    if (-not $SkipFrontend) {
        try {
            Ensure-FrontendDeps -Force:$ForceFrontendInstall
            Run-FrontendTests
            Add-Summary -Suite "Frontend" -Status "PASS" -Details "npm run test:coverage && npm run coverage:summary"
        } catch {
            Add-Summary -Suite "Frontend" -Status "FAIL" -Details $_.Exception.Message
            throw
        }
    } else {
        Write-Host "Skipping frontend tests (-SkipFrontend set)." -ForegroundColor Yellow
        Add-Summary -Suite "Frontend" -Status "SKIPPED" -Details "-SkipFrontend flag"
    }

    if (-not $SkipE2E) {
        try {
            Run-E2E
            Add-Summary -Suite "E2E" -Status "PASS" -Details "npm run e2e:full"
        } catch {
            Add-Summary -Suite "E2E" -Status "FAIL" -Details $_.Exception.Message
            throw
        }
    } else {
        Write-Host "Skipping Playwright E2E (-SkipE2E set)." -ForegroundColor Yellow
        Add-Summary -Suite "E2E" -Status "SKIPPED" -Details "-SkipE2E flag"
    }

    Write-Section "All requested test suites completed"
}
catch {
    $script:StoredError = $_
}
finally {
    if ($script:TestSummary.Count -gt 0) {
        Write-Section "Composite Test Summary"
        $script:TestSummary | Format-Table -AutoSize
        Write-Host "Artifacts saved to: $RunDir" -ForegroundColor DarkGray
        Write-Host "Full transcript: $TranscriptPath" -ForegroundColor DarkGray
    }
    try { Stop-Transcript | Out-Null } catch {}

    foreach ($key in @("ENVIRONMENT","DATABASE_URL","MEDIA_STORAGE_PATH","TRANSCRIPT_STORAGE_PATH")) {
        if ($OriginalEnv[$key]) {
            Set-Item -Path "Env:$key" -Value $OriginalEnv[$key]
        } else {
            Remove-Item -Path "Env:$key" -ErrorAction SilentlyContinue
        }
    }

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

    Write-Host "Cleaning scratch test workspace..." -ForegroundColor DarkGray
    if (Test-Path $TestDbPath) {
        Remove-Item $TestDbPath -Force
    }
    $alignmentDb = Join-Path $TestWorkspace "selenite.alignment.db"
    if (Test-Path $alignmentDb) {
        Remove-Item $alignmentDb -Force
    }
    foreach ($path in @($TestMediaPath, $TestTranscriptPath)) {
        if (Test-Path $path) {
            Remove-Item $path -Recurse -Force
        }
    }
    Write-Host "Scratch test workspace cleanup complete." -ForegroundColor DarkGray

    Write-Host "Removing transient Playwright artifacts..." -ForegroundColor DarkGray
    $playwrightReportDir = Join-Path $FrontendDir "playwright-report"
    if (Test-Path $playwrightReportDir) {
        Remove-Item $playwrightReportDir -Recurse -Force
    }
    $playwrightResultsDir = Join-Path $FrontendDir "test-results"
    if (Test-Path $playwrightResultsDir) {
        Remove-Item $playwrightResultsDir -Recurse -Force
    }
    Write-Host "Playwright artifact cleanup complete." -ForegroundColor DarkGray
}

if ($script:StoredError) {
    throw $script:StoredError
}

Write-Section "Repository hygiene verification"
$systemPython = Get-SystemPython
& $systemPython (Join-Path $RepoRoot "scripts/check_repo_hygiene.py")
Throw-OnError "Repository hygiene check"

# Stamp the repo so pre-flight checks know tests ran recently
$stampPath = Join-Path $RepoRoot ".last_tests_run"
$timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
Set-Content -Path $stampPath -Value "last_tests_run=$timestamp" -Encoding UTF8
Write-Host "Recorded test run timestamp at $stampPath" -ForegroundColor Green





<#
.SYNOPSIS
  Repository guardrail check.

.DESCRIPTION
  Runs a lightweight set of hygiene checks before commits/PRs:
    1. Flags FastAPI routes without `Depends(get_current_user)` (outside allowlist).
    2. Detects hardcoded credentials/IPs.
    3. Warns when raw `console.log` statements exist without an obvious dev guard.
    4. Reminds the contributor to re-run the unified test harness.

  This script is intentionally fast and dependency-free so it can be run locally,
  in CI, or by any AI agent before making changes.
#>
[CmdletBinding()]
param(
    [switch]$Strict
)

$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
Set-Location $repoRoot

$failures = @()

function Write-Info($msg) { Write-Host "[preflight] $msg" -ForegroundColor Cyan }
function Add-Failure($msg) {
    Write-Host "[FAIL] $msg" -ForegroundColor Red
    $script:failures += $msg
}

Write-Info "Running guardrail checks..."

function Should-ExcludePath {
    param([string]$Path)
    $fragments = @(
        "\node_modules\",
        "\.venv\",
        "\lite-env\",
        "\dist\",
        "\coverage\",
        "\playwright-report\",
        "\test-results\",
        "\docs\memorialization\test-runs\",
        "\storage\",
        "\scratch\"
    )
    foreach ($fragment in $fragments) {
        if ($Path -like "*$fragment*") {
            return $true
        }
    }
    return $false
}

function Get-FilesByExtension {
    param([string[]]$Extensions)
    return Get-ChildItem -Path $repoRoot -Recurse -File -Force |
        Where-Object {
            $Extensions -contains $_.Extension.ToLower() -and
            -not (Should-ExcludePath $_.FullName.Replace('/', '\'))
        }
}

function IsSensitiveAllowlisted {
    param([string]$Path)
    $norm = $Path.Replace('/', '\')
    if ($norm -like "*\tests\*") { return $true }
    $allow = @(
        "\scripts\pre-flight-check.ps1",
        "\test-cors.ps1",
        "\test-network-access.ps1",
        "\scripts\get-auth-token.ps1",
        "\scripts\smoke_test.py"
    )
    foreach ($entry in $allow) {
        if ($norm -like "*$entry") { return $true }
    }
    return $false
}

$script:codeFiles = Get-FilesByExtension -Extensions @('.ps1', '.py', '.ts', '.tsx', '.html')

# 1. Route authentication check
$routeAllowlist = @(
    (Join-Path $repoRoot "backend/app/routes/auth.py"),
    (Join-Path $repoRoot "backend/app/routes/health.py"),
    (Join-Path $repoRoot "backend/app/routes/diagnostics.py") # temporary; still warn if Strict
).ForEach({ $_.Replace('/', '\') })

$routeDir = Join-Path $repoRoot "backend/app/routes"
$routeFiles = Get-ChildItem -Path $routeDir -Filter "*.py" -Recurse
foreach ($file in $routeFiles) {
    $normalizedPath = $file.FullName.Replace('/', '\')
    if ($routeAllowlist -contains $normalizedPath) {
        if ($Strict -and $file.Name -eq "diagnostics.py") {
            Add-Failure "diagnostics route file is still allowlisted; tighten auth or remove."
        }
        continue
    }
    $content = Get-Content $file.FullName -Raw
    $regex = [regex]'@router\.(get|post|put|delete|patch)\([\s\S]*?async def\s+\w+\('
    $matches = $regex.Matches($content)
    foreach ($match in $matches) {
        $start = $match.Index
        $length = [Math]::Min(800, $content.Length - $start)
        $snippet = $content.Substring($start, $length)
        if ($snippet -notmatch 'Depends\s*\(\s*get_current_user\s*\)') {
            Add-Failure "Endpoint missing Depends(get_current_user): $($file.FullName)"
        }
    }
}

# 2. Sensitive literal detection
$sensitivePatterns = @(
    'admin/changeme',
    '192\.168\.\d+\.\d+',
    '0\.0\.0\.0:5173',
    '100\.85\.28\.75',
    'whisperx.*password',
    'Bearer\s+[A-Za-z0-9_-]{10,}'
)

foreach ($pattern in $sensitivePatterns) {
    $hits = Select-String -Path $codeFiles.FullName -Pattern $pattern -ErrorAction SilentlyContinue
    if ($hits) {
        foreach ($hit in $hits) {
            if (IsSensitiveAllowlisted $hit.Path) { continue }
            Add-Failure "Sensitive literal matched ($pattern) in $($hit.Path):$($hit.LineNumber)"
        }
    }
}

# 3. Console logging guard
$frontendFiles = Get-ChildItem -Path (Join-Path $repoRoot "frontend/src") -Recurse -File | Where-Object { $_.Extension -in @('.ts','.tsx') }
$consoleHits = Select-String -Path $frontendFiles.FullName -Pattern "console\.(log|info|warn|error)" -ErrorAction SilentlyContinue
foreach ($hit in $consoleHits) {
    if ($hit.Path -like "*frontend\src\lib\debug.ts") { continue }
    if ($hit.Line -notmatch 'dev(Log|Info|Warn|Error)' -and $hit.Line -notmatch 'debug\.' ) {
        Write-Host "[WARN] console usage without dev guard: $($hit.Path):$($hit.LineNumber)" -ForegroundColor Yellow
        if ($Strict) {
            Add-Failure "console.* without dev guard"
        }
    }
}

# 4. Reminder to run tests
$testStamp = Join-Path $repoRoot ".last_tests_run"
if (-not (Test-Path $testStamp)) {
    Write-Host "[WARN] No .last_tests_run stamp found. Run ./run-tests.ps1 -SkipE2E before committing." -ForegroundColor Yellow
} else {
    $lastRun = Get-Item $testStamp
    Write-Info "Tests last marked as run: $($lastRun.LastWriteTime)"
    if ((Get-Date) - $lastRun.LastWriteTime -gt [TimeSpan]::FromHours(24)) {
        Write-Host "[WARN] .last_tests_run is older than 24 hours; rerun ./run-tests.ps1 before committing." -ForegroundColor Yellow
    }
}

if ($failures.Count -gt 0) {
    Write-Host ""
    Write-Host "Pre-flight check failed with $($failures.Count) issue(s)." -ForegroundColor Red
    exit 1
}

Write-Host "Pre-flight check passed." -ForegroundColor Green
exit 0

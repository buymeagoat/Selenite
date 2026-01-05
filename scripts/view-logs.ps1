<#
.SYNOPSIS
    View Selenite logs with filtering for diagnostic information.

.DESCRIPTION
    Tail and filter Selenite application logs, highlighting client errors,
    API requests, and other diagnostic information.

.PARAMETER Follow
    Continuously follow the log file (like tail -f).

.PARAMETER Lines
    Number of recent lines to show (default: 50).

.PARAMETER Filter
    Filter logs by keyword (e.g., "CLIENT ERROR", "LOGIN", "API").

.PARAMETER ShowAll
    Show all logs without filtering.

.EXAMPLE
    .\view-logs.ps1
    Shows last 50 lines with diagnostic filtering.

.EXAMPLE
    .\view-logs.ps1 -Follow
    Continuously follow logs in real-time.

.EXAMPLE
    .\view-logs.ps1 -Filter "LOGIN" -Lines 100
    Show last 100 lines containing "LOGIN".
#>

param(
    [switch]$Follow,
    [int]$Lines = 50,
    [string]$Filter = "",
    [switch]$ShowAll
)

$guardScript = Join-Path $PSScriptRoot 'workspace-guard.ps1'
if (Test-Path $guardScript) { . $guardScript }






$ErrorActionPreference = "Stop"

$repo = Resolve-Path (Join-Path $PSScriptRoot '..')
$logDir = Join-Path $repo "logs"
$backendLog = Join-Path $repo "backend\logs\selenite.log"

# Prefer backend log, fall back to repo logs
$logPath = $null
if (Test-Path $backendLog) {
    $logPath = $backendLog
} elseif (Test-Path $logDir) {
    $logFiles = Get-ChildItem -Path $logDir -Filter "*.log" | Sort-Object LastWriteTime -Descending
    if ($logFiles) {
        $logPath = $logFiles[0].FullName
    }
}

if (-not $logPath) {
    Write-Host "No log files found in logs/ or backend/logs/" -ForegroundColor Red
    Write-Host "Log directory: $logDir" -ForegroundColor Yellow
    Write-Host "Backend log: $backendLog" -ForegroundColor Yellow
    exit 1
}

Write-Host "Viewing log: $logPath" -ForegroundColor Cyan
Write-Host ""

function Format-LogLine {
    param([string]$Line)
    
    # Highlight different log types
    if ($Line -match "ERROR|CRITICAL") {
        Write-Host $Line -ForegroundColor Red
    } elseif ($Line -match "WARNING|WARN") {
        Write-Host $Line -ForegroundColor Yellow
    } elseif ($Line -match "CLIENT ERROR|CLIENT LOG") {
        Write-Host $Line -ForegroundColor Magenta
    } elseif ($Line -match "LOGIN|AUTH") {
        Write-Host $Line -ForegroundColor Cyan
    } elseif ($Line -match "API REQUEST|API RESPONSE|API ERROR") {
        Write-Host $Line -ForegroundColor Green
    } else {
        Write-Host $Line
    }
}

function Show-Logs {
    param([string[]]$LogLines)
    
    $filteredLines = $LogLines
    
    if (-not $ShowAll -and -not $Filter) {
        # Default: show diagnostic-relevant lines
        $filteredLines = $LogLines | Where-Object {
            $_ -match "ERROR|WARNING|CLIENT|LOGIN|AUTH|API REQUEST|API RESPONSE|API ERROR|CORS"
        }
    } elseif ($Filter) {
        $filteredLines = $LogLines | Where-Object { $_ -match $Filter }
    }
    
    foreach ($line in $filteredLines) {
        Format-LogLine $line
    }
}

if ($Follow) {
    Write-Host "Following logs (Ctrl+C to stop)..." -ForegroundColor Cyan
    Write-Host ""
    
    # Show recent lines first
    $recentLines = Get-Content -Path $logPath -Tail $Lines
    Show-Logs $recentLines
    
    # Then follow new lines
    Get-Content -Path $logPath -Wait -Tail 0 | ForEach-Object {
        if ($ShowAll) {
            Format-LogLine $_
        } elseif ($Filter) {
            if ($_ -match $Filter) {
                Format-LogLine $_
            }
        } elseif ($_ -match "ERROR|WARNING|CLIENT|LOGIN|AUTH|API REQUEST|API RESPONSE|API ERROR|CORS") {
            Format-LogLine $_
        }
    }
} else {
    $logLines = Get-Content -Path $logPath -Tail $Lines
    Show-Logs $logLines
}





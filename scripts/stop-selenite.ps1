<#
.SYNOPSIS
    Stop all Selenite processes (backend uvicorn, frontend vite/node).

.DESCRIPTION
    Matches running processes by command line contents and known ports
    (8100 for backend, 5173 for frontend) and stops them.
#>

$ErrorActionPreference = "Stop"

Write-Host "Stopping Selenite processes..." -ForegroundColor Cyan

# Collect candidate processes by command line (python/node running uvicorn/vite/npm)
$processes = @()
$currentPid = $PID
try {
    $procCim = Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -match 'python|node') -and (
            $_.CommandLine -match 'uvicorn' -or
            $_.CommandLine -match 'app.main:app' -or
            $_.CommandLine -match 'vite' -or
            $_.CommandLine -match 'npm run start:prod'
        )
    }
    if ($procCim) {
        $processes += ($procCim | ForEach-Object { Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue }) | Where-Object { $_ }
    }
} catch {}

# Also include any python/node processes launched from the repo path
try {
    $repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
    $procFromRepo = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match [regex]::Escape($repoRoot) }
    if ($procFromRepo) {
        $processes += ($procFromRepo | ForEach-Object { Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue }) | Where-Object { $_ }
    }
} catch {}

# Deduplicate
$processes = $processes | Sort-Object Id -Unique
# Do not stop the current PowerShell host or the invoker scripts
$processes = $processes | Where-Object {
    $_.Id -ne $currentPid -and ($_.CommandLine -notmatch 'start-selenite\.ps1' -and $_.CommandLine -notmatch 'restart-selenite\.ps1')
}

if (-not $processes -or $processes.Count -eq 0) {
    Write-Host "No Selenite processes found by command line match." -ForegroundColor Yellow
} else {
    Write-Host "Found $($processes.Count) process(es):" -ForegroundColor Yellow
    $processes | Select-Object Id, ProcessName, @{Name='Command';Expression={
        try {
            $cim = Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)" -ErrorAction SilentlyContinue
            $cl = $cim.CommandLine
        } catch { $cl = $_.Path }
        if ($cl -and $cl.Length -gt 80) { $cl.Substring(0,80) + '...' } else { $cl }
    }} | Format-Table -AutoSize

    $processes | ForEach-Object {
        try {
            Write-Host "Stopping PID $($_.Id) ($($_.ProcessName))..." -ForegroundColor Yellow
            Stop-Process -Id $_.Id -Force -ErrorAction Stop
            Write-Host "  Stopped" -ForegroundColor Green
        } catch {
            Write-Host "  Failed: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

Start-Sleep -Seconds 1

# Kill any listeners on known ports (8100 backend, 5173 frontend)
function Stop-PortListeners {
    param([int[]]$Ports)
    foreach ($port in $Ports) {
        $listeners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        foreach ($l in $listeners) {
            try {
                $pid = $l.OwningProcess
                $p = Get-Process -Id $pid -ErrorAction SilentlyContinue
                if ($p) {
                    Write-Host "Stopping listener PID $pid on port $port ($($p.ProcessName))..." -ForegroundColor Yellow
                    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                    Write-Host "  Stopped" -ForegroundColor Green
                } else {
                    Write-Host "Listener on port $port had exited (PID $pid)." -ForegroundColor Yellow
                }
            } catch {}
        }
    }
}

Stop-PortListeners -Ports @(8100, 5173)

Start-Sleep -Seconds 2

# Verify all stopped (by port and by command line)
$remaining = @()
try { $remaining += Get-NetTCPConnection -LocalPort 8100,5173 -State Listen -ErrorAction SilentlyContinue } catch {}
try {
    $remaining += (Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -match 'python|node') -and (
            $_.CommandLine -match 'uvicorn' -or
            $_.CommandLine -match 'app.main:app' -or
            $_.CommandLine -match 'vite' -or
            $_.CommandLine -match 'npm run start:prod'
        )
    })
} catch {}

if ($remaining -and $remaining.Count -gt 0) {
    Write-Host ""
    Write-Host "Warning: Some processes are still running:" -ForegroundColor Red
    try {
        $remaining | ForEach-Object {
            if ($_.ProcessId) {
                $p = Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue
                if ($p) { Write-Host (" - PID {0} ({1})" -f $p.Id, $p.ProcessName) -ForegroundColor Red }
            } elseif ($_.OwningProcess) {
                Write-Host (" - PID {0} (listener on port)" -f $_.OwningProcess) -ForegroundColor Red
            }
        }
    } catch {}
} else {
    Write-Host ""
    Write-Host "All Selenite processes stopped." -ForegroundColor Green
}

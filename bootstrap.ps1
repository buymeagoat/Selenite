<#
    Bootstrap script for Selenite.
    Executes the same steps documented in BOOTSTRAP.md.
    Run from a PowerShell prompt:  .\bootstrap.ps1
#>

param(
    [switch]$SkipPreflight,
    [switch]$Dev,            # Use uvicorn reload; ENVIRONMENT=development
    [switch]$Seed,           # Run app.seed
    [switch]$ForceInstall,   # Force npm install even if node_modules exists
    [switch]$ResetAuth,      # Clear cached auth state (frontend .auth folder)
    [int]$BindPort = 8100,   # Backend port
    [string]$BindIP = "127.0.0.1",  # Bind address for backend/frontend (use 0.0.0.0 or Tailscale IP)
    [string]$ApiBase = ""           # VITE_API_URL; defaults to http://<BindIP>:8100 when empty
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$BackendDir = Join-Path $Root 'backend'
$FrontendDir = Join-Path $Root 'frontend'
$MediaDir = Join-Path $Root 'storage\media'
$TranscriptDir = Join-Path $Root 'storage\transcripts'
$ApiBaseResolved = if ($ApiBase -ne "") { $ApiBase } else { "http://$BindIP`:$BindPort" }
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
        function Get-FreePort {
            $listener = [System.Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, 0)
            $listener.Start()
            $port = $listener.LocalEndpoint.Port
            $listener.Stop()
            return $port
        }
        function Stop-PortListeners {
            param([int[]]$Ports)
            foreach ($port in $Ports) {
                $attempt = 0
                do {
                    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
                    if (-not $conns) { break }
                    $pids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
                    if ($attempt -eq 0) {
                        Write-Host "Found existing listeners on port $port; stopping them (PIDs: $($pids -join ', '))..." -ForegroundColor Yellow
                    }
                    foreach ($targetPid in $pids) {
                        try {
                            # Try taskkill to ensure child processes die too
                            taskkill /PID $targetPid /F /T *> $null 2>&1
                        } catch {}
                        try { Stop-Process -Id $targetPid -Force -ErrorAction SilentlyContinue } catch {}
                    }
                    Start-Sleep -Seconds 1
                    $attempt++
                } while ($attempt -lt 10)
                $remaining = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
                if ($remaining) {
                    Write-Host "Warning: Port $port is still in use after cleanup attempts:" -ForegroundColor Red
                    foreach ($r in $remaining) {
                        try {
                            $p = Get-Process -Id $r.OwningProcess -ErrorAction SilentlyContinue
                            if ($p) {
                                Write-Host (" - PID {0} ({1}) CmdLine: {2}" -f $p.Id, $p.ProcessName, ($p.Path)) -ForegroundColor Red
                            } else {
                                Write-Host (" - PID {0} (process exited)" -f $r.OwningProcess) -ForegroundColor Red
                            }
                        } catch {}
                    }
                    Write-Host "Please kill the above processes or free the port, then rerun bootstrap." -ForegroundColor Red
                }
            }
        }

        # Stop Selenite-related processes by command line (uvicorn/vite/node launched from repo)
        $repoPattern = [regex]::Escape($Root)
        $procQuery = Get-CimInstance Win32_Process | Where-Object {
            ($_."CommandLine" -match "uvicorn" -or $_."CommandLine" -match "vite" -or $_."CommandLine" -match "npm run start:prod" -or $_."CommandLine" -match "python.exe.*app.main" -or $_."CommandLine" -match "vite preview") -and
            ($_.CommandLine -match $repoPattern)
        }
        if ($procQuery) {
            Write-Host "Stopping existing Selenite processes..." -ForegroundColor Yellow
            $procQuery | ForEach-Object {
                try { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } catch {}
            }
        }
        # If port is still in use later, we will kill by port regardless of repo match

        # Kill any process bound to common ports (8100 backend, 5173 frontend)
        Stop-PortListeners -Ports @($BindPort, 5173)

        # If backend port is still busy after cleanup, fall back to a free port to keep boot moving
        $stillBusy = Get-NetTCPConnection -LocalPort $BindPort -State Listen -ErrorAction SilentlyContinue
        if ($stillBusy) {
            Write-Host "Backend port $BindPort is still busy after cleanup; selecting a free port instead." -ForegroundColor Yellow
            $oldPort = $BindPort
            $BindPort = Get-FreePort
            $ApiBaseResolved = if ($ApiBase -ne "") { $ApiBase } else { "http://$BindIP`:$BindPort" }
            Write-Host "Using backend port $BindPort for this run (was $oldPort)." -ForegroundColor Yellow
        }

        # Close any lingering PowerShell windows that were spawned by this bootstrap (title contains Selenite)
        Get-Process | Where-Object { $_.MainWindowTitle -match 'Selenite' -and $_.ProcessName -match 'pwsh|powershell' } | ForEach-Object {
            try { $_.CloseMainWindow() | Out-Null } catch {}
            try { $_.Kill() | Out-Null } catch {}
        }
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
    if ($ResetAuth) {
        $authDir = Join-Path $FrontendDir '.auth'
        if (Test-Path $authDir) {
            Remove-Item -Recurse -Force $authDir -ErrorAction SilentlyContinue
            Write-Host "Cleared frontend cached auth state (.auth folder)." -ForegroundColor Yellow
        }
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
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host $BindIP --port $BindPort --app-dir app $uvicornArgs
"@
    Start-Process -FilePath "pwsh" -ArgumentList "-NoExit", "-Command", $backendCmd
    Write-Host "Backend starting on http://$BindIP`:$BindPort (check new window)." -ForegroundColor Green
}

Invoke-Step "Start frontend production preview (new window)" {
    $frontendCmd = @"
cd "$FrontendDir"
Write-Host ''
Write-Host '  ______     ______     __         ______     __   __     __     ______    ' -ForegroundColor Cyan
Write-Host ' /\  ___\   /\  == \   /\ \       /\  == \   /\ "-.\ \   /\ \   /\  == \   ' -ForegroundColor Cyan
Write-Host ' \ \  __\   \ \  __<   \ \ \____  \ \  __<   \ \ \-.  \  \ \ \  \ \  __<   ' -ForegroundColor Cyan
Write-Host '  \ \_____\  \ \_\ \_\  \ \_____\  \ \_\ \_\  \ \_\"\_\  \ \_\  \ \_\ \_\ ' -ForegroundColor Cyan
Write-Host '   \/_____/   \/_/ /_/   \/_____/   \/_/ /_/   \/_/ \/_/   \/_/   \/_/ /_/ ' -ForegroundColor Cyan
`$env:VITE_API_URL='$ApiBaseResolved'
npm run start:prod -- --host $BindIP --port 5173 --strictPort
"@
    Start-Process -FilePath "pwsh" -ArgumentList "-NoExit", "-Command", $frontendCmd
    Write-Host "Frontend starting on http://$BindIP`:5173 (check new window)." -ForegroundColor Green
}

Invoke-Step "Verify backend via smoke test" {
    Set-Location $Root
    $pythonExe = Join-Path $BackendDir '.venv\Scripts\python.exe'
    $smokeScript = Join-Path $Root 'scripts\smoke_test.py'
    & $pythonExe $smokeScript --base-url http://127.0.0.1:$BindPort --health-timeout 90
}

Write-Section "All done"
Write-Host "Backend and frontend processes have been launched in separate PowerShell windows."
Write-Host "If either window reports an error, resolve it before proceeding." -ForegroundColor Yellow

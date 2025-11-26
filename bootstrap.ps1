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
    [switch]$BackupDb,       # Create a DB backup before migrations/seed
    [int]$BindPort = 8100,   # Backend port
    [string]$BindIP = "0.0.0.0",  # Bind address for backend/frontend (0.0.0.0 listens on all)
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
$BackupDir = Join-Path $Root 'storage\backups'
$ApiBaseResolved = $null
New-Item -ItemType Directory -Force -Path $MediaDir | Out-Null
New-Item -ItemType Directory -Force -Path $TranscriptDir | Out-Null
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

function Get-SystemPython {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        $python = Get-Command python3 -ErrorAction SilentlyContinue
    }
    if (-not $python) {
        throw "Python is required on PATH to run bootstrap."
    }
    return $python.Path
}

function Invoke-SqliteGuard {
    param([string]$RepoRoot)
    $guard = Join-Path $RepoRoot 'scripts\sqlite_guard.py'
    if (-not (Test-Path $guard)) { return }
    try {
        $pythonExe = Get-SystemPython
        & $pythonExe $guard --repo-root $RepoRoot --enforce | Write-Host
    } catch {
        Write-Warning "SQLite guard failed: $_"
    }
}

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

function Get-AdvertiseHost {
    param([string]$BindHost)
    # When binding to all interfaces, pick a concrete IP to advertise for VITE_API_URL.
    $candidates = Get-NetIPAddress -AddressFamily IPv4 -PrefixOrigin Manual, Dhcp -ErrorAction SilentlyContinue | Where-Object {
        $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*'
    }
    if (-not $candidates) { return "http://127.0.0.1`:$BindPort" }
    $ordered = $candidates | Sort-Object -Property @{ Expression = {
            $ip = $_.IPAddress
            if ($_.InterfaceAlias -match 'Tailscale') { return 0 }
            if ($ip -like '10.*' -or $ip -like '192.168.*' -or $ip -like '172.16.*') { return 1 }
            return 2
        } }
    $ipPick = $ordered[0].IPAddress
    return "http://$ipPick`:$BindPort"
}

if (-not $SkipPreflight) {
    Invoke-Step "Pre-flight cleanup" {
        $logRoot = Join-Path $Root 'logs'
        Get-ChildItem -Path $logRoot -Filter *.log -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
            $_.IsReadOnly = $false
        }
        function Test-PortBindable {
            param([string]$BindHost, [int]$Port)
            try {
                $listener = [System.Net.Sockets.TcpListener]::new([Net.IPAddress]::Parse($BindHost), $Port)
                $listener.Start()
                $listener.Stop()
                return $true
            } catch {
                return $false
            }
        }
        function Get-FreePort {
            $listener = [System.Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, 0)
            $listener.Start()
            $port = $listener.LocalEndpoint.Port
            $listener.Stop()
            return $port
        }
        function Backup-Database {
            param([string]$DbPath, [string]$BackupRoot)
            if (-not (Test-Path $DbPath)) { return }
            try {
                $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
                $backupFile = Join-Path $BackupRoot ("selenite-{0}.db" -f $timestamp)
                Copy-Item -Path $DbPath -Destination $backupFile -Force
                Write-Host "Database backup created: $backupFile" -ForegroundColor Yellow
            } catch {
                Write-Host "Warning: failed to create DB backup: $_" -ForegroundColor Red
            }
        }
        function Assert-SingleDatabase {
            param([string]$ExpectedPath)
            $expectedResolved = Resolve-Path -Path $ExpectedPath -ErrorAction SilentlyContinue
            $expectedFull = if ($expectedResolved) { $expectedResolved.Path } else { $ExpectedPath }
            $dbs = Get-ChildItem -Path $Root -Filter "selenite.db" -Recurse -ErrorAction SilentlyContinue
            $rogue = if ($expectedResolved) {
                $dbs | Where-Object { $_.FullName -ne $expectedFull }
            } else {
                $dbs # Any existing DB is unexpected if the authoritative one does not exist yet
            }
            if ($rogue) {
                Write-Host "Multiple selenite.db files detected; expected only $expectedFull" -ForegroundColor Red
                $rogue | ForEach-Object { Write-Host " - Unexpected DB: $($_.FullName)" -ForegroundColor Red }
                throw "Resolve duplicate databases before bootstrapping to avoid credential drift."
            }
            if ($expectedResolved) {
                Write-Host "Database path: $expectedFull" -ForegroundColor DarkGray
            } else {
                Write-Host "Database path not created yet (will be created by migrations): $expectedFull" -ForegroundColor Yellow
            }
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
                    # If no process exists for the remaining listener, treat as zombie and probe bindability
                    $live = $remaining | ForEach-Object { Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue } | Where-Object { $_ }
                    if (-not $live) {
                        if (Test-PortBindable -BindHost $BindIP -Port $port) {
                            Write-Host "Port $port was held by a zombie entry but is now bindable; continuing." -ForegroundColor Yellow
                            continue
                        }
                    }
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

        # If backend port is still busy after cleanup, confirm bindability; if not, fall back to free port
        $stillBusy = Get-NetTCPConnection -LocalPort $BindPort -State Listen -ErrorAction SilentlyContinue
        $canBind = Test-PortBindable -BindHost $BindIP -Port $BindPort
        if ($stillBusy -and -not $canBind) {
            Write-Host "Backend port $BindPort is still busy after cleanup; selecting a free port instead." -ForegroundColor Yellow
            $oldPort = $BindPort
            $BindPort = Get-FreePort
            $ApiBaseResolved = if ($ApiBase -ne "") { $ApiBase } else { "http://$BindIP`:$BindPort" }
            Write-Host "Using backend port $BindPort for this run (was $oldPort)." -ForegroundColor Yellow
        } elseif ($canBind -and $stillBusy) {
            Write-Host "Backend port $BindPort appears bindable despite lingering entries; proceeding." -ForegroundColor Yellow
        }

        # Close any lingering PowerShell windows that were spawned by this bootstrap (title contains Selenite)
        Get-Process | Where-Object { $_.MainWindowTitle -match 'Selenite' -and $_.ProcessName -match 'pwsh|powershell' } | ForEach-Object {
            try { $_.CloseMainWindow() | Out-Null } catch {}
            try { $_.Kill() | Out-Null } catch {}
        }

        Invoke-SqliteGuard -RepoRoot $Root

        # Ensure we only have one authoritative SQLite DB
        $primaryDb = Join-Path $BackendDir 'selenite.db'
        Assert-SingleDatabase -ExpectedPath $primaryDb
    }
}

if ($ApiBase -ne "") {
    $ApiBaseResolved = $ApiBase
} else {
    if ($BindIP -eq "0.0.0.0") {
        $ApiBaseResolved = Get-AdvertiseHost -BindHost $BindIP
        Write-Host "Binding to all interfaces; advertising API as $ApiBaseResolved" -ForegroundColor Yellow
    } else {
        $ApiBaseResolved = "http://$BindIP`:$BindPort"
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

Invoke-Step "Database backup" {
    if ($BackupDb) {
        $dbPath = Join-Path $BackendDir 'selenite.db'
        Backup-Database -DbPath $dbPath -BackupRoot $BackupDir
    } else {
        Write-Host "Skipping DB backup (use -BackupDb to enable)." -ForegroundColor Yellow
    }
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

Invoke-Step "Reset admin credentials (sanity)" {
    # Run in backend directory so SQLite path resolves to backend/selenite.db
    Set-Location $BackendDir
    $resetScript = Join-Path $Root 'scripts\reset_admin_password.py'
    & "$BackendDir\.venv\Scripts\python.exe" $resetScript --username admin --password changeme
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
    & $pythonExe $smokeScript --base-url $ApiBaseResolved --health-timeout 90
}

Write-Section "All done"
Write-Host "Backend and frontend processes have been launched in separate PowerShell windows."
Write-Host "If either window reports an error, resolve it before proceeding." -ForegroundColor Yellow

# Test runner with hard timeout and progress monitoring
param(
    [int]$TimeoutSeconds = 30,
    [string]$Pattern = "",
    [switch]$Verbose
)

$env:PATH = "C:\Program Files\nodejs;" + $env:PATH
Set-Location $PSScriptRoot

Write-Host "Running tests with $TimeoutSeconds second timeout..." -ForegroundColor Cyan
Write-Host "Working directory: $(Get-Location)" -ForegroundColor Gray

# Build test command
$testArgs = if ($Pattern) { 
    @("--", "--run", "--no-coverage", $Pattern)
} else { 
    @("--", "--run", "--no-coverage")
}

Write-Host "Command: npm test $($testArgs -join ' ')" -ForegroundColor Gray
Write-Host ""

# Create job to run tests
$job = Start-Job -ScriptBlock {
    param($workDir, $args)
    Set-Location $workDir
    $env:PATH = "C:\Program Files\nodejs;" + $env:PATH
    npm test @args 2>&1
} -ArgumentList (Get-Location).Path, $testArgs

# Monitor with timeout
$timeout = (Get-Date).AddSeconds($TimeoutSeconds)
$lastOutput = Get-Date

while ((Get-Date) -lt $timeout) {
    $output = Receive-Job $job
    
    if ($output) {
        $output | ForEach-Object { Write-Host $_ }
        $lastOutput = Get-Date
    }
    
    if ($job.State -eq 'Completed') {
        Write-Host "`nTests completed successfully in $([int]((Get-Date) - $timeout.AddSeconds($TimeoutSeconds)).TotalSeconds) seconds" -ForegroundColor Green
        $remaining = Receive-Job $job
        if ($remaining) { $remaining | ForEach-Object { Write-Host $_ } }
        Remove-Job $job
        exit 0
    }
    
    if ($job.State -eq 'Failed') {
        Write-Host "`nTests failed" -ForegroundColor Red
        Receive-Job $job | ForEach-Object { Write-Host $_ }
        Remove-Job $job
        exit 1
    }
    
    Start-Sleep -Milliseconds 200
}

# Timeout reached
Write-Host "`n`nTIMEOUT: Tests exceeded $TimeoutSeconds seconds" -ForegroundColor Red
Write-Host "Last output was $([int]((Get-Date) - $lastOutput).TotalSeconds) seconds ago" -ForegroundColor Yellow

# Get any remaining output
$finalOutput = Receive-Job $job
if ($finalOutput) {
    Write-Host "`nFinal output:" -ForegroundColor Yellow
    $finalOutput | Select-Object -Last 50 | ForEach-Object { Write-Host $_ }
}

# Kill the job
Stop-Job $job -ErrorAction SilentlyContinue
Remove-Job $job -Force -ErrorAction SilentlyContinue

# Kill any hanging node processes
Write-Host "`nKilling hanging Node processes..." -ForegroundColor Yellow
Get-Process -Name "node" -ErrorAction SilentlyContinue | 
    Where-Object { $_.StartTime -gt (Get-Date).AddMinutes(-2) } | 
    ForEach-Object {
        Write-Host "Killing PID $($_.Id): $($_.ProcessName)" -ForegroundColor Gray
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }

Write-Host "`nTest run terminated due to timeout" -ForegroundColor Red
exit 124  # Standard timeout exit code

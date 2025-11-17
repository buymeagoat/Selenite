# Find which test file is causing the hang
$env:PATH = "C:\Program Files\nodejs;" + $env:PATH
Set-Location $PSScriptRoot

Write-Host "Finding hanging test file..." -ForegroundColor Cyan
Write-Host "Testing each file individually with 10 second timeout`n" -ForegroundColor Gray

$testFiles = Get-ChildItem "src/tests/*.test.tsx" | Select-Object -ExpandProperty Name
$results = @()

foreach ($file in $testFiles) {
    Write-Host "Testing $file... " -NoNewline -ForegroundColor Yellow
    
    $job = Start-Job -ScriptBlock {
        param($workDir, $file)
        Set-Location $workDir
        $env:PATH = "C:\Program Files\nodejs;" + $env:PATH
        npm test -- --run --no-coverage "src/tests/$file" 2>&1
    } -ArgumentList (Get-Location).Path, $file
    
    $completed = Wait-Job $job -Timeout 10
    
    if ($completed) {
        $exitCode = Receive-Job $job -ErrorAction SilentlyContinue | Out-Null
        if ($job.State -eq 'Completed') {
            Write-Host "✓ PASS" -ForegroundColor Green
            $results += [PSCustomObject]@{
                File = $file
                Status = "PASS"
                Duration = "< 10s"
            }
        } else {
            Write-Host "✗ FAIL" -ForegroundColor Red
            $results += [PSCustomObject]@{
                File = $file
                Status = "FAIL"
                Duration = "< 10s"
            }
        }
    } else {
        Write-Host "⏱ TIMEOUT (>10s)" -ForegroundColor Magenta
        $results += [PSCustomObject]@{
            File = $file
            Status = "TIMEOUT"
            Duration = "> 10s"
        }
        Stop-Job $job -ErrorAction SilentlyContinue
    }
    
    Remove-Job $job -Force -ErrorAction SilentlyContinue
}

Write-Host "`n=== SUMMARY ===" -ForegroundColor Cyan
$results | Format-Table -AutoSize

$timeouts = $results | Where-Object { $_.Status -eq "TIMEOUT" }
if ($timeouts) {
    Write-Host "`nFiles causing timeout:" -ForegroundColor Red
    $timeouts | ForEach-Object { Write-Host "  - $($_.File)" -ForegroundColor Red }
} else {
    Write-Host "`nNo individual file timeouts detected" -ForegroundColor Green
    Write-Host "The hang may occur when running all tests together" -ForegroundColor Yellow
}

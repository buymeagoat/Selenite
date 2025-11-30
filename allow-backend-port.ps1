<#
.SYNOPSIS
    Add Windows Firewall rule to allow Selenite backend on port 8100.

.DESCRIPTION
    Creates an inbound firewall rule to allow Python/uvicorn backend
    to accept connections from the local network on port 8100.

.NOTES
    Must be run as Administrator.
#>

$ErrorActionPreference = "Stop"

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host ""
    Write-Host "Right-click PowerShell and select 'Run as Administrator', then run:" -ForegroundColor Yellow
    Write-Host "  .\allow-backend-port.ps1" -ForegroundColor Cyan
    exit 1
}

$ruleName = "Selenite Backend (Port 8100)"

# Check if rule already exists
$existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue

if ($existingRule) {
    Write-Host "Firewall rule '$ruleName' already exists." -ForegroundColor Yellow
    Write-Host "Current status: Enabled=$($existingRule.Enabled), Action=$($existingRule.Action)" -ForegroundColor Yellow
    
    $response = Read-Host "Do you want to recreate it? (y/n)"
    if ($response -ne 'y') {
        Write-Host "Keeping existing rule." -ForegroundColor Green
        exit 0
    }
    
    Remove-NetFirewallRule -DisplayName $ruleName
    Write-Host "Removed existing rule." -ForegroundColor Yellow
}

# Create new firewall rule
try {
    New-NetFirewallRule `
        -DisplayName $ruleName `
        -Description "Allow inbound connections to Selenite backend API on port 8100" `
        -Direction Inbound `
        -Protocol TCP `
        -LocalPort 8100 `
        -Action Allow `
        -Profile Private,Domain `
        -Enabled True
    
    Write-Host ""
    Write-Host "✓ Firewall rule created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Backend port 8100 is now allowed through Windows Firewall." -ForegroundColor Green
    Write-Host "You should now be able to access the backend from other devices on your local network." -ForegroundColor Green
    
} catch {
    Write-Host ""
    Write-Host "ERROR: Failed to create firewall rule" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

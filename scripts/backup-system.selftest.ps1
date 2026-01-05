


$guardScript = Join-Path $PSScriptRoot 'workspace-guard.ps1'
if (Test-Path $guardScript) { . $guardScript }





& (Join-Path $PSScriptRoot "backup-system.ps1") -SelfTest





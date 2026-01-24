$guardScript = Join-Path $PSScriptRoot 'workspace-guard.ps1'
if (Test-Path $guardScript) { . $guardScript }

# Selenite QA Gateway - Hook Installation Script
# Automatically installs Git hooks for pre-commit, commit-msg, and pre-push validation

$ErrorActionPreference = "Stop"

Write-Host "?? Installing Selenite QA Gateway hooks..." -ForegroundColor Cyan
Write-Host ""

# Ensure we're in the repository root
$RepoRoot = git rev-parse --show-toplevel 2>$null
if (-not $RepoRoot) {
    Write-Host "? Error: Not in a Git repository" -ForegroundColor Red
    exit 1
}

Set-Location $RepoRoot

# Ensure .git/hooks directory exists
$HooksDir = Join-Path $RepoRoot ".git\hooks"
if (-not (Test-Path $HooksDir)) {
    New-Item -ItemType Directory -Path $HooksDir -Force | Out-Null
}

# Install pre-commit hook
$PreCommitSrc = Join-Path $RepoRoot ".husky\pre-commit"
$PreCommitDst = Join-Path $HooksDir "pre-commit"

if (Test-Path $PreCommitSrc) {
    Copy-Item $PreCommitSrc $PreCommitDst -Force
    Write-Host "? Installed pre-commit hook" -ForegroundColor Green
    Write-Host "    Validates: code formatting, linting, type-checking, unit tests" -ForegroundColor Gray
} else {
    Write-Host "??  Warning: .husky/pre-commit not found" -ForegroundColor Yellow
}

# Install commit-msg hook
$CommitMsgSrc = Join-Path $RepoRoot ".husky\commit-msg"
$CommitMsgDst = Join-Path $HooksDir "commit-msg"

if (Test-Path $CommitMsgSrc) {
    Copy-Item $CommitMsgSrc $CommitMsgDst -Force
    Write-Host "? Installed commit-msg hook" -ForegroundColor Green
    Write-Host "    Enforces: [Component] Description format (min 10 chars)" -ForegroundColor Gray
} else {
    Write-Host "??  Warning: .husky/commit-msg not found" -ForegroundColor Yellow
}

# Install pre-push hook
$PrePushSrc = Join-Path $RepoRoot ".husky\pre-push"
$PrePushDst = Join-Path $HooksDir "pre-push"

if (Test-Path $PrePushSrc) {
    Copy-Item $PrePushSrc $PrePushDst -Force
    Write-Host "? Installed pre-push hook" -ForegroundColor Green
    Write-Host "    Blocks prod pushes unless explicitly acknowledged" -ForegroundColor Gray
} else {
    Write-Host "??  Warning: .husky/pre-push not found" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "?? QA Gateway hooks installed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Test the hooks:" -ForegroundColor Cyan
Write-Host "  git commit --allow-empty -m 'bad'  # Should fail" -ForegroundColor Gray
Write-Host "  git commit --allow-empty -m '[Test] Valid commit message for testing'  # Should pass" -ForegroundColor Gray
Write-Host ""
Write-Host "Emergency bypass (use sparingly):" -ForegroundColor Yellow
Write-Host "  `$env:SKIP_QA='1'; git commit -m '[Component] Message'; Remove-Item Env:SKIP_QA" -ForegroundColor Gray
Write-Host ""

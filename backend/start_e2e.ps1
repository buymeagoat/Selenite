# PowerShell script to seed and start backend for Playwright E2E
Set-Location $PSScriptRoot

if (-Not (Test-Path .venv\Scripts\python.exe)) {
  python -m venv .venv
}
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip > $null
pip install -r requirements.txt > $null

Write-Host "[E2E] Seeding database..."
python -m app.seed_e2e --clear > $null
python -m app.seed_e2e > $null
Write-Host "[E2E] Seed complete. Starting uvicorn..."

# Start uvicorn (no reload for test stability)
python -m uvicorn app.main:app --port 8100 --log-level warning

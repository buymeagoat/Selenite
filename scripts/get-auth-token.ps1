param(
    [string]$Username = "admin",
    [string]$Password,
    [string]$ApiBaseUrl = "http://127.0.0.1:8201",
    [switch]$ShowExample
)

$guardScript = Join-Path $PSScriptRoot 'workspace-guard.ps1'
if (Test-Path $guardScript) { . $guardScript }






if (-not $Password) {
    $Password = Read-Host -AsSecureString "Enter password for $Username" | `
        ConvertFrom-SecureString -AsPlainText
}

if (-not $ApiBaseUrl.EndsWith("/")) {
    $ApiBaseUrl = "$ApiBaseUrl/"
}

$loginUri = "${ApiBaseUrl.TrimEnd('/')}/auth/login"

Write-Host "Requesting token from $loginUri ..." -ForegroundColor Cyan
try {
    $response = Invoke-RestMethod -Method Post -Uri $loginUri -ContentType "application/json" -Body (
        @{ username = $Username; password = $Password } | ConvertTo-Json
    )
} catch {
    Write-Host "Login failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

if (-not $response.access_token) {
    Write-Host "No token returned. Response:" -ForegroundColor Red
    $response | ConvertTo-Json -Depth 4
    exit 1
}

$token = $response.access_token
Write-Host "`nBearer token (copy for API calls):" -ForegroundColor Green
Write-Host $token

if ($ShowExample) {
    $example = @"
Example usage:

`$headers = @{
  Authorization = "Bearer $token"
}
Invoke-RestMethod -Uri "${ApiBaseUrl}system/info" -Headers `$headers

curl -H "Authorization: Bearer $token" ${ApiBaseUrl}system/availability
"@
    Write-Host "`n$example"
}





# Force a full image rebuild and restart (clears Docker layer cache).
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir  = $PSScriptRoot
$chatbotDir = Split-Path -Parent $scriptDir

& "$scriptDir\check_prereqs.ps1"

Push-Location $chatbotDir
try {
    Write-Host "Stopping existing containers..." -ForegroundColor Cyan
    docker-compose down

    Write-Host "Rebuilding images (no cache)..." -ForegroundColor Cyan
    docker-compose build --no-cache

    Write-Host "Starting services..." -ForegroundColor Cyan
    docker-compose up -d

    Write-Host ""
    Write-Host "Rebuild complete. Open http://localhost in your browser." -ForegroundColor Green
} finally {
    Pop-Location
}

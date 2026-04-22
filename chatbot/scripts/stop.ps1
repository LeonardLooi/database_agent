# Stop all running services without removing volumes.
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$chatbotDir = Split-Path -Parent $PSScriptRoot

Push-Location $chatbotDir
try {
    Write-Host "Stopping services..." -ForegroundColor Cyan
    docker-compose down
    Write-Host "Services stopped. Data volumes are preserved." -ForegroundColor Green
} finally {
    Pop-Location
}

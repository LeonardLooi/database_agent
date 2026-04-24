# Stop all running services without removing volumes.
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$chatbotDir = Split-Path -Parent $PSScriptRoot

# Detect compose command (v2 plugin preferred over v1 standalone)
$null = docker compose version 2>&1
if ($LASTEXITCODE -eq 0) {
    function dc { docker compose @args }
} else {
    function dc { docker-compose @args }
}

Push-Location $chatbotDir
try {
    Write-Host "Stopping services..." -ForegroundColor Cyan
    dc down
    Write-Host "Services stopped. Data volumes are preserved." -ForegroundColor Green
} finally {
    Pop-Location
}

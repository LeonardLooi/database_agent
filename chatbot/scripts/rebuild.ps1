# Force a full image rebuild and restart (clears Docker layer cache).
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir  = $PSScriptRoot
$chatbotDir = Split-Path -Parent $scriptDir

& "$scriptDir\check_prereqs.ps1"

# Detect compose command (v2 plugin preferred over v1 standalone)
$null = docker compose version 2>&1
if ($LASTEXITCODE -eq 0) {
    function dc { docker compose @args }
} else {
    function dc { docker-compose @args }
}

Push-Location $chatbotDir
try {
    Write-Host "Stopping existing containers..." -ForegroundColor Cyan
    dc down

    Write-Host "Rebuilding images (no cache)..." -ForegroundColor Cyan
    dc build --no-cache

    Write-Host "Starting services..." -ForegroundColor Cyan
    dc up -d

    Write-Host ""
    Write-Host "Rebuild complete. Open https://localhost in your browser." -ForegroundColor Green
    Write-Host "(Accept the self-signed certificate warning on first visit — expected for local dev.)"
} finally {
    Pop-Location
}

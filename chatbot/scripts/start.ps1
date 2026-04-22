# Start all services (build images if needed).
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir   = $PSScriptRoot
$chatbotDir  = Split-Path -Parent $scriptDir

& "$scriptDir\check_prereqs.ps1"

Push-Location $chatbotDir
try {
    Write-Host "Building and starting services..." -ForegroundColor Cyan
    docker-compose up --build -d
    Write-Host ""
    Write-Host "Stack is up. Open http://localhost in your browser." -ForegroundColor Green
    Write-Host "Logs: docker-compose logs -f"
    Write-Host "Stop: $scriptDir\stop.ps1"
} finally {
    Pop-Location
}

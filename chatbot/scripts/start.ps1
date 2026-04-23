# Start all services. Delegates to build.ps1 for enterprise CA/proxy support.
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir  = $PSScriptRoot
$chatbotDir = Split-Path -Parent $scriptDir

& "$scriptDir\check_prereqs.ps1"

Write-Host "Building and starting services..." -ForegroundColor Cyan
& "$chatbotDir\build.ps1"

Write-Host ""
Write-Host "Stack is up. Open http://localhost in your browser." -ForegroundColor Green
Write-Host "Logs: docker-compose logs -f"
Write-Host "Stop: $scriptDir\stop.ps1"

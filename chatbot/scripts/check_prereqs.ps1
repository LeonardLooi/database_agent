# Verify required tools are installed before starting the stack.
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Test-Command($cmd) {
    return [bool](Get-Command $cmd -ErrorAction SilentlyContinue)
}

$missing = @()

if (-not (Test-Command "docker")) { $missing += "docker" }

# Accept compose v2 plugin (docker compose) OR v1 standalone (docker-compose)
$null = docker compose version 2>&1
$hasComposeV2 = ($LASTEXITCODE -eq 0)
$hasComposeV1 = (Test-Command "docker-compose")

if (-not $hasComposeV2 -and -not $hasComposeV1) {
    $missing += "docker compose (v2) or docker-compose (v1)"
}

if ($missing.Count -gt 0) {
    Write-Error "Missing required tools: $($missing -join ', '). Install Docker Desktop from https://www.docker.com/products/docker-desktop/"
    exit 1
}

try {
    $null = docker info 2>&1
    if ($LASTEXITCODE -ne 0) { throw "docker info returned exit code $LASTEXITCODE" }
} catch {
    Write-Error "Docker daemon is not running. Start Docker Desktop and retry."
    exit 1
}

$chatbotDir = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $chatbotDir ".env"
if (-not (Test-Path $envFile)) {
    Write-Warning ".env not found. Copy env.template to .env and fill in your API keys."
    Write-Warning "  Copy-Item '$chatbotDir\env.template' '$envFile'"
}

if ($hasComposeV2) {
    Write-Host "Using Docker Compose v2 (docker compose)" -ForegroundColor DarkGray
} else {
    Write-Host "Using Docker Compose v1 (docker-compose) — consider upgrading to Docker Desktop 4.x+" -ForegroundColor Yellow
}

Write-Host "Prerequisites OK." -ForegroundColor Green

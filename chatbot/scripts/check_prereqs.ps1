# Verify required tools are installed before starting the stack.
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Test-Command($cmd) {
    return [bool](Get-Command $cmd -ErrorAction SilentlyContinue)
}

$missing = @()

if (-not (Test-Command "docker")) { $missing += "docker" }
if (-not (Test-Command "docker-compose")) { $missing += "docker-compose" }

if ($missing.Count -gt 0) {
    Write-Error "Missing required tools: $($missing -join ', '). Install Docker Desktop from https://www.docker.com/products/docker-desktop/"
    exit 1
}

try {
    docker info | Out-Null
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

Write-Host "Prerequisites OK." -ForegroundColor Green

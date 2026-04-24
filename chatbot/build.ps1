# Build all services and prune dangling images.
#
# Enterprise setup (one-time only):
#   1. Copy-Item enterprise-build.example .env.build
#   2. Fill in HTTP_PROXY / HTTPS_PROXY in .env.build (if your network requires a proxy)
#   3. Drop your corporate CA cert at: certs\corp-ca.crt
#   4. .\build.ps1  — cert and proxy are injected automatically, no further config needed
#      (If execution policy blocks the script: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass)
#
# Non-enterprise: just run .\build.ps1

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Detect compose command (v2 plugin preferred over v1 standalone) ─────────────
$null = docker compose version 2>&1
if ($LASTEXITCODE -eq 0) {
    function dc { docker compose @args }
} else {
    if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
        Write-Error "Neither 'docker compose' nor 'docker-compose' found. Install Docker Desktop."
        exit 1
    }
    function dc { docker-compose @args }
}

# ── Load proxy settings from .env.build ─────────────────────────────────────────
if (Test-Path ".env.build") {
    Write-Host "[build] Loading proxy settings from .env.build"
    Get-Content ".env.build" | ForEach-Object {
        # Skip blank lines and comments
        if ($_ -match "^\s*([^#\s][^=]*)=(.*)$") {
            [System.Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim(), "Process")
        }
    }
}

# ── Auto-detect corporate CA cert ────────────────────────────────────────────────
# Place your cert at certs\corp-ca.crt — no env var wrangling needed.
if (Test-Path "certs\corp-ca.crt") {
    if (-not $env:CORPORATE_CA_CERT) {
        Write-Host "[build] Corporate CA detected at certs\corp-ca.crt — injecting into build"
        $env:CORPORATE_CA_CERT = Get-Content "certs\corp-ca.crt" -Raw
    }
} else {
    Write-Host "[build] No corporate CA found at certs\corp-ca.crt — skipping (non-enterprise build)"
}

# ── Build ─────────────────────────────────────────────────────────────────────────
Push-Location $PSScriptRoot
try {
    dc up --build -d
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "[build] Pruning dangling images from previous build..."
    docker image prune -f
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "[build] Done."
} finally {
    Pop-Location
}

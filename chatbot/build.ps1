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

# ── Load proxy settings from .env.build ────────────────────────────────────────
if (Test-Path ".env.build") {
    Write-Host "[build] Loading proxy settings from .env.build"
    Get-Content ".env.build" | ForEach-Object {
        # Skip blank lines and comments
        if ($_ -match "^\s*([^#\s][^=]*)=(.*)$") {
            [System.Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim(), "Process")
        }
    }
}

# ── Auto-detect corporate CA cert ──────────────────────────────────────────────
# Place your cert at certs\corp-ca.crt — no env var wrangling needed.
if (Test-Path "certs\corp-ca.crt") {
    if (-not $env:CORPORATE_CA_CERT) {
        Write-Host "[build] Corporate CA detected at certs\corp-ca.crt — injecting into build"
        $env:CORPORATE_CA_CERT = Get-Content "certs\corp-ca.crt" -Raw
    }
} else {
    Write-Host "[build] No corporate CA found at certs\corp-ca.crt — skipping (non-enterprise build)"
}

# ── Build ───────────────────────────────────────────────────────────────────────
docker-compose up --build -d
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[build] Pruning dangling images from previous build..."
docker image prune -f
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[build] Done."

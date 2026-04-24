# Build all services and prune dangling images.
#
# Enterprise setup (one-time only):
#   1. Copy-Item enterprise-build.example .env.build
#   2. Fill in HTTP_PROXY / HTTPS_PROXY in .env.build (if your network requires a proxy)
#   3. Drop your corporate CA cert at: certs\corp-ca.crt
#   4. .\build.ps1  -- cert and proxy are injected automatically, no further config needed
#      (If execution policy blocks the script: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass)
#
# Non-enterprise: just run .\build.ps1

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# -- Detect compose command (v2 plugin preferred over v1 standalone) -------------
docker compose version 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) {
    function dc { docker compose @args }
} else {
    if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
        Write-Error "Neither 'docker compose' nor 'docker-compose' found. Install Docker Desktop."
        exit 1
    }
    function dc { docker-compose @args }
}

# -- Load proxy settings from .env.build -----------------------------------------
if (Test-Path ".env.build") {
    Write-Host "[build] Loading proxy settings from .env.build"
    Get-Content ".env.build" | ForEach-Object {
        if ($_ -match "^\s*([^#\s][^=]*)=(.*)$") {
            [System.Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim(), "Process")
        }
    }
}

# -- Pre-copy corporate CA cert into each build context --------------------------
# Avoids Windows environment variable and command-line length limits that occur
# when cert content is passed as a build arg string.
# Each Dockerfile uses COPY corp-ca.crt directly -- no ARG injection needed.
$buildContexts = @("backend", "frontend", "nginx")
$certSrc = Join-Path $PSScriptRoot "certs\corp-ca.crt"
$hasCert = Test-Path $certSrc

foreach ($ctx in $buildContexts) {
    $dest = Join-Path $PSScriptRoot "$ctx\corp-ca.crt"
    if ($hasCert) {
        Copy-Item $certSrc $dest -Force
    } else {
        # Empty placeholder -- Dockerfile checks file size before installing
        New-Item -Path $dest -ItemType File -Force | Out-Null
    }
}

if ($hasCert) {
    Write-Host "[build] Corporate CA detected at certs\corp-ca.crt -- copied into build contexts"
} else {
    Write-Host "[build] No corporate CA found at certs\corp-ca.crt -- skipping (non-enterprise build)"
}

# -- Build -------------------------------------------------------------------------
Push-Location $PSScriptRoot
try {
    dc up --build -d
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "[build] Pruning dangling images from previous build..."
    docker image prune -f
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "[build] Done."
} finally {
    # Always clean up cert copies -- they must not persist in source directories
    foreach ($ctx in $buildContexts) {
        $dest = Join-Path $PSScriptRoot "$ctx\corp-ca.crt"
        if (Test-Path $dest) { Remove-Item $dest -Force }
    }
    Pop-Location
}

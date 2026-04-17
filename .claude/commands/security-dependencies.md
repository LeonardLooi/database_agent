---
description: Multi-ecosystem dependency vulnerability scanner with SBOM generation and risk-weighted prioritization. Scans npm (NestJS/Angular), pip (Python), Maven (Java), pub.dev (Flutter). Outputs CycloneDX SBOM and prioritized CVE list.
allowed-tools: Bash, Read, Glob, Grep
disable-model-invocation: true
---

# Dependency Vulnerability Scanner

Scan project dependencies across multiple ecosystems to identify vulnerabilities, generate an SBOM, and provide risk-weighted prioritization.

## Arguments

$ARGUMENTS

## Instructions

### Step 1: Determine scan path and detect ecosystems

```bash
SCAN_PATH="${1:-.}"
echo "========================================="
echo "DEPENDENCY VULNERABILITY SCAN"
echo "========================================="
echo "Scanning: $SCAN_PATH"
echo ""

echo "--- Ecosystem Detection ---"
HAS_NPM=false
HAS_PIP=false
HAS_MAVEN=false
HAS_PUB=false

[ -f "$SCAN_PATH/package.json" ] && HAS_NPM=true && echo "  npm ecosystem detected (package.json)"
[ -f "$SCAN_PATH/pyproject.toml" ] || [ -f "$SCAN_PATH/requirements.txt" ] && HAS_PIP=true && echo "  pip ecosystem detected"
[ -f "$SCAN_PATH/pom.xml" ] && HAS_MAVEN=true && echo "  Maven ecosystem detected (pom.xml)"
[ -f "$SCAN_PATH/pubspec.yaml" ] && HAS_PUB=true && echo "  pub.dev ecosystem detected (pubspec.yaml)"

if [ "$HAS_NPM" = false ] && [ "$HAS_PIP" = false ] && [ "$HAS_MAVEN" = false ] && [ "$HAS_PUB" = false ]; then
  echo "  No supported ecosystems detected. Supported: npm, pip, Maven, pub.dev"
  echo "  Ensure $SCAN_PATH contains package.json, pyproject.toml, requirements.txt, pom.xml, or pubspec.yaml."
  exit 1
fi
echo ""
```

### Step 2: Run ecosystem-specific scanners

#### npm (NestJS / Angular)

```bash
if [ "$HAS_NPM" = true ]; then
  echo "--- npm Audit ---"
  cd "$SCAN_PATH"

  if ! command -v npm &>/dev/null; then
    echo "  [SKIP] npm not found. Install Node.js: https://nodejs.org/"
  else
    if command -v jq &>/dev/null; then
      npm audit --json 2>/dev/null | jq '.vulnerabilities | to_entries[] | {name: .key, severity: .value.severity, cvss: .value.cvss.score, fixAvailable: .value.fixAvailable}' 2>/dev/null || echo "  No vulnerabilities found or npm audit not available."
    else
      npm audit 2>/dev/null | grep -E "CRITICAL|HIGH|MODERATE|LOW" || echo "  No vulnerabilities found or npm audit not available."
      echo "  [NOTE] Install jq for structured JSON output: https://jqlang.github.io/jq/"
    fi
  fi
  echo ""
fi
```

#### pip (Python)

```bash
if [ "$HAS_PIP" = true ]; then
  echo "--- pip Audit ---"
  cd "$SCAN_PATH"

  if command -v pip-audit &>/dev/null; then
    pip-audit --format=json --desc 2>/dev/null || echo "  pip-audit scan completed with errors."
  elif command -v safety &>/dev/null; then
    safety check --json 2>/dev/null || echo "  safety check completed with errors."
  else
    echo "  [SKIP] Neither pip-audit nor safety found."
    echo "  Install: pip install pip-audit"
    echo "  Or:      pip install safety"
    if command -v pip &>/dev/null; then
      echo "  Falling back to outdated package check:"
      pip list --outdated 2>/dev/null || echo "  Could not list outdated packages."
    fi
  fi
  echo ""
fi
```

#### Maven (Java)

```bash
if [ "$HAS_MAVEN" = true ]; then
  echo "--- Maven Dependency Check ---"
  cd "$SCAN_PATH"

  if ! command -v mvn &>/dev/null; then
    echo "  [SKIP] mvn not found. Install Maven: https://maven.apache.org/install.html"
  else
    mvn org.owasp:dependency-check-maven:check -DfailBuildOnCVSS=0 -Dformat=JSON 2>/dev/null
    if [ -f "target/dependency-check-report.json" ]; then
      echo "  Report written to: target/dependency-check-report.json"
      if command -v jq &>/dev/null; then
        jq '.dependencies[]? | select(.vulnerabilities != null) | {fileName, vulnerabilities: [.vulnerabilities[]? | {name, severity, cvssv3: .cvssv3?.baseScore}]}' target/dependency-check-report.json 2>/dev/null
      fi
    else
      echo "  [NOTE] OWASP dependency-check plugin may not be configured."
      echo "  Add to pom.xml or run: mvn org.owasp:dependency-check-maven:check"
    fi
  fi
  echo ""
fi
```

#### pub.dev (Flutter / Dart)

```bash
if [ "$HAS_PUB" = true ]; then
  echo "--- pub.dev Audit ---"
  cd "$SCAN_PATH"

  if command -v flutter &>/dev/null; then
    flutter pub audit 2>/dev/null || echo "  flutter pub audit not available (requires Flutter 3.10+)."
  elif command -v dart &>/dev/null; then
    dart pub outdated --json 2>/dev/null || echo "  dart pub outdated failed."
  else
    echo "  [SKIP] Neither flutter nor dart CLI found."
    echo "  Install Flutter: https://docs.flutter.dev/get-started/install"
  fi
  echo ""
fi
```

### Step 3: Calculate priority scores

For each CVE found, calculate a priority score:

```
priority_score = (cvss * 0.4) + (exploitability_score * 2.0) + (fix_available ? 1.0 : 0.0)
```

Where:
- `cvss`: CVSS base score (0.0-10.0)
- `exploitability_score`: CVSS exploitability sub-score (default 2.0 if not available)
- `fix_available`: 1.0 if a patched version exists, 0.0 otherwise

Sort all findings by priority_score descending.

### Step 4: Generate CycloneDX SBOM summary

For each detected dependency, output the PURL (Package URL) format:

```
pkg:{ecosystem}/{package}@{version}
```

Examples:
- `pkg:npm/express@4.18.2`
- `pkg:pypi/fastapi@0.135.2`
- `pkg:maven/org.springframework.boot/spring-boot-starter@3.5.0`
- `pkg:pub/flutter@3.38.0`

### Step 5: Produce final report

```
DEPENDENCY VULNERABILITY SCAN
==============================
Scanned: [path]
Ecosystems: [list of detected ecosystems]
Total vulnerabilities: [count]

IMMEDIATE ACTION REQUIRED (CVSS 9.0+):
  Priority | Package        | CVE           | CVSS | Fix Available | Fix Version
  -------- | -------------- | ------------- | ---- | ------------- | -----------
  [sorted by priority_score desc]

SHORT-TERM (CVSS 7.0-8.9):
  Priority | Package        | CVE           | CVSS | Fix Available | Fix Version
  -------- | -------------- | ------------- | ---- | ------------- | -----------
  [sorted by priority_score desc]

MONITOR (CVSS < 7.0):
  [count] lower-severity findings -- run with --all to see full list

SBOM SUMMARY (CycloneDX PURL format):
  [list of pkg:... PURLs for all dependencies]

NEXT STEPS:
  [ ] Update packages with available patches for CVSS 9+ immediately
  [ ] Review short-term findings in next sprint planning
  [ ] Run /security-hardening for comprehensive remediation
```

---
description: Static Application Security Testing across the full stack. Runs Bandit (Python), Semgrep (multi-language), ESLint Security (TypeScript/Angular), dart analyze (Flutter), SpotBugs (Java). Generates SARIF report with risk score 0-100.
allowed-tools: Bash, Read, Glob, Grep
disable-model-invocation: true
---

# SAST Security Scan

Run static application security testing on the specified path.

## Scan Path

Scan `$ARGUMENTS` if provided, otherwise scan the current directory.

```bash
SCAN_PATH="${ARGUMENTS:-.}"
```

## Step 1: Language Detection

Detect which ecosystems are present in the scan path:

```bash
[ -f pom.xml ] && echo "Java/Spring detected"
[ -f package.json ] && echo "TypeScript/Node detected"
[ -f pyproject.toml ] || [ -f requirements.txt ] && echo "Python detected"
[ -f pubspec.yaml ] && echo "Dart/Flutter detected"
```

## Step 2: Run Language-Specific Scanners

### Java (if pom.xml found)

```bash
mvn verify -Pspotbugs -DskipTests 2>&1 | grep -E "BUG|WARNING|ERROR"
semgrep --config=p/java --json ${SCAN_PATH} 2>/dev/null
```

### TypeScript/NestJS/Angular (if package.json found)

```bash
npx eslint --plugin security --ext .ts ${SCAN_PATH} 2>&1 | grep -E "error|warning" | head -50
semgrep --config=p/typescript --json ${SCAN_PATH} 2>/dev/null
```

### Python (if pyproject.toml or requirements.txt found)

```bash
bandit -r ${SCAN_PATH} -f json -ll 2>/dev/null
semgrep --config=p/python --json ${SCAN_PATH} 2>/dev/null
```

### Dart/Flutter (if pubspec.yaml found)

```bash
dart analyze ${SCAN_PATH} 2>&1
flutter analyze ${SCAN_PATH} 2>&1 | grep -E "error|warning|info"
```

### All Languages (if .semgrep.yml exists)

```bash
semgrep --config=.semgrep.yml --json ${SCAN_PATH} 2>/dev/null
```

## Step 3: Risk Score Calculation

```
Risk Score = min(100, sum of:
  CRITICAL findings x 10
  HIGH findings x 7
  MEDIUM findings x 4
  LOW findings x 1
)
```

## Step 4: Output

```
SAST SCAN RESULTS
=================
Path: [scanned path]
Languages: [detected languages]
Risk Score: [0-100]

CRITICAL ([count]):
  - [file:line] [finding description] [CWE]

HIGH ([count]):
  - [file:line] [finding description] [CWE]

MEDIUM ([count]):
  - [file:line] [finding description] [CWE]

LOW ([count]):
  - [finding description]

NEXT STEPS:
  [ ] Fix all CRITICAL findings before merge
  [ ] Review HIGH findings — fix or document accepted risk
  [ ] Run /security-hardening for comprehensive remediation
```

$ARGUMENTS

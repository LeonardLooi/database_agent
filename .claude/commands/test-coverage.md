# /test-coverage — Multi-Stack Test Coverage Report

Detect which stacks are present and run coverage for each. Lists files below 80% threshold sorted worst-first.

**Minimum threshold: 80% coverage. 100% required for auth, crypto, payment logic.**

## Stack Detection + Coverage Commands

### Spring Boot (Java 21 / Maven)
Detected by: `pom.xml` containing `spring-boot`

```bash
./mvnw test jacoco:report -q
# Report: target/site/jacoco/index.html
# Console summary:
./mvnw jacoco:report -q && cat target/site/jacoco/jacoco.csv | \
  awk -F',' 'NR>1 {missed=$4+$6; total=missed+$5+$7; if(total>0) pct=int((total-missed)*100/total); else pct=0; print pct"% "$2"/"$3}' | \
  sort -n | head -20
```

### Python / FastAPI (Python 3.14)
Detected by: `pyproject.toml` or `requirements.txt` containing `fastapi`

```bash
pytest --cov=src --cov-report=term-missing --cov-fail-under=80 -q 2>&1 | \
  grep -E "(FAIL|PASS|ERROR|%)" | head -30
# Files below threshold:
pytest --cov=src --cov-report=term-missing -q 2>&1 | \
  awk '/^TOTAL/{next} /[0-9]+%/{if(int($4)<80) print $4" "$1}' | sort -n
```

### NestJS (Node.js / TypeScript)
Detected by: `package.json` containing `@nestjs/core`

```bash
npm run test:cov -- --silent 2>&1 | tail -40
# Files below threshold (vitest):
npm run test:cov -- --silent 2>&1 | \
  awk '/^\|/{gsub(/\|/,""); if($2+0 < 80) print $2"% "$1}' | sort -n
```

### Flutter (Dart 3.10.9)
Detected by: `pubspec.yaml` containing `flutter:`

```bash
flutter test --coverage -q 2>&1 | tail -20
# Generate LCOV report:
genhtml coverage/lcov.info -o coverage/html --quiet
# Files below threshold:
lcov --summary coverage/lcov.info 2>&1 | grep -E "lines|functions"
```

## Output Format

```
## Test Coverage Report — {date}

### Spring Boot API
✅ Overall: 84% (threshold: 80%)

Files below 80%:
| File | Coverage | Missing Lines |
|------|----------|---------------|
| UserService.java | 67% | 45-52, 78-80 |
| AuthFilter.java  | 71% | 12-15 |

### Python API
❌ Overall: 71% (threshold: 80%) — BELOW THRESHOLD

Files below 80% (sorted worst-first):
| File | Coverage | Missing Lines |
|------|----------|---------------|
| payment_service.py | 45% | 23-67, 89-102 |
| user_repository.py | 62% | 34-45 |

### NestJS API
✅ Overall: 88% (threshold: 80%)
(No files below threshold)

### Flutter App
✅ Overall: 82% (threshold: 80%)

## Summary
- Stacks checked: 4
- Passing (≥80%): 3
- Failing (<80%): 1 (Python API)
- Critical files below 100%: [list any auth/crypto/payment files not at 100%]

## Suggested Next Steps
Generate missing tests for worst-coverage files:
1. payment_service.py (45%) — add tests for lines 23-67 (payment processing logic)
2. user_repository.py (62%) — add tests for lines 34-45 (error paths)
```

## Rules

- Run ALL detected stacks — do not skip
- 80% is the minimum; auth/crypto/payment code requires 100%
- Sort worst-coverage files first — highest ROI to fix
- Do NOT auto-generate tests — report only, human decides
- If a stack build fails before coverage runs, report: "STACK BUILD FAILED — fix build errors first"
- If no test infrastructure detected for a stack, report: "No test runner detected — run `/scaffold-{stack}` to set up testing"

## Related

- `/tdd` — test-first implementation when coverage is below threshold
- Agent: `.claude/agents/tdd-guide.md` — Red-Green-Refactor enforcement

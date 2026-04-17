# /verify — Binary Build + Test Verification

Runs the fastest possible verification for changed stacks. Returns binary PASS/FAIL with counts.

## Modes

### `/verify` (default: quick)
Compile + lint only. No test execution. Fastest feedback.

### `/verify full`
Compile + lint + all tests. Full confidence.

### `/verify pre-commit`
Quick verify + check for TODO/FIXME/console.log in staged files.

### `/verify pre-pr`
Full verify + security scan + coverage check.

## Stack Detection + Commands

Detected by file presence in current directory tree:

### Spring Boot (`pom.xml` with spring-boot)
```bash
# quick
./mvnw compile -q 2>&1; echo "EXIT:$?"

# full
./mvnw test -q 2>&1 | tail -5; echo "EXIT:$?"

# pre-pr additions
./mvnw dependency-check:check -q 2>&1 | grep -E "(CRITICAL|HIGH)"
```

### Python (`pyproject.toml` or `requirements.txt`)
```bash
# quick
python -m py_compile $(find src -name "*.py") && ruff check src/ -q
echo "EXIT:$?"

# full
pytest -q 2>&1 | tail -5; echo "EXIT:$?"

# pre-pr additions
bandit -r src/ -ll -q
```

### NestJS (`package.json` with @nestjs/core)
```bash
# quick
npm run build -- --silent 2>&1 | tail -5; echo "EXIT:$?"

# full
npm run test -- --silent 2>&1 | tail -5; echo "EXIT:$?"

# pre-pr additions
npm audit --audit-level=high
```

### Angular (`angular.json`)
```bash
# quick
npm run build -- --configuration=production --silent 2>&1 | tail -5; echo "EXIT:$?"

# full
npm test -- --watch=false --browsers=ChromeHeadless 2>&1 | tail -5; echo "EXIT:$?"
```

### Flutter (`pubspec.yaml` with flutter:)
```bash
# quick
flutter analyze --no-pub -q 2>&1 | tail -5; echo "EXIT:$?"

# full
flutter test -q 2>&1 | tail -5; echo "EXIT:$?"
```

## Output Format

```
## Verification — {mode} — {date}

| Stack | Compile | Tests | Status |
|-------|---------|-------|--------|
| Spring Boot | ✅ EXIT 0 | ✅ 47 passed | PASS |
| Python | ✅ EXIT 0 | ❌ 2 failed | FAIL |
| NestJS | ✅ EXIT 0 | ✅ 83 passed | PASS |
| Flutter | ✅ EXIT 0 | ✅ 31 passed | PASS |

### FAIL Details
Python — 2 failures:
- test_create_user_duplicate: AssertionError at tests/test_user.py:45
- test_payment_timeout: TimeoutError at tests/test_payment.py:78

## Final Verdict: ❌ FAIL (1 of 4 stacks failing)
```

**Binary rule:** If ANY stack fails → overall verdict is FAIL. No partial credit.

## pre-commit Checks

```bash
# Check staged files for forbidden patterns
git diff --cached --name-only | xargs grep -n "TODO\|FIXME\|console\.log\|print(" 2>/dev/null
```

If any matches: list them. These are not blocking (human decides) but must be acknowledged.

## Rules

- Run ALL detected stacks — never skip a stack silently
- Report exact exit codes — not "it looks like it passed"
- If a stack build tool is missing (`mvnw`, `flutter`, etc.) → report "BUILD TOOL NOT FOUND — install X"
- Do NOT interpret test failure messages — show raw output, human diagnoses

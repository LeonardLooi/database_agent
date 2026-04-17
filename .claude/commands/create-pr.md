---
description: Create a PR with embedded risk score, conventional title, and context-aware checklist. Analyzes the diff to calculate risk (size, complexity, test coverage, dependencies, security) and generates the gh pr create command. Usage: /create-pr [optional: target branch, defaults to develop]
allowed-tools: Bash, Read, Glob, Grep
---

# Create PR

Generate a pull request with embedded risk assessment.

## Step 1 — Determine diff scope

```bash
# Current branch
git rev-parse --abbrev-ref HEAD

# Target branch: use $ARGUMENTS if provided, otherwise develop
TARGET=${ARGUMENTS:-develop}

# Verify target exists; fall back to main if develop doesn't exist
git show-ref --verify --quiet refs/heads/$TARGET || TARGET=main

# Commit range
git log --oneline $TARGET..HEAD
```

## Step 2 — Run risk assessment

Gather raw data:

```bash
git diff --shortstat $TARGET..HEAD
git diff --name-status $TARGET..HEAD
git diff --name-only $TARGET..HEAD | grep -E "package\.json$|package-lock\.json|pnpm-lock\.yaml|yarn\.lock|requirements\.txt|uv\.lock|Pipfile\.lock|pom\.xml|build\.gradle|pubspec\.yaml|pubspec\.lock"
git diff --name-only $TARGET..HEAD | grep -iE "auth|login|token|jwt|crypto|secret|password|credential|permission|role|guard|interceptor|middleware|\.env|config/.*\.(yml|yaml|json)"
git diff $TARGET..HEAD
```

Apply the exact same scoring logic as `/pr-risk` — 5 dimensions, 0–10 each:

### A. Size Risk
Use the higher of file-count score and line-count score.

| Score | Files changed | OR total lines changed |
|-------|--------------|----------------------|
| 0–2   | ≤ 5          | ≤ 100                |
| 3–4   | ≤ 10         | ≤ 300                |
| 5–6   | ≤ 20         | ≤ 600                |
| 7–8   | ≤ 40         | ≤ 1,000              |
| 9–10  | > 40         | > 1,000              |

### B. Complexity Risk
Start at 0, add points per signal found in the diff (cap at 10):

| Signal in diff | Points |
|----------------|--------|
| Public interface or API contract changed | +2 |
| Database schema or migration file added or modified | +3 |
| Auth, security, permission, or role logic changed | +3 |
| Async or concurrent code added or modified | +2 |
| New third-party integration added | +2 |
| CI/CD, Docker, or infrastructure config changed | +1 |
| Cross-cutting concern modified (logging, error handler, event bus, interceptor) | +1 |

### C. Test Coverage Risk
```
test_ratio = test_files_changed / max(source_files_changed, 1)
```
Source files: `.ts`, `.java`, `.py`, `.dart`, `.kt`, `.swift`, `.js` (excluding test files).
Test files: paths containing `test`, `spec`, `__tests__`, `_test.`, `.test.`, `.spec.`

| Score | test_ratio |
|-------|-----------|
| 0–1   | ≥ 1.0     |
| 2–3   | 0.5–0.99  |
| 4–5   | 0.2–0.49  |
| 6–7   | 0.01–0.19 |
| 8–10  | 0 (no test files changed despite source changes) |

If no source files changed (docs-only, config-only): score = 0.

### D. Dependency Risk

| Score | Criteria |
|-------|----------|
| 0     | No dependency files changed |
| 2     | Lock file changed only |
| 4     | Package manifest changed — patch or minor bumps only |
| 6     | New direct dependency added |
| 8     | Major version bump OR dependency removed |
| 10    | Unverified source, fork, or git-URL dependency |

### E. Security Risk
Start at 0, add points per signal (cap at 10):

| Signal | Points |
|--------|--------|
| Auth / login / session / token handling changed | +3 |
| JWT, OAuth, or credential logic changed | +3 |
| Input validation or sanitization changed | +2 |
| SQL query construction changed | +2 |
| New public endpoint or new response field exposed | +1 |
| Environment variable or secrets config changed | +2 |
| CORS, rate-limiting, or firewall rules changed | +2 |

### Overall Score
```
overall = (size + complexity + test_coverage + dependency + security) / 5
```

| Overall | Level | Required action |
|---------|-------|----------------|
| < 3.0   | 🟢 Low      | Standard review, one approver |
| 3.0–5.9 | 🟡 Medium   | Thorough review recommended |
| 6.0–7.9 | 🟠 High     | Two reviewers + test evidence required |
| ≥ 8.0   | 🔴 Critical | Tech lead sign-off before merge |

## Step 3 — Generate PR title

```bash
git log --oneline $TARGET..HEAD
```

Analyze the commits and pick the type that best represents the aggregate change:

| Type | When to use |
|------|-------------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `refactor` | Code restructuring without behavior change |
| `perf` | Performance improvement |
| `test` | Adding or updating tests |
| `chore` | Tooling, config, dependency updates |

Format: `type(scope): description` — 70 characters max, imperative mood, lowercase after colon.

Examples:
- `feat(auth): add JWT refresh token rotation`
- `fix(api): handle null response from payment gateway`
- `refactor(orders): extract order validation into service`

## Step 4 — Generate PR description

Construct the PR body using the template below, substituting the actual values calculated in Steps 2 and 3.

## PR Description Template

```markdown
## Summary
- [2-4 bullet points describing what changed and why — derived from commit messages and diff]

## Risk Assessment
**Overall Risk**: [🟢 Low / 🟡 Medium / 🟠 High / 🔴 Critical] ([X.X] / 10)

| Factor | Score | Key Signal |
|--------|-------|------------|
| Size | X/10 | N files, N lines |
| Complexity | X/10 | [what drove the score] |
| Test Coverage | X/10 | ratio X.XX |
| Dependencies | X/10 | [what changed] |
| Security | X/10 | [what changed] |

[Include only if 🔴 Critical]: ⛔ **Requires tech lead sign-off before merge**
[Include only if 🟠 High]: ⚠️ **Two reviewers + test evidence required**

## Test Plan
- [ ] [Specific thing to test based on what changed]
- [ ] [Edge case to verify based on what changed]

## Pre-Merge Checklist

<!-- Always included -->
- [ ] Self-review done — read the full diff as if it's someone else's code
- [ ] No debug statements (`console.log`, `print`, `System.out.println`, `debugPrint`)
- [ ] No hardcoded credentials, API keys, or tokens
- [ ] CI is green

<!-- Include if source files changed -->
- [ ] No functions > 50 lines introduced
- [ ] All catch blocks log the error and rethrow or return error state

<!-- Include if test_ratio < 0.5 or no test files changed -->
- [ ] New logic has at least one test for the happy path
- [ ] At least one error condition is tested

<!-- Include if auth / security files changed -->
- [ ] No SQL string concatenation (parameterized queries only)
- [ ] Input validated at system boundary
- [ ] New routes/endpoints have authorization checks
- [ ] No sensitive data written to logs

<!-- Include if dependency files changed -->
- [ ] New package has active maintenance
- [ ] No known CVEs: run `npm audit` / `pip-audit` / `flutter pub audit`
- [ ] License is compatible with project

<!-- Include if database migration files changed -->
- [ ] Migration has a down/rollback path
- [ ] No data-destructive operation without backup step noted
- [ ] Index strategy reviewed for expected query patterns

<!-- Include if CI/CD or infrastructure config changed -->
- [ ] Secrets are referenced from vault/env, not hardcoded
- [ ] Change is tested in non-production environment first
- [ ] Rollback plan exists

🤖 Generated with [Claude Code](https://claude.ai/claude-code)
```

## Step 5 — Output gh command

Print the complete `gh pr create` command. Do NOT run it — let the user run it after review.

```bash
gh pr create \
  --base $TARGET \
  --title "<generated title from Step 3>" \
  --body "$(cat <<'EOF'
<generated body from Step 4>
EOF
)"
```

## Step 6 — Output

Print in this order:

1. **Risk assessment summary** — the scored table from Step 2 with the overall level
2. **The full `gh pr create` command** — ready to copy and run
3. **Review recommendations** — which `/review-pr` filters to run based on what changed:
   - Security-sensitive changes → run `/review-pr errors` and dispatch `security-reviewer`
   - Auth / permission changes → run `/review-pr types` in addition to errors
   - High test_ratio gap → run `/review-pr tests`
   - Complex diff (complexity score ≥ 6) → run `/review-pr simplify`
   - Default: run `/review-pr` (all 6 roles)

$ARGUMENTS

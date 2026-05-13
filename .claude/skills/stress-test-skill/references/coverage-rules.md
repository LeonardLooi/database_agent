# Coverage Rules

Target: 98% line and branch coverage across all layers (or user-specified target).
Every module below target must have missing tests generated in full before the iteration closes.

---

## FastAPI — Python coverage

**Run:**
```bash
pytest --cov=app --cov-report=term-missing --cov-branch --cov-fail-under=98
```

**Per-module requirements:**

| Module type | Min line coverage | Min branch coverage | Notes |
|-------------|------------------|--------------------|----|
| Routers (endpoints) | 98% | 95% | Every endpoint exercised, happy + error paths |
| Services (business logic) | 98% | 98% | Core logic must be fully covered |
| Models / schemas | 95% | 90% | Pydantic validators must be tested |
| Middleware | 95% | 90% | Auth, logging, error handlers |
| Config / settings | 90% | 85% | Missing env var, invalid value scenarios |
| LLM agent logic | 98% | 95% | Tool-call loops, retry logic, timeout paths |
| DB repositories | 95% | 90% | CRUD operations, pool exhaustion handling |
| Utils / helpers | 98% | 95% | Pure functions — easiest to cover fully |

**Test generation priorities (if below target):**
1. Unhappy paths on every endpoint (400, 401, 403, 404, 422, 500)
2. LLM timeout and retry branches
3. DB connection failure branches
4. Background task failure + exception propagation

**Example missing test pattern:**
```python
# If router/agent.py has uncovered exception branch:
@pytest.mark.asyncio
async def test_agent_query_llm_timeout(client, mock_llm_timeout):
    response = await client.post("/api/v1/agent/query", json={"prompt": "test"})
    assert response.status_code == 504
    assert "timeout" in response.json()["detail"].lower()
```

---

## Angular — TypeScript coverage

**Run:**
```bash
ng test --no-watch --code-coverage --browsers=ChromeHeadless
```
Report: `coverage/lcov-report/index.html`

**Per-module requirements:**

| Module type | Min line coverage | Min branch coverage | Notes |
|-------------|------------------|--------------------|----|
| Services (HttpClient wrappers) | 98% | 95% | All endpoints called, error intercepted |
| Components (smart) | 95% | 90% | Input/output, lifecycle hooks, subscriptions |
| Components (dumb/presentational) | 90% | 85% | Template bindings, @Input rendering |
| Interceptors | 98% | 95% | JWT inject, 401 redirect, retry |
| Guards | 98% | 95% | Auth guard: logged in + logged out |
| Resolvers | 95% | 90% | Data loaded, error redirect |
| Pipes | 98% | 95% | Pure functions — easy to cover |
| State management (NgRx/signals) | 95% | 90% | Reducers, effects, selectors |

**Angular test generation priorities (if below target):**
1. HTTP interceptor: token injection, 401 handling, retry logic
2. Auth guard: unauthenticated redirect, role-based access
3. Service error paths: 4xx/5xx propagation to component
4. Component `ngOnDestroy`: subscription teardown
5. SSE / EventSource teardown on navigate-away

**Example missing test pattern:**
```typescript
// If auth.interceptor.spec.ts missing 401 redirect test:
it('should redirect to /login on 401', () => {
  const router = TestBed.inject(Router);
  spyOn(router, 'navigate');
  
  httpMock.expectOne('/api/protected').flush(
    { message: 'Unauthorized' },
    { status: 401, statusText: 'Unauthorized' }
  );
  
  expect(router.navigate).toHaveBeenCalledWith(['/login']);
});
```

---

## E2E coverage (Playwright / Cypress)

**Required flows — each must have a passing E2E test:**

| Flow | Tool | Assertion |
|------|------|-----------|
| Login with valid credentials | Playwright | Redirected to dashboard, token in storage |
| Login with invalid credentials | Playwright | Error message shown, no redirect |
| Logout | Playwright | Token cleared, redirected to login |
| Submit agent prompt (happy path) | Playwright | Streaming response renders, completes |
| Submit agent prompt (API error) | Playwright | User-friendly error shown, not blank |
| Navigate deep link directly | Playwright | Page loads correctly (not 404) |
| Token expiry mid-session | Playwright | Graceful re-login, not frozen |
| Network failure during stream | Playwright | Error state shown, retry option available |
| Mobile viewport rendering | Playwright | No layout overflow, tap targets reachable |

**Playwright example:**
```typescript
test('agent query streams and completes', async ({ page }) => {
  await page.goto('http://localhost/agent');
  await page.fill('[data-testid="prompt-input"]', 'What is the capital of France?');
  await page.click('[data-testid="submit-btn"]');
  
  // Wait for streaming to start
  await expect(page.locator('[data-testid="stream-output"]')).not.toBeEmpty({ timeout: 5000 });
  
  // Wait for stream to complete
  await expect(page.locator('[data-testid="done-indicator"]')).toBeVisible({ timeout: 30000 });
  
  // Assert no error state
  await expect(page.locator('[data-testid="error-banner"]')).not.toBeVisible();
});
```

---

## API contract testing

**Generate live schema:**
```bash
curl -s http://localhost/api/openapi.json > actual-schema.json
```

**Compare with Angular service calls:**
```bash
# Extract all HttpClient paths from Angular source
grep -rn "http\.\(get\|post\|put\|patch\|delete\)" src/ --include="*.ts" | \
  grep -oP "(/api[^'\"]+)" | sort -u
```

**Assert each Angular path exists in OpenAPI schema:**
```python
# contract_check.py
import json, sys

schema = json.load(open("actual-schema.json"))
paths = schema["paths"]

angular_paths = [
    "/api/v1/agent/query",
    "/api/v1/agent/stream",
    # ... add all paths from grep output
]

for path in angular_paths:
    # Normalize path params: /users/{id} matches /users/123
    if path not in paths:
        print(f"BROKEN CONTRACT: {path} not in OpenAPI schema")
        sys.exit(1)

print("All Angular API paths verified against OpenAPI schema ✅")
```

---

## Coverage reporting

**Unified report (after all tests pass):**
```bash
# Merge Python + JS coverage into one report (optional, using lcov)
# Python → lcov format
coverage lcov -o python-coverage.lcov

# Merge (requires lcov installed)
lcov -a python-coverage.lcov -a coverage/lcov.info -o merged-coverage.lcov
genhtml merged-coverage.lcov --output-directory coverage-report/
```

**Minimum bar before Phase 5:**
- FastAPI: ≥ 98% line, ≥ 95% branch
- Angular: ≥ 98% line, ≥ 95% branch
- E2E: all required flows passing
- Contract: zero drift between Angular calls and OpenAPI schema

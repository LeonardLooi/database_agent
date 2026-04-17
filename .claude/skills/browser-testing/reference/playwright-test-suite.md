# Playwright Test Suite — @playwright/test Patterns

Reference for writing actual Playwright test suites (`.spec.ts` files) — distinct from `playwright-cli` which is used for interactive inspection.

**Use `playwright-cli`** for: interactive testing, debugging, one-off QA checks.
**Use `@playwright/test`** for: automated test suites that run in CI on every PR.

## Install

```bash
npm install -D @playwright/test
npx playwright install chromium  # install browsers
```

## File Organization

```
tests/
├── e2e/
│   ├── auth/
│   │   ├── login.spec.ts
│   │   └── register.spec.ts
│   ├── features/
│   │   ├── dashboard.spec.ts
│   │   └── profile.spec.ts
│   └── api/
│       └── health.spec.ts
├── pages/                      # Page Object Models
│   ├── LoginPage.ts
│   └── DashboardPage.ts
├── fixtures/
│   └── auth.ts
└── playwright.config.ts
```

## playwright.config.ts — Our Stack

```typescript
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['junit', { outputFile: 'playwright-results.xml' }],   // for CI
    ['json', { outputFile: 'playwright-results.json' }],
  ],
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:4200',  // Angular default
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 10_000,
    navigationTimeout: 30_000,
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile-chrome', use: { ...devices['Pixel 5'] } },
    // Add firefox/webkit only if cross-browser testing is required
  ],
  webServer: {
    command: 'ng serve --port 4200',        // Angular frontend
    url: 'http://localhost:4200',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
})
```

## Page Object Model (POM)

Use POM for any page tested in more than one spec. Use `data-testid` attributes — never CSS classes (classes change with daisyUI refactors).

```typescript
// tests/pages/LoginPage.ts
import { Page, Locator } from '@playwright/test'

export class LoginPage {
  readonly page: Page
  readonly emailInput: Locator
  readonly passwordInput: Locator
  readonly submitButton: Locator
  readonly errorMessage: Locator

  constructor(page: Page) {
    this.page = page
    this.emailInput    = page.locator('[data-testid="email-input"]')
    this.passwordInput = page.locator('[data-testid="password-input"]')
    this.submitButton  = page.locator('[data-testid="login-submit"]')
    this.errorMessage  = page.locator('[data-testid="login-error"]')
  }

  async goto() {
    await this.page.goto('/login')
    await this.page.waitForLoadState('networkidle')
  }

  async login(email: string, password: string) {
    await this.emailInput.fill(email)
    await this.passwordInput.fill(password)
    await this.submitButton.click()
  }
}
```

## Test Structure

```typescript
// tests/e2e/auth/login.spec.ts
import { test, expect } from '@playwright/test'
import { LoginPage } from '../../pages/LoginPage'

test.describe('Login', () => {
  let loginPage: LoginPage

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page)
    await loginPage.goto()
  })

  test('valid credentials → redirect to dashboard', async ({ page }) => {
    await loginPage.login('user@example.com', 'password123')

    await expect(page).toHaveURL(/\/dashboard/)
    await expect(page.locator('[data-testid="user-menu"]')).toBeVisible()
  })

  test('invalid credentials → show error', async ({ page }) => {
    await loginPage.login('user@example.com', 'wrongpassword')

    await expect(loginPage.errorMessage).toBeVisible()
    await expect(loginPage.errorMessage).toContainText(/invalid/i)
    await expect(page).toHaveURL(/\/login/)  // stays on login page
  })

  test('empty form → validation errors', async ({ page }) => {
    await loginPage.submitButton.click()

    // Both fields should show validation state
    await expect(loginPage.emailInput).toHaveAttribute('aria-invalid', 'true')
    await expect(page.locator('[data-testid="email-error"]')).toBeVisible()
  })
})
```

## Flaky Test Patterns

### Quarantine a known flaky test

```typescript
test('flaky: search with debounce', async ({ page }) => {
  test.fixme(true, 'Flaky — debounce timing. Track: #123')
  // test code — won't run until fixme is removed
})

// Skip only in CI (run locally for investigation)
test('animation timing', async ({ page }) => {
  test.skip(!!process.env.CI, 'Flaky in CI — Issue #456')
  // ...
})
```

### Diagnose flakiness

```bash
# Run a single spec 10 times to surface intermittent failures
npx playwright test tests/e2e/auth/login.spec.ts --repeat-each=10

# Run with retries to see if it's timing-dependent
npx playwright test tests/e2e/auth/login.spec.ts --retries=3
```

### Common fixes

```typescript
// ❌ Race condition: assumes element is ready
await page.click('[data-testid="button"]')

// ✅ auto-wait locator
await page.locator('[data-testid="button"]').click()

// ❌ Arbitrary timeout
await page.waitForTimeout(5000)

// ✅ Wait for specific API response
await page.waitForResponse(r => r.url().includes('/api/auth') && r.status() === 200)

// ❌ Click during Angular animation
await page.click('[data-testid="menu-item"]')

// ✅ Wait for Angular animation to settle
await page.locator('[data-testid="menu-item"]').waitFor({ state: 'visible' })
await page.waitForLoadState('networkidle')
await page.locator('[data-testid="menu-item"]').click()
```

## Artifact Management

```typescript
// In tests
await page.screenshot({ path: 'artifacts/after-login.png' })
await page.screenshot({ path: 'artifacts/full-page.png', fullPage: true })

// Configured globally in playwright.config.ts:
// screenshot: 'only-on-failure'
// video: 'retain-on-failure'
// trace: 'on-first-retry'
```

View trace after failure:
```bash
npx playwright show-trace artifacts/trace.zip
```

## GitHub Actions CI

```yaml
# .github/workflows/e2e.yml
name: E2E Tests
on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - run: npm ci
      - run: npx playwright install --with-deps chromium

      - name: Start backend (NestJS)
        run: npm run start:dev &
        working-directory: ./backend
        env:
          NODE_ENV: test
          DATABASE_URL: ${{ secrets.TEST_DATABASE_URL }}

      - name: Run E2E tests
        run: npx playwright test
        env:
          BASE_URL: ${{ vars.STAGING_URL || 'http://localhost:4200' }}
          CI: true

      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: playwright-report
          path: playwright-report/
          retention-days: 30
```

## Test Report Template

Output this summary after a test run:

```markdown
## E2E Test Report — [date] — [branch]

**Duration:** Xm Ys
**Status:** PASSING ✅ / FAILING ❌

### Summary
Total: X | Passed: Y (Z%) | Failed: A | Flaky: B | Skipped: C

### Failed Tests
| Test | File:Line | Error | Screenshot |
|------|-----------|-------|-----------|
| login invalid credentials | auth/login.spec.ts:28 | expected URL /login | failed-1.png |

### Artifacts
- HTML Report: playwright-report/index.html
- Screenshots: artifacts/*.png
- Videos: artifacts/videos/*.webm
- Traces: `npx playwright show-trace artifacts/*.zip`
```

## Anti-Patterns

- **Testing via CSS classes** — daisyUI class names change during refactors. Always use `data-testid`.
- **`waitForTimeout(N)`** — arbitrary sleeps create flakiness. Use `waitForResponse`, `waitForURL`, or `waitFor({ state })`.
- **POM for every page** — only create POMs for pages used in 2+ specs. Rule of Three applies.
- **Running E2E for unit-testable logic** — E2E tests are slow. UI rendering → E2E. Business logic → unit tests. API contracts → integration tests.
- **No retries in CI** — set `retries: 2` in CI. Network blips and timing variations are real; retries distinguish flakiness from real failures.

# Angular E2E Testing with Cypress

Cypress is the recommended E2E testing framework for Angular 21 SPAs.

## Setup

```bash
# Add Cypress to existing Angular project
ng add @cypress/schematic

# Or manual install
npm install --save-dev cypress @cypress/angular
npx cypress open  # First-run setup wizard
```

cypress.config.ts:
```typescript
import { defineConfig } from 'cypress';

export default defineConfig({
  e2e: {
    baseUrl: 'http://localhost:4200',
    specPattern: 'cypress/e2e/**/*.cy.ts',
    supportFile: 'cypress/support/e2e.ts',
    video: false,
    screenshotOnRunFailure: true,
  },
  component: {
    devServer: {
      framework: 'angular',
      bundler: 'webpack',
    },
    specPattern: '**/*.cy.ts',
  },
});
```

## E2E test structure

```typescript
// cypress/e2e/login.cy.ts
describe('Login page', () => {
  beforeEach(() => {
    cy.visit('/login');
  });

  it('should display login form', () => {
    cy.get('input[type="email"]').should('be.visible');
    cy.get('input[type="password"]').should('be.visible');
    cy.get('button[type="submit"]').should('be.disabled');
  });

  it('should enable submit when form is valid', () => {
    cy.get('input[type="email"]').type('user@example.com');
    cy.get('input[type="password"]').type('password123');
    cy.get('button[type="submit"]').should('not.be.disabled');
  });

  it('should navigate to dashboard after login', () => {
    cy.intercept('POST', '/api/auth/login', {
      statusCode: 200,
      body: { token: 'fake-token', user: { name: 'Test User' } },
    }).as('loginRequest');

    cy.get('input[type="email"]').type('user@example.com');
    cy.get('input[type="password"]').type('password123');
    cy.get('button[type="submit"]').click();

    cy.wait('@loginRequest');
    cy.url().should('include', '/dashboard');
    cy.get('h1').should('contain', 'Dashboard');
  });
});
```

## Cypress Component Testing (unit-level)

```typescript
// src/app/features/dashboard/dashboard.component.cy.ts
import { mount } from '@cypress/angular';
import { DashboardComponent } from './dashboard.component';
import { provideHttpClientTesting } from '@angular/common/http/testing';

describe('DashboardComponent', () => {
  it('should render stats cards', () => {
    mount(DashboardComponent, {
      providers: [provideHttpClientTesting()],
    });

    cy.get('[data-cy="stats-card"]').should('have.length', 4);
  });

  it('should show loading skeleton while data loads', () => {
    mount(DashboardComponent, {
      providers: [provideHttpClientTesting()],
    });

    // Loading state — before any HTTP flush
    cy.get('.skeleton').should('be.visible');
  });
});
```

## Custom commands

```typescript
// cypress/support/commands.ts
declare global {
  namespace Cypress {
    interface Chainable {
      login(email: string, password: string): Chainable<void>;
      dataCy(selector: string): Chainable<JQuery<HTMLElement>>;
    }
  }
}

Cypress.Commands.add('login', (email: string, password: string) => {
  cy.intercept('POST', '/api/auth/login', {
    statusCode: 200,
    body: { token: 'test-token' },
  });
  cy.visit('/login');
  cy.get('input[type="email"]').type(email);
  cy.get('input[type="password"]').type(password);
  cy.get('button[type="submit"]').click();
  cy.url().should('include', '/dashboard');
});

// Use data-cy attributes for stable selectors (never rely on CSS classes for E2E)
Cypress.Commands.add('dataCy', (selector: string) => {
  return cy.get(`[data-cy="${selector}"]`);
});
```

## data-cy attribute convention

```html
<!-- Use data-cy for E2E selectors — never CSS classes or text content -->
<button data-cy="submit-login" type="submit" class="btn btn-primary">
  Log in
</button>

<div data-cy="stats-card" class="card bg-base-100 shadow">
  ...
</div>
```

```typescript
// In tests
cy.dataCy('submit-login').click();
cy.dataCy('stats-card').should('have.length', 4);
```

## Intercepting API calls

```typescript
it('should show error when API fails', () => {
  cy.intercept('GET', '/api/dashboard/stats', {
    statusCode: 500,
    body: { error: 'Internal Server Error' },
  }).as('statsError');

  cy.visit('/dashboard');
  cy.wait('@statsError');

  cy.get('[data-cy="error-alert"]').should('be.visible');
  cy.get('[data-cy="error-alert"]').should('contain', 'Failed to load');
});
```

## Run commands

```bash
# Open interactive Cypress UI
npx cypress open

# Run all E2E tests headless
npx cypress run

# Run component tests
npx cypress run --component

# Run specific spec
npx cypress run --spec "cypress/e2e/login.cy.ts"

# CI mode with recording
npx cypress run --record --key <dashboard-key>
```

## PropertyHarbor: E2E for marketing site

The Angular app is a static marketing site. E2E tests should cover:
- [ ] Landing page renders app download CTAs
- [ ] Navigation between pages works
- [ ] Feature pages load with correct content
- [ ] App store links are present and correct format
- [ ] Mobile viewport renders correctly (use `cy.viewport('iphone-14')`)
- [ ] No broken images or missing assets

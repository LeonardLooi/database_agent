# Angular Automated Accessibility Testing

Automated accessibility testing patterns for Angular 21.x using axe-core and pa11y. These patterns complement the manual checklist at `.claude/skills/angular-spa/reference/accessibility-checklist.md`.

## 1. axe-core with Angular Testing Library

Install:
```bash
npm install --save-dev @axe-core/playwright axe-core jest-axe @testing-library/angular
```

### Component Unit Test (jest-axe)

```typescript
// src/app/components/order-form/order-form.component.spec.ts
import { render } from '@testing-library/angular';
import { axe, toHaveNoViolations } from 'jest-axe';
import { OrderFormComponent } from './order-form.component';

expect.extend(toHaveNoViolations);

describe('OrderFormComponent — Accessibility', () => {
  it('has no WCAG 2.1 AA violations', async () => {
    const { container } = await render(OrderFormComponent, {
      componentProperties: { title: 'Create Order' },
    });
    const results = await axe(container, {
      runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] },
    });
    expect(results).toHaveNoViolations();
  });

  it('icon-only buttons have aria-label', async () => {
    const { container } = await render(OrderFormComponent);
    const results = await axe(container, {
      runOnly: { type: 'rule', values: ['button-name'] },
    });
    expect(results).toHaveNoViolations();
  });
});
```

### E2E Test with Playwright + axe-core

```typescript
// e2e/accessibility.spec.ts
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Accessibility — WCAG 2.1 AA', () => {
  test('home page has no violations', async ({ page }) => {
    await page.goto('/');
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .exclude('.no-a11y-check')
      .analyze();
    expect(results.violations).toEqual([]);
  });

  test('order form keyboard navigation', async ({ page }) => {
    await page.goto('/orders/new');
    // Tab through all interactive elements
    const focusable = await page.locator('a[href], button:not([disabled]), input, select, textarea, [tabindex]:not([tabindex="-1"])').all();
    for (const el of focusable) {
      await page.keyboard.press('Tab');
      const focused = await page.evaluate(() => document.activeElement?.tagName);
      expect(focused).not.toBe('BODY'); // focus should not escape to body
    }
  });
});
```

## 2. Keyboard Navigation Testing

```typescript
// keyboard-navigation.spec.ts
import { test, expect } from '@playwright/test';

test('modal traps focus correctly', async ({ page }) => {
  await page.goto('/dashboard');
  await page.click('[data-testid="open-modal"]');

  // Focus should be inside modal
  await page.keyboard.press('Tab');
  const focusedEl = await page.evaluate(() => {
    const el = document.activeElement;
    return el?.closest('[role="dialog"]') !== null;
  });
  expect(focusedEl).toBe(true);

  // Esc closes modal
  await page.keyboard.press('Escape');
  await expect(page.locator('[role="dialog"]')).not.toBeVisible();
});

test('skip link navigates to main content', async ({ page }) => {
  await page.goto('/');
  await page.keyboard.press('Tab'); // first tab = skip link
  const skipLink = page.locator('a[href="#main-content"]');
  await expect(skipLink).toBeFocused();
  await page.keyboard.press('Enter');
  const mainFocused = await page.evaluate(() => document.activeElement?.id);
  expect(mainFocused).toBe('main-content');
});
```

## 3. Heading Structure Validation

```typescript
// heading-structure.spec.ts — validates WCAG 2.4.6 Headings
import { test, expect } from '@playwright/test';

test('heading hierarchy has no skipped levels', async ({ page }) => {
  await page.goto('/');
  const headings = await page.evaluate(() =>
    Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, h6')).map(h => ({
      level: parseInt(h.tagName[1]),
      text: h.textContent?.trim() ?? '',
      isEmpty: !h.textContent?.trim(),
    }))
  );

  // Must have exactly one h1
  const h1Count = headings.filter(h => h.level === 1).length;
  expect(h1Count).toBe(1);

  // No empty headings
  const emptyHeadings = headings.filter(h => h.isEmpty);
  expect(emptyHeadings).toHaveLength(0);

  // No skipped levels
  let previousLevel = 0;
  for (const heading of headings) {
    if (previousLevel > 0) {
      expect(heading.level).toBeLessThanOrEqual(previousLevel + 1);
    }
    previousLevel = heading.level;
  }
});
```

## 4. Color Contrast Validation

```typescript
// contrast.spec.ts — validates WCAG 1.4.3
import { test, expect } from '@playwright/test';

function relativeLuminance(r: number, g: number, b: number): number {
  const [rs, gs, bs] = [r, g, b].map(c => {
    c = c / 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

function contrastRatio(l1: number, l2: number): number {
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

test('text elements meet WCAG AA contrast', async ({ page }) => {
  await page.goto('/');
  // axe-core handles contrast automatically — use it instead of manual calculation
  const results = await new (await import('@axe-core/playwright')).default({ page })
    .withRules(['color-contrast'])
    .analyze();
  expect(results.violations).toHaveLength(0);
});
```

## 5. High Contrast Mode CSS (Angular)

Add to global styles (`src/styles.scss`):

```scss
// High contrast media query — WCAG 1.4.11 Non-text Contrast
@media (prefers-contrast: high) {
  :root {
    --text-primary: #000000;
    --bg-primary: #ffffff;
    --border-color: #000000;
  }

  a {
    text-decoration: underline !important;
  }

  button,
  input,
  select,
  textarea {
    border: 2px solid var(--border-color) !important;
  }

  .btn {
    outline: 2px solid currentColor;
  }
}

// Reduced motion — WCAG 2.3.3
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

## 6. Form Accessibility Patterns

```html
<!-- order-form.component.html -->

<!-- Required field with visible indicator -->
<div class="form-control">
  <label class="label" for="item-id">
    <span class="label-text">Item ID <span aria-label="required" class="text-error">*</span></span>
  </label>
  <input
    id="item-id"
    type="text"
    class="input input-bordered"
    [formControl]="itemIdControl"
    aria-required="true"
    [attr.aria-invalid]="itemIdControl.invalid && itemIdControl.touched"
    aria-describedby="item-id-error"
  />
  @if (itemIdControl.invalid && itemIdControl.touched) {
    <span id="item-id-error" role="alert" class="label-text-alt text-error">
      Enter a valid item ID (letters, numbers, hyphens only)
    </span>
  }
</div>

<!-- Live region for async status updates -->
<div aria-live="polite" aria-atomic="true" class="sr-only">
  {{ statusMessage() }}
</div>

<!-- Icon-only button -->
<button type="button" class="btn btn-circle btn-ghost" aria-label="Remove item from cart">
  <svg aria-hidden="true" focusable="false">...</svg>
</button>
```

## pa11y Integration

```bash
# Run pa11y against built Angular app (port 4200)
npx pa11y http://localhost:4200 --standard WCAG2AA --threshold 0 --reporter json > a11y-report.json

# Run against multiple routes
npx pa11y-ci --config .pa11yci.json

# .pa11yci.json
{
  "defaults": {
    "standard": "WCAG2AA",
    "threshold": 0,
    "timeout": 30000
  },
  "urls": [
    "http://localhost:4200",
    "http://localhost:4200/orders",
    "http://localhost:4200/orders/new",
    "http://localhost:4200/dashboard"
  ]
}
```

# Angular Testing with Vitest

Angular 21 supports Vitest as the default test runner (replacing Karma/Jasmine). Vitest is faster, ESM-native, and integrates with Vite's build pipeline.

## Setup — new Angular project

```bash
# Angular 21 projects: Vitest is the default when using the CLI
npx @angular/cli@latest new my-app --style=scss --ssr=false --ai-config=claude
# Vitest config is generated automatically
```

## Setup — existing project (migrate from Karma)

```bash
# Remove Karma
npm uninstall karma karma-chrome-launcher karma-coverage karma-jasmine karma-jasmine-html-reporter

# Add Vitest + Angular Vitest preset
npm install --save-dev vitest @analogjs/vitest-angular

# Update angular.json: change "test" builder to Vitest
```

angular.json change:
```json
{
  "architect": {
    "test": {
      "builder": "@analogjs/vitest-angular:test",
      "options": {
        "configFile": "vitest.config.ts"
      }
    }
  }
}
```

vitest.config.ts:
```typescript
import { defineConfig } from 'vitest/config';
import angular from '@analogjs/vitest-angular/plugin';

export default defineConfig({
  plugins: [angular()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['src/test-setup.ts'],
    include: ['src/**/*.spec.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      thresholds: {
        branches: 90,
        lines: 90,
        functions: 90,
        statements: 90,
      },
    },
  },
});
```

src/test-setup.ts:
```typescript
import '@angular/compiler';
import { getTestBed } from '@angular/core/testing';
import { BrowserDynamicTestingModule, platformBrowserDynamicTesting } from '@angular/platform-browser-dynamic/testing';

getTestBed().initTestEnvironment(
  BrowserDynamicTestingModule,
  platformBrowserDynamicTesting(),
);
```

## Writing tests with Vitest syntax

Vitest uses the same `describe`/`it`/`expect` API as Jest — tests are largely compatible.

```typescript
// counter.component.spec.ts
import { TestBed } from '@angular/core/testing';
import { CounterComponent } from './counter.component';

describe('CounterComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CounterComponent],
    }).compileComponents();
  });

  it('should increment count on button click', async () => {
    const fixture = TestBed.createComponent(CounterComponent);
    fixture.detectChanges();

    const button = fixture.nativeElement.querySelector('button');
    button.click();
    fixture.detectChanges();

    expect(fixture.componentInstance.count()).toBe(1);
  });
});
```

## Zoneless TestBed (Angular 21 default)

```typescript
import { TestBed } from '@angular/core/testing';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';

// In Angular 21, TestBed is zoneless by default — no special config needed
// But if you need to be explicit:
await TestBed.configureTestingModule({
  imports: [MyComponent],
  providers: [
    // Only needed if explicitly enabling for Angular 20 compat
    // provideExperimentalZonelessChangeDetection(),
  ],
}).compileComponents();
```

## Testing Signals

```typescript
it('should react to signal changes', async () => {
  const fixture = TestBed.createComponent(SearchComponent);
  fixture.detectChanges();

  // Set signal input
  fixture.componentRef.setInput('query', 'angular');
  fixture.detectChanges();

  // Read signal value
  expect(fixture.componentInstance.results()).toHaveLength(3);
  
  // Wait for async signal resolution
  await fixture.whenStable();
  fixture.detectChanges();
  
  const items = fixture.nativeElement.querySelectorAll('.result-item');
  expect(items.length).toBe(3);
});
```

## Testing resource() (async data primitive)

```typescript
import { TestBed, fakeAsync, tick } from '@angular/core/testing';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';

describe('UserProfileComponent', () => {
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserProfileComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('should display user name after resource loads', fakeAsync(async () => {
    const fixture = TestBed.createComponent(UserProfileComponent);
    fixture.componentRef.setInput('userId', '42');
    fixture.detectChanges();

    // resource() starts loading — isLoading() is true
    expect(fixture.componentInstance.userResource.isLoading()).toBe(true);

    // Flush HTTP request
    const req = httpMock.expectOne('/api/users/42');
    req.flush({ id: '42', name: 'Jane Doe' });
    tick();
    fixture.detectChanges();

    expect(fixture.componentInstance.userResource.value()?.name).toBe('Jane Doe');
    expect(fixture.nativeElement.querySelector('h2').textContent).toContain('Jane Doe');
  }));
});
```

## Vitest vs Karma comparison

| Feature | Karma | Vitest |
|---|---|---|
| Speed | Slow (browser launch) | Fast (native ESM) |
| Watch mode | Slow rebuild | Instant HMR |
| ESM support | Limited | Native |
| Coverage | Istanbul | V8 (faster) |
| Angular 21 default | No | Yes |
| Config file | karma.conf.js | vitest.config.ts |

## Run commands

```bash
# Run all tests
ng test

# Watch mode
ng test --watch

# Coverage
ng test --coverage

# Single file
ng test --include="**/counter.component.spec.ts"

# Run via Vitest CLI directly
npx vitest run
npx vitest --coverage
```

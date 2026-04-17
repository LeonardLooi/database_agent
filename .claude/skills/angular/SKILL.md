---
name: angular
description: "Angular 21.x core patterns and APIs — Signals, Standalone components, Zoneless change detection, SSR/Hydration, Dependency Injection, Component composition, Signal-based state, Testing. Load when writing Angular code for API reference, testing patterns, or SSR configuration."
allowed-tools: Read, Edit, Write, Glob, Grep, Bash, WebFetch, mcp__context7__resolve-library-id, mcp__context7__query-docs, mcp__angular-cli__get_best_practices, mcp__angular-cli__search_documentation
metadata:
  triggers: Angular signals, Angular standalone, Angular zoneless, Angular SSR, Angular hydration, Angular DI, Angular testing, Angular state management, Angular 21
  related-skills: angular-spa, angular-best-practices, angular-ui-patterns
  domain: frontend
  role: specialist
  scope: reference
  output-format: code
last-reviewed: "2026-03-15"
---

## Iron Law

**READ `angular-spa` skill for TailwindCSS 4.x, daisyUI 5.5.5, and workspace conventions BEFORE implementing. This skill is API reference only — no design token or styling patterns here.**

## When to Use This Skill

- Building new Angular applications (v20+)
- Implementing Signals-based reactive patterns
- Creating Standalone Components and migrating from NgModules
- Configuring Zoneless Angular applications
- Implementing SSR, prerendering, and hydration
- Optimizing Angular performance
- Adopting modern Angular patterns and best practices

## Do Not Use This Skill When

- Migrating from AngularJS (1.x) — use `angular-migration` skill
- Working with legacy Angular apps that cannot upgrade
- General TypeScript issues — use `typescript-expert` skill

---

**Version context:** Angular 20 (Signals/Zoneless stable), Angular 21 (Signals-first default, current), Angular 22 (Signal Forms — upcoming).

---

## Angular 21 Zoneless Note

Angular 21 is **zoneless by default**. Do NOT add `provideZonelessChangeDetection()` — it is implicit and adding it causes warnings.

- Angular 20: `provideZonelessChangeDetection()` required explicitly
- Angular 21+: Zoneless is the default. No provider needed. No `zone.js` import.

This workspace uses Angular 21+. The patterns below show v20-style explicit providers for reference — in Angular 21 omit those providers.

---

## 1. Signals: The New Reactive Primitive

Signals are Angular's fine-grained reactivity system, replacing zone.js-based change detection.

### Core Concepts

```typescript
import { signal, computed, effect } from "@angular/core";

// Writable signal
const count = signal(0);

// Read value
console.log(count()); // 0

// Update value
count.set(5); // Direct set
count.update((v) => v + 1); // Functional update

// Computed (derived) signal
const doubled = computed(() => count() * 2);

// Effect (side effects)
effect(() => {
  console.log(`Count changed to: ${count()}`);
});
```

### Signal-Based Inputs and Outputs

```typescript
import { Component, input, output, model } from "@angular/core";

@Component({
  selector: "app-user-card",
  standalone: true,
  template: `
    <div class="card">
      <h3>{{ name() }}</h3>
      <span>{{ role() }}</span>
      <button (click)="select.emit(id())">Select</button>
    </div>
  `,
})
export class UserCardComponent {
  // Signal inputs (read-only)
  id = input.required<string>();
  name = input.required<string>();
  role = input<string>("User"); // With default

  // Output
  select = output<string>();

  // Two-way binding (model)
  isSelected = model(false);
}

// Usage:
// <app-user-card [id]="'123'" [name]="'John'" [(isSelected)]="selected" />
```

### Signal Queries (viewChild / contentChild)

```typescript
import {
  Component,
  viewChild,
  viewChildren,
  contentChild,
} from "@angular/core";

@Component({
  selector: "app-container",
  standalone: true,
  template: `
    <input #searchInput />
    <app-item *ngFor="let item of items()" />
  `,
})
export class ContainerComponent {
  // Signal-based queries
  searchInput = viewChild<ElementRef>("searchInput");
  items = viewChildren(ItemComponent);
  projectedContent = contentChild(HeaderDirective);

  focusSearch() {
    this.searchInput()?.nativeElement.focus();
  }
}
```

---

## 2. Standalone Components

Standalone components are self-contained and don't require NgModule declarations.

### Creating Standalone Components

```typescript
import { Component } from "@angular/core";
import { CommonModule } from "@angular/common";
import { RouterLink } from "@angular/router";

@Component({
  selector: "app-header",
  standalone: true,
  imports: [CommonModule, RouterLink], // Direct imports
  template: `
    <header>
      <a routerLink="/">Home</a>
      <a routerLink="/about">About</a>
    </header>
  `,
})
export class HeaderComponent {}
```

### Bootstrapping Without NgModule

```typescript
// main.ts
import { bootstrapApplication } from "@angular/platform-browser";
import { provideRouter } from "@angular/router";
import { provideHttpClient } from "@angular/common/http";
import { AppComponent } from "./app/app.component";
import { routes } from "./app/app.routes";

bootstrapApplication(AppComponent, {
  providers: [provideRouter(routes), provideHttpClient()],
});
```

### Lazy Loading Standalone Components

```typescript
// app.routes.ts
import { Routes } from "@angular/router";

export const routes: Routes = [
  {
    path: "dashboard",
    loadComponent: () =>
      import("./dashboard/dashboard.component").then(
        (m) => m.DashboardComponent,
      ),
  },
  {
    path: "admin",
    loadChildren: () =>
      import("./admin/admin.routes").then((m) => m.ADMIN_ROUTES),
  },
];
```

---

## 3. Zoneless Angular

Zoneless applications don't use zone.js, improving performance and debugging.

> **Angular 21 reminder:** Zoneless is the default. The `provideZonelessChangeDetection()` call shown below is v20-style — omit it in Angular 21 projects.

### Enabling Zoneless Mode (Angular 20 only)

```typescript
// main.ts (Angular 20 style — NOT needed in Angular 21+)
import { bootstrapApplication } from "@angular/platform-browser";
import { provideZonelessChangeDetection } from "@angular/core";
import { AppComponent } from "./app/app.component";

bootstrapApplication(AppComponent, {
  providers: [provideZonelessChangeDetection()],
});
```

### Zoneless Component Patterns

```typescript
import { Component, signal, ChangeDetectionStrategy } from "@angular/core";

@Component({
  selector: "app-counter",
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div>Count: {{ count() }}</div>
    <button (click)="increment()">+</button>
  `,
})
export class CounterComponent {
  count = signal(0);

  increment() {
    this.count.update((v) => v + 1);
    // No zone.js needed — Signal triggers change detection
  }
}
```

### Key Zoneless Benefits

- **Performance**: No zone.js patches on async APIs
- **Debugging**: Clean stack traces without zone wrappers
- **Bundle size**: Smaller without zone.js (~15KB savings)
- **Interoperability**: Better with Web Components and micro-frontends

---

## 4. Server-Side Rendering & Hydration

### SSR Setup with Angular CLI

```bash
ng add @angular/ssr
```

### Hydration Configuration

```typescript
// app.config.ts
import { ApplicationConfig } from "@angular/core";
import {
  provideClientHydration,
  withEventReplay,
} from "@angular/platform-browser";

export const appConfig: ApplicationConfig = {
  providers: [provideClientHydration(withEventReplay())],
};
```

### Incremental Hydration (v20+)

```typescript
import { Component } from "@angular/core";

@Component({
  selector: "app-page",
  standalone: true,
  template: `
    <app-hero />

    @defer (hydrate on viewport) {
      <app-comments />
    }

    @defer (hydrate on interaction) {
      <app-chat-widget />
    }
  `,
})
export class PageComponent {}
```

**Hydration triggers:** `on idle` | `on viewport` | `on interaction` | `on hover` | `on timer(ms)`

---

## 5. Modern Routing Patterns

> See [references/api-reference.md](references/api-reference.md) for full routing examples (functional guards, resolvers).

**Key patterns:**
- `CanActivateFn` with `inject()` for functional guards
- `ResolveFn<T>` for route-level data pre-fetching
- `toSignal(route.data.pipe(...))` to consume resolved data

---

## 6. Dependency Injection

> See [references/api-reference.md](references/api-reference.md) for full DI examples (inject(), InjectionToken).

**Key patterns:**
- `inject()` function (no constructor required)
- `InjectionToken<T>` for typed configuration values

---

## 7. Component Composition

> See [references/api-reference.md](references/api-reference.md) for full composition examples (ng-content slots, hostDirectives).

**Key patterns:**
- `<ng-content select="[attr]">` for named slots
- `hostDirectives` for behavior composition without inheritance

---

## 8. Signal-Based State Management

> See [references/api-reference.md](references/api-reference.md) for full state service and component store examples.

**Key patterns:**
- Private `signal()` + public `computed()` for encapsulated state
- `@Injectable()` (no `providedIn: 'root'`) for scoped component stores

---

## 9. Forms with Signals

> See [references/api-reference.md](references/api-reference.md) for full reactive forms and signal form patterns.

**Key patterns:**
- `FormBuilder` + `Validators` for current reactive forms
- Signal-based validation via `computed()` (v22+ preview)

---

## 10. Performance Optimization

### Change Detection Strategies

Always use `ChangeDetectionStrategy.OnPush`. Triggers re-check only when: input signal/reference changes, event handler runs, async pipe emits, or signal value changes.

### Defer Blocks for Lazy Loading

```typescript
@defer (on viewport) {
  <app-heavy-chart />
} @placeholder {
  <div class="skeleton" />
} @loading (minimum 200ms) {
  <app-spinner />
} @error {
  <p>Failed to load chart</p>
}
```

### NgOptimizedImage

```typescript
import { NgOptimizedImage } from '@angular/common';

@Component({
  imports: [NgOptimizedImage],
  template: `
    <img
      ngSrc="hero.jpg"
      width="800"
      height="600"
      priority
    />

    <img
      ngSrc="thumbnail.jpg"
      width="200"
      height="150"
      loading="lazy"
      placeholder="blur"
    />
  `
})
```

---

## 11. Testing Modern Angular

> See [references/api-reference.md](references/api-reference.md) for full testing examples (signal components, setInput).

**Key patterns:**
- Import standalone components directly in `TestBed.configureTestingModule({ imports: [...] })`
- Use `componentRef.setInput('name', value)` to set signal inputs in tests
- Call `fixture.detectChanges()` after signal mutations to trigger DOM update

---

## Key Decision Tables

> See [references/api-reference.md](references/api-reference.md) for full Signals vs RxJS table and Pattern Do/Don't summary.

| Use Case              | Use Signals  | Use RxJS                      |
| --------------------- | ------------ | ----------------------------- |
| Local component state | Yes          | No — overkill                 |
| HTTP requests         | No           | Yes — HttpClient Observable   |
| Complex async flows   | No           | Yes — switchMap, mergeMap     |

---

## Common Troubleshooting

> See [references/api-reference.md](references/api-reference.md) for the full troubleshooting table.

| Issue                          | Solution                                            |
| ------------------------------ | --------------------------------------------------- |
| Signal not updating UI         | Ensure `OnPush` + call signal as function `count()` |
| `provideZonelessChangeDetection` warning in v21 | Remove call — zoneless is the default in v21+ |
| SSR fetch fails                | Use `TransferState` or `withFetch()`                |

---

## Related Skills

- `angular-spa` — workspace skill with TailwindCSS 4.x, daisyUI 5.5.5, conventions
- `angular-best-practices` — impact-prioritized rules (CRITICAL to LOW-MEDIUM)
- `angular-ui-patterns` — loading, error, empty state patterns

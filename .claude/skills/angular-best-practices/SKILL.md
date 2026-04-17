---
name: angular-best-practices
description: "Impact-prioritized Angular 21.x best practices — CRITICAL: OnPush+Signals, async waterfalls, bundle optimization. HIGH: rendering performance, SSR hydration. MEDIUM: template optimization, state management. LOW: memory management. Load when reviewing Angular code, writing components, or optimizing performance."
allowed-tools: Read, Edit, Write, Glob, Grep, Bash, WebFetch, mcp__context7__resolve-library-id, mcp__context7__query-docs, mcp__angular-cli__get_best_practices
metadata:
  triggers: Angular performance, Angular optimization, Angular OnPush, Angular bundle, Angular lazy loading, Angular SSR, Angular memory leak, Angular trackBy, Angular virtual scroll, Angular review
  related-skills: angular-spa, angular, angular-ui-patterns
  domain: frontend
  role: specialist
  scope: review
  output-format: checklist
last-reviewed: "2026-03-15"
---

## Iron Law

**LOAD `angular-spa` FIRST for TailwindCSS 4.x + daisyUI workspace conventions. This skill provides ranked best practices for review and optimization — not implementation templates.**

---

## When to Apply

Reference these guidelines when:

- Writing new Angular components or pages
- Implementing data fetching patterns
- Reviewing code for performance issues
- Refactoring existing Angular code
- Optimizing bundle size or load times
- Configuring SSR/hydration

---

## Priority Matrix

| Priority | Category              | Impact     | Focus                           |
| -------- | --------------------- | ---------- | ------------------------------- |
| 1        | Change Detection      | CRITICAL   | Signals, OnPush, Zoneless       |
| 2        | Async Waterfalls      | CRITICAL   | RxJS patterns, SSR preloading   |
| 3        | Bundle Optimization   | CRITICAL   | Lazy loading, tree shaking      |
| 4        | Rendering Performance | HIGH       | @defer, trackBy, virtualization |
| 5        | Server-Side Rendering | HIGH       | Hydration, prerendering         |
| 6        | Template Optimization | MEDIUM     | Control flow, pipes             |
| 7        | State Management      | MEDIUM     | Signal patterns, selectors      |
| 8        | Memory Management     | LOW-MEDIUM | Cleanup, subscriptions          |

---

## 1. Change Detection (CRITICAL)

### Use OnPush Change Detection

```typescript
// ✅ CORRECT - OnPush with Signals
@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<div>{{ count() }}</div>`,
})
export class CounterComponent {
  count = signal(0);
}

// ❌ WRONG - Default change detection
@Component({
  template: `<div>{{ count }}</div>`, // Checked every cycle
})
export class CounterComponent {
  count = 0;
}
```

### Prefer Signals Over Mutable Properties

```typescript
// ✅ CORRECT - Signals trigger precise updates
@Component({
  template: `
    <h1>{{ title() }}</h1>
    <p>Count: {{ count() }}</p>
  `,
})
export class DashboardComponent {
  title = signal("Dashboard");
  count = signal(0);
}

// ❌ WRONG - Mutable properties require zone.js checks
@Component({
  template: `
    <h1>{{ title }}</h1>
    <p>Count: {{ count }}</p>
  `,
})
export class DashboardComponent {
  title = "Dashboard";
  count = 0;
}
```

### Enable Zoneless for New Projects

```typescript
// main.ts - Zoneless Angular (v20+)
bootstrapApplication(AppComponent, {
  providers: [provideZonelessChangeDetection()],
});
```

**Benefits:**

- No zone.js patches on async APIs
- Smaller bundle (~15KB savings)
- Clean stack traces for debugging
- Better micro-frontend compatibility

---

## 2. Async Operations & Waterfalls (CRITICAL)

### Eliminate Sequential Data Fetching

```typescript
// ❌ WRONG - Nested subscriptions create waterfalls
this.route.params.subscribe((params) => {
  // 1. Wait for params
  this.userService.getUser(params.id).subscribe((user) => {
    // 2. Wait for user
    this.postsService.getPosts(user.id).subscribe((posts) => {
      // 3. Wait for posts
    });
  });
});

// ✅ CORRECT - Parallel execution with forkJoin
forkJoin({
  user: this.userService.getUser(id),
  posts: this.postsService.getPosts(id),
}).subscribe((data) => {
  // Fetched in parallel
});

// ✅ CORRECT - Flatten dependent calls with switchMap
this.route.params
  .pipe(
    map((p) => p.id),
    switchMap((id) => this.userService.getUser(id)),
  )
  .subscribe();
```

### Avoid Client-Side Waterfalls in SSR

```typescript
// ✅ CORRECT - Use resolvers or blocking hydration for critical data
export const route: Route = {
  path: "profile/:id",
  resolve: { data: profileResolver }, // Fetched on server before navigation
  component: ProfileComponent,
};

// ❌ WRONG - Component fetches data on init
class ProfileComponent implements OnInit {
  ngOnInit() {
    // Starts ONLY after JS loads and component renders
    this.http.get("/api/profile").subscribe();
  }
}
```

---

## 3. Bundle Optimization (CRITICAL)

### Lazy Load Routes

```typescript
// ✅ CORRECT - Lazy load feature routes
export const routes: Routes = [
  {
    path: "admin",
    loadChildren: () =>
      import("./admin/admin.routes").then((m) => m.ADMIN_ROUTES),
  },
  {
    path: "dashboard",
    loadComponent: () =>
      import("./dashboard/dashboard.component").then(
        (m) => m.DashboardComponent,
      ),
  },
];

// ❌ WRONG - Eager loading everything
import { AdminModule } from "./admin/admin.module";
export const routes: Routes = [
  { path: "admin", component: AdminComponent }, // In main bundle
];
```

### Use @defer for Heavy Components

```html
<!-- ✅ CORRECT - Heavy component loads on demand -->
@defer (on viewport) {
<app-analytics-chart [data]="data()" />
} @placeholder {
<div class="chart-skeleton"></div>
}

<!-- ❌ WRONG - Heavy component in initial bundle -->
<app-analytics-chart [data]="data()" />
```

### Avoid Barrel File Re-exports

```typescript
// ❌ WRONG - Imports entire barrel, breaks tree-shaking
import { Button, Modal, Table } from "@shared/components";

// ✅ CORRECT - Direct imports
import { Button } from "@shared/components/button/button.component";
import { Modal } from "@shared/components/modal/modal.component";
```

### Dynamic Import Third-Party Libraries

```typescript
// ✅ CORRECT - Load heavy library on demand
async loadChart() {
  const { Chart } = await import('chart.js');
  this.chart = new Chart(this.canvas, config);
}

// ❌ WRONG - Bundle Chart.js in main chunk
import { Chart } from 'chart.js';
```

---

## 4. Rendering Performance (HIGH)

### Always Use trackBy with @for

```html
<!-- ✅ CORRECT - Efficient DOM updates -->
@for (item of items(); track item.id) {
<app-item-card [item]="item" />
}

<!-- ❌ WRONG - Entire list re-renders on any change -->
@for (item of items(); track $index) {
<app-item-card [item]="item" />
}
```

### Use Virtual Scrolling for Large Lists

Use `CdkVirtualScrollViewport` with `itemSize` for lists >50 items. See [references/extended-patterns.md](references/extended-patterns.md) for the full example.

### Prefer Pure Pipes Over Methods

Use `@Pipe({ pure: true })` — memoized and called only when inputs change. Never call methods in templates — they run every change detection cycle. See [references/extended-patterns.md](references/extended-patterns.md) for examples.

### Use computed() for Derived Data

Use `computed()` instead of getters — cached until signal dependencies change. See [references/extended-patterns.md](references/extended-patterns.md) for before/after examples.

---

## 5. Server-Side Rendering (HIGH)

### Configure Incremental Hydration

```typescript
// app.config.ts
import {
  provideClientHydration,
  withIncrementalHydration,
} from "@angular/platform-browser";

export const appConfig: ApplicationConfig = {
  providers: [
    provideClientHydration(withIncrementalHydration(), withEventReplay()),
  ],
};
```

### Defer Non-Critical Content

```html
<!-- Critical above-the-fold content -->
<app-header />
<app-hero />

<!-- Below-fold deferred with hydration triggers -->
@defer (hydrate on viewport) {
<app-product-grid />
} @defer (hydrate on interaction) {
<app-chat-widget />
}
```

### Use TransferState for SSR Data

```typescript
@Injectable({ providedIn: "root" })
export class DataService {
  private http = inject(HttpClient);
  private transferState = inject(TransferState);
  private platformId = inject(PLATFORM_ID);

  getData(key: string): Observable<Data> {
    const stateKey = makeStateKey<Data>(key);

    if (isPlatformBrowser(this.platformId)) {
      const cached = this.transferState.get(stateKey, null);
      if (cached) {
        this.transferState.remove(stateKey);
        return of(cached);
      }
    }

    return this.http.get<Data>(`/api/${key}`).pipe(
      tap((data) => {
        if (isPlatformServer(this.platformId)) {
          this.transferState.set(stateKey, data);
        }
      }),
    );
  }
}
```

---

## 6. Template Optimization (MEDIUM)

### Use New Control Flow Syntax

```html
<!-- ✅ CORRECT - New control flow (faster, smaller bundle) -->
@if (user()) {
<span>{{ user()!.name }}</span>
} @else {
<span>Guest</span>
} @for (item of items(); track item.id) {
<app-item [item]="item" />
} @empty {
<p>No items</p>
}

<!-- ❌ WRONG - Legacy structural directives -->
<span *ngIf="user; else guest">{{ user.name }}</span>
<ng-template #guest><span>Guest</span></ng-template>
```

### Avoid Complex Template Expressions

```typescript
// ✅ CORRECT - Precompute in component
class Component {
  items = signal<Item[]>([]);
  sortedItems = computed(() =>
    [...this.items()].sort((a, b) => a.name.localeCompare(b.name))
  );
}

// Template
@for (item of sortedItems(); track item.id) { ... }

// ❌ WRONG - Sorting in template on every render
@for (item of items() | sort:'name'; track item.id) { ... }
```

---

## 7. State Management (MEDIUM)

> See [references/extended-patterns.md](references/extended-patterns.md) for full examples (selectors, feature-scoped stores).

**Key rules:**
- Use `store.selectSignal(selector)` — subscribes only to the slice that changed, not entire state
- `@Injectable()` without `providedIn: 'root'` for feature-scoped stores provided at component level

---

## 8. Memory Management (LOW-MEDIUM)

> See [references/extended-patterns.md](references/extended-patterns.md) for full examples (takeUntilDestroyed, toSignal).

**Key rules:**
- Use `takeUntilDestroyed(this.destroyRef)` — auto-unsubscribes on component destroy, no manual `ngOnDestroy`
- Prefer `toSignal(obs$)` over manual subscribe/unsubscribe entirely

---

## Quick Reference Checklists

> See [references/extended-patterns.md](references/extended-patterns.md) for the full New Component, Performance Review, and SSR checklists.

**New component minimum:**
- [ ] `changeDetection: ChangeDetectionStrategy.OnPush`
- [ ] `standalone: true`
- [ ] `@for` with `track item.id` (not `$index`)

---

## Related Skills

- `angular-spa` — workspace skill: TailwindCSS 4.x, daisyUI 5.5.5, conventions
- `angular` — core API reference: signals, standalone, routing patterns
- `angular-ui-patterns` — UI state patterns: loading, error, empty states

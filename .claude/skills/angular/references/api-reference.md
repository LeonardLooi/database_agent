# Angular API Reference

Extended patterns and examples moved from `../SKILL.md` for reference.

---

## Routing Patterns

### Functional Route Guards

```typescript
// auth.guard.ts
import { inject } from "@angular/core";
import { Router, CanActivateFn } from "@angular/router";
import { AuthService } from "./auth.service";

export const authGuard: CanActivateFn = (route, state) => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (auth.isAuthenticated()) {
    return true;
  }

  return router.createUrlTree(["/login"], {
    queryParams: { returnUrl: state.url },
  });
};

// Usage in routes
export const routes: Routes = [
  {
    path: "dashboard",
    loadComponent: () => import("./dashboard.component"),
    canActivate: [authGuard],
  },
];
```

### Route-Level Data Resolvers

```typescript
import { inject } from '@angular/core';
import { ResolveFn } from '@angular/router';
import { UserService } from './user.service';
import { User } from './user.model';

export const userResolver: ResolveFn<User> = (route) => {
  const userService = inject(UserService);
  return userService.getUser(route.paramMap.get('id')!);
};

// In routes
{
  path: 'user/:id',
  loadComponent: () => import('./user.component'),
  resolve: { user: userResolver }
}

// In component
export class UserComponent {
  private route = inject(ActivatedRoute);
  user = toSignal(this.route.data.pipe(map(d => d['user'])));
}
```

---

## Dependency Injection

### Modern inject() Function

```typescript
import { Component, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { UserService } from './user.service';

@Component({...})
export class UserComponent {
  // Modern inject() — no constructor needed
  private http = inject(HttpClient);
  private userService = inject(UserService);

  // Works in any injection context
  users = toSignal(this.userService.getUsers());
}
```

### Injection Tokens for Configuration

```typescript
import { InjectionToken, inject } from "@angular/core";

// Define token
export const API_BASE_URL = new InjectionToken<string>("API_BASE_URL");

// Provide in config
bootstrapApplication(AppComponent, {
  providers: [{ provide: API_BASE_URL, useValue: "https://api.example.com" }],
});

// Inject in service
@Injectable({ providedIn: "root" })
export class ApiService {
  private baseUrl = inject(API_BASE_URL);

  get(endpoint: string) {
    return this.http.get(`${this.baseUrl}/${endpoint}`);
  }
}
```

---

## Component Composition

### Content Projection (Slots)

```typescript
@Component({
  selector: 'app-card',
  template: `
    <div class="card">
      <div class="header">
        <!-- Select by attribute -->
        <ng-content select="[card-header]"></ng-content>
      </div>
      <div class="body">
        <!-- Default slot -->
        <ng-content></ng-content>
      </div>
    </div>
  `
})
export class CardComponent {}

// Usage
// <app-card>
//   <h3 card-header>Title</h3>
//   <p>Body content</p>
// </app-card>
```

### Host Directives (Composition Without Inheritance)

```typescript
// Reusable behaviors without inheritance
@Directive({
  standalone: true,
  selector: '[appTooltip]',
  inputs: ['tooltip']
})
export class TooltipDirective { ... }

@Component({
  selector: 'app-button',
  standalone: true,
  hostDirectives: [
    {
      directive: TooltipDirective,
      inputs: ['tooltip: title'] // Map input
    }
  ],
  template: `<ng-content />`
})
export class ButtonComponent {}
```

---

## Signal-Based State Management

### Signal State Service

```typescript
import { Injectable, signal, computed } from "@angular/core";

interface AppState {
  user: User | null;
  theme: "light" | "dark";
  notifications: Notification[];
}

@Injectable({ providedIn: "root" })
export class StateService {
  // Private writable signals
  private _user = signal<User | null>(null);
  private _theme = signal<"light" | "dark">("light");
  private _notifications = signal<Notification[]>([]);

  // Public read-only computed
  readonly user = computed(() => this._user());
  readonly theme = computed(() => this._theme());
  readonly notifications = computed(() => this._notifications());
  readonly unreadCount = computed(
    () => this._notifications().filter((n) => !n.read).length,
  );

  // Actions
  setUser(user: User | null) {
    this._user.set(user);
  }

  toggleTheme() {
    this._theme.update((t) => (t === "light" ? "dark" : "light"));
  }

  addNotification(notification: Notification) {
    this._notifications.update((n) => [...n, notification]);
  }
}
```

### Component Store Pattern with Signals

```typescript
import { Injectable, signal, computed, inject } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { toSignal } from "@angular/core/rxjs-interop";

@Injectable()
export class ProductStore {
  private http = inject(HttpClient);

  // State
  private _products = signal<Product[]>([]);
  private _loading = signal(false);
  private _filter = signal("");

  // Selectors
  readonly products = computed(() => this._products());
  readonly loading = computed(() => this._loading());
  readonly filteredProducts = computed(() => {
    const filter = this._filter().toLowerCase();
    return this._products().filter((p) =>
      p.name.toLowerCase().includes(filter),
    );
  });

  // Actions
  loadProducts() {
    this._loading.set(true);
    this.http.get<Product[]>("/api/products").subscribe({
      next: (products) => {
        this._products.set(products);
        this._loading.set(false);
      },
      error: () => this._loading.set(false),
    });
  }

  setFilter(filter: string) {
    this._filter.set(filter);
  }
}
```

---

## Forms with Signals

### Current Reactive Forms

```typescript
import { Component, inject } from "@angular/core";
import { FormBuilder, Validators, ReactiveFormsModule } from "@angular/forms";

@Component({
  selector: "app-user-form",
  standalone: true,
  imports: [ReactiveFormsModule],
  template: `
    <form [formGroup]="form" (ngSubmit)="onSubmit()">
      <input formControlName="name" placeholder="Name" />
      <input formControlName="email" type="email" placeholder="Email" />
      <button [disabled]="form.invalid">Submit</button>
    </form>
  `,
})
export class UserFormComponent {
  private fb = inject(FormBuilder);

  form = this.fb.group({
    name: ["", Validators.required],
    email: ["", [Validators.required, Validators.email]],
  });

  onSubmit() {
    if (this.form.valid) {
      console.log(this.form.value);
    }
  }
}
```

### Signal-Aware Form Patterns (Preview — v22+)

```typescript
// Future Signal Forms API (experimental — available in v22+)
import { Component, signal, computed } from '@angular/core';

@Component({...})
export class SignalFormComponent {
  name = signal('');
  email = signal('');

  // Computed validation
  isValid = computed(() =>
    this.name().length > 0 &&
    this.email().includes('@')
  );

  submit() {
    if (this.isValid()) {
      console.log({ name: this.name(), email: this.email() });
    }
  }
}
```

---

## Testing Modern Angular

### Testing Signal Components

```typescript
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { CounterComponent } from "./counter.component";

describe("CounterComponent", () => {
  let component: CounterComponent;
  let fixture: ComponentFixture<CounterComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CounterComponent], // Standalone import
    }).compileComponents();

    fixture = TestBed.createComponent(CounterComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should increment count", () => {
    expect(component.count()).toBe(0);

    component.increment();

    expect(component.count()).toBe(1);
  });

  it("should update DOM on signal change", () => {
    component.count.set(5);
    fixture.detectChanges();

    const el = fixture.nativeElement.querySelector(".count");
    expect(el.textContent).toContain("5");
  });
});
```

### Testing with Signal Inputs (setInput)

```typescript
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ComponentRef } from "@angular/core";
import { UserCardComponent } from "./user-card.component";

describe("UserCardComponent", () => {
  let fixture: ComponentFixture<UserCardComponent>;
  let componentRef: ComponentRef<UserCardComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserCardComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(UserCardComponent);
    componentRef = fixture.componentRef;

    // Set signal inputs via setInput
    componentRef.setInput("id", "123");
    componentRef.setInput("name", "John Doe");

    fixture.detectChanges();
  });

  it("should display user name", () => {
    const el = fixture.nativeElement.querySelector("h3");
    expect(el.textContent).toContain("John Doe");
  });
});
```

---

## Key Decision Tables

### Signals vs RxJS

| Use Case                | Signals         | RxJS                             |
| ----------------------- | --------------- | -------------------------------- |
| Local component state   | Preferred       | Overkill                         |
| Derived/computed values | `computed()`    | `combineLatest` works            |
| Side effects            | `effect()`      | `tap` operator                   |
| HTTP requests           | No              | HttpClient returns Observable    |
| Event streams           | No              | `fromEvent`, operators           |
| Complex async flows     | No              | `switchMap`, `mergeMap`          |

### Pattern Do/Don't Summary

| Pattern              | Do                             | Don't                           |
| -------------------- | ------------------------------ | ------------------------------- |
| **State**            | Use Signals for local state    | Overuse RxJS for simple state   |
| **Components**       | Standalone with direct imports | Bloated SharedModules           |
| **Change Detection** | OnPush + Signals               | Default CD everywhere           |
| **Lazy Loading**     | `@defer` and `loadComponent`   | Eager load everything           |
| **DI**               | `inject()` function            | Constructor injection (verbose) |
| **Inputs**           | `input()` signal function      | `@Input()` decorator (legacy)   |
| **Zoneless**         | Default in Angular 21+         | Add `provideZonelessChangeDetection()` in v21+ |

---

## Common Troubleshooting

| Issue                          | Solution                                            |
| ------------------------------ | --------------------------------------------------- |
| Signal not updating UI         | Ensure `OnPush` + call signal as function `count()` |
| Hydration mismatch             | Check server/client content consistency             |
| Circular dependency            | Use `inject()` with `forwardRef`                    |
| Zoneless not detecting changes | Trigger via signal updates, not mutations           |
| SSR fetch fails                | Use `TransferState` or `withFetch()`                |
| `provideZonelessChangeDetection` warning in v21 | Remove call — zoneless is the default in v21+ |

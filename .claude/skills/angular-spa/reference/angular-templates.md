# Angular 21.x Code Templates

This reference contains all code templates for Angular SPA development with standalone components, signals, and lazy routing.

> **IMPORTANT:** Angular 21 is zoneless by default. Do NOT use `provideZoneChangeDetection()`, `zone.js`, or `CommonModule`. Do NOT set `standalone: true` in decorators (it is the default in v20+).

---

## Standalone Component Template

```typescript
import { Component, ChangeDetectionStrategy, signal, computed, inject } from '@angular/core';

@Component({
  selector: 'app-feature',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (loading()) {
      <div class="spinner">Loading...</div>
    } @else if (error()) {
      <p class="error">Something went wrong.</p>
    } @else {
      <div class="feature">
        @for (item of items(); track item.id) {
          <div class="feature__item">{{ item.name }}</div>
        } @empty {
          <p>No items found.</p>
        }
      </div>
    }
  `,
  styles: [`
    .feature { display: flex; flex-direction: column; gap: 1rem; }
    .feature__item { padding: 1rem; border: 1px solid #e0e0e0; border-radius: 8px; }
  `]
})
export class FeatureComponent {
  private service = inject(FeatureService);
  items = signal<Item[]>([]);
  loading = signal(true);
  error = signal(false);

  totalItems = computed(() => this.items().length);

  constructor() {
    this.service.getAll().subscribe({
      next: (data) => { this.items.set(data); this.loading.set(false); },
      error: () => { this.error.set(true); this.loading.set(false); },
    });
  }
}
```

**Key Points:**
- Do NOT set `standalone: true` — it is the default in Angular v20+
- Do NOT import `CommonModule` — control flow (`@if`, `@for`) is built-in
- Use `ChangeDetectionStrategy.OnPush` on all components
- Use `signal()` for reactive state, `computed()` for derived state
- Use `inject()` function for dependencies
- Use `@if`, `@for`, `@empty` control flow (not `*ngIf`/`*ngFor`)
- Inline template for small components, external for large ones
- Always handle loading, error, and empty states

---

## Service Template

```typescript
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class UserService {
  private http = inject(HttpClient);
  private baseUrl = `${environment.apiUrl}/api/v1/users`;

  getAll(): Observable<User[]> {
    return this.http.get<User[]>(this.baseUrl);
  }

  getById(id: string): Observable<User> {
    return this.http.get<User>(`${this.baseUrl}/${id}`);
  }

  create(dto: CreateUserDto): Observable<User> {
    return this.http.post<User>(this.baseUrl, dto);
  }

  update(id: string, dto: UpdateUserDto): Observable<User> {
    return this.http.patch<User>(`${this.baseUrl}/${id}`, dto);
  }

  delete(id: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${id}`);
  }
}
```

**Key Points:**
- Use `providedIn: 'root'` for singleton services
- Use `inject()` instead of constructor injection
- Return `Observable<T>` for async operations
- Use environment variables for API URLs
- Follow CRUD naming: `getAll`, `getById`, `create`, `update`, `delete`

### DTO vs Domain Model (Angular services)
// Services return domain models, not raw API shapes.
// If the API response shape differs from what components need, transform inside the service.
// For simple marketing site calls this is usually unnecessary.
// For complex data: define a separate ApiResponseDto interface, add a private mapper method.
// Components and templates NEVER import API response types directly.

---

## Lazy Routes Template

```typescript
// app.routes.ts
import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
  {
    path: 'dashboard',
    loadComponent: () => import('./features/dashboard/dashboard.component')
      .then(m => m.DashboardComponent),
    canActivate: [authGuard],
  },
  {
    path: 'users',
    loadChildren: () => import('./features/users/users.routes')
      .then(m => m.USER_ROUTES),
    canActivate: [authGuard],
  },
  {
    path: 'login',
    loadComponent: () => import('./features/auth/login.component')
      .then(m => m.LoginComponent),
  },
  { path: '**', redirectTo: 'dashboard' },
];
```

**Child Routes Example:**
```typescript
// features/users/users.routes.ts
import { Routes } from '@angular/router';

export const USER_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./user-list.component').then(m => m.UserListComponent),
  },
  {
    path: ':id',
    loadComponent: () => import('./user-detail.component').then(m => m.UserDetailComponent),
  },
];
```

**Key Points:**
- Use `loadComponent` for lazy-loaded standalone components
- Use `loadChildren` for feature route modules
- Use functional guards (`authGuard`, not class-based)
- Always handle wildcard route (`**`) as last route

---

## app.config.ts

```typescript
import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { routes } from './app.routes';
import { authInterceptor } from './core/interceptors/auth.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    provideHttpClient(withInterceptors([authInterceptor])),
  ],
};
```

**Key Points:**
- Angular 21 is zoneless by default — do NOT add `provideZoneChangeDetection()` or `provideZonelessChangeDetection()`
- Do NOT import or install `zone.js`
- Use `provideHttpClient(withInterceptors([...]))` for HTTP + functional interceptors
- Use `provideRouter(routes)` for routing configuration
- Add `provideAnimations()` only if using Angular animations

---

## Auth Interceptor

```typescript
import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { AuthService } from '../services/auth.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const token = inject(AuthService).getToken();
  if (token) {
    req = req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });
  }
  return next(req);
};
```

**Register in app.config.ts:**
```typescript
provideHttpClient(
  withInterceptors([authInterceptor]),
)
```

**Key Points:**
- Use functional interceptors (`HttpInterceptorFn`, not class-based)
- Use `inject()` to access services inside interceptor
- Use `req.clone()` to modify requests (requests are immutable)
- Register with `withInterceptors([...])` in `provideHttpClient`

---

## Auth Guard (Functional)

```typescript
import { CanActivateFn, Router } from '@angular/router';
import { inject } from '@angular/core';
import { AuthService } from '../services/auth.service';

export const authGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (authService.isAuthenticated()) {
    return true;
  }
  return router.createUrlTree(['/login']);
};
```

**Key Points:**
- Use `CanActivateFn` — not class-based guards
- Use `inject()` for dependencies
- Return `true`, `false`, or `UrlTree` for redirect

---

## Component Test Template

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideZonelessChangeDetection } from '@angular/core';
import { UserListComponent } from './user-list.component';

describe('UserListComponent', () => {
  let fixture: ComponentFixture<UserListComponent>;
  let component: UserListComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserListComponent],
      providers: [
        provideZonelessChangeDetection(),
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(UserListComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should display items', () => {
    const items = fixture.nativeElement.querySelectorAll('.feature__item');
    expect(items.length).toBeGreaterThanOrEqual(0);
  });
});
```

**Service Test Template:**
```typescript
import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideZonelessChangeDetection } from '@angular/core';
import { UserService } from './user.service';

describe('UserService', () => {
  let service: UserService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });
    service = TestBed.inject(UserService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should fetch users', () => {
    const mockUsers = [{ id: '1', name: 'Test' }];
    service.getAll().subscribe(users => {
      expect(users).toEqual(mockUsers);
    });
    const req = httpMock.expectOne('/api/v1/users');
    expect(req.request.method).toBe('GET');
    req.flush(mockUsers);
  });
});
```

**Key Points:**
- Import standalone component directly in `imports: [...]`
- Use `provideZonelessChangeDetection()` in TestBed (required for tests even though it's the app default)
- Use `await fixture.whenStable()` instead of `fixture.detectChanges()` for zoneless
- Use `provideHttpClientTesting()` for HTTP mocking
- Use `HttpTestingController` for service tests

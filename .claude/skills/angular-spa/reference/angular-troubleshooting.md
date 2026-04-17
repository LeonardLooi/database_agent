# Angular 21.x — Troubleshooting, CLI Commands & Best Practices

## Common Compilation Errors

**Error:** `NullInjectorError: No provider for HttpClient`
- **Fix:** Add `provideHttpClient()` to `app.config.ts` providers

**Error:** `NG0908: In this configuration Angular requires Zone.js`
- **Fix:** Remove `provideZoneChangeDetection()` from `app.config.ts` — Angular 21 is zoneless by default. Do NOT install `zone.js`.

**Error:** `Cannot find module './feature.component'`
- **Fix:** Ensure component is exported with `export class FeatureComponent`

**Error:** `ExpressionChangedAfterItHasBeenCheckedError`
- **Fix:** Use `ChangeDetectionStrategy.OnPush` and signals; avoid mutating state outside Angular's change detection cycle

## Runtime Errors

**Error:** Route not lazy loading
- **Fix:** Verify `loadComponent` returns a Promise; use dynamic import `() => import('./...')`

**Error:** Interceptor not firing
- **Fix:** Register with `provideHttpClient(withInterceptors([...]))` in `app.config.ts`

**Error:** Signal not updating UI
- **Fix:** Ensure you're calling `.set()` or `.update()`, not mutating signal value directly

**Error:** Guard not protecting route
- **Fix:** Add `canActivate: [guardFn]` to route config

**Error:** Blank screen after bootstrap
- **Fix:** Check browser console for errors. Common cause: using `provideZoneChangeDetection()` without `zone.js` installed. Remove it — Angular 21 is zoneless by default.

**Error:** TailwindCSS/daisyUI styles not applied (unstyled page)
- **Fix:** Angular's `@angular/build:application` builder only reads `.postcssrc.json` for PostCSS config. It **ignores** `postcss.config.js`. Create `.postcssrc.json` in the project root:
  ```json
  { "plugins": { "@tailwindcss/postcss": {} } }
  ```
  Also ensure global styles are in a `.css` file (not `.scss`) — Sass intercepts TailwindCSS 4.x directives. After changing the config, restart `ng serve`.

## Angular CLI Commands

```bash
# Generate component (standalone is the default — no flag needed)
ng generate component features/users/user-list

# Generate service
ng generate service core/services/user

# Generate guard (functional)
ng generate guard core/guards/auth --functional

# Run dev server
ng serve

# Build for production
ng build --configuration=production

# Run tests
ng test

# Run linter
ng lint
```

**Note:** Do NOT pass `--standalone` to `ng generate component` — standalone is the default since Angular v19 and the flag has been removed.

## Best Practices

- Always use `ChangeDetectionStrategy.OnPush` for performance
- Prefer signals over BehaviorSubject for component state
- Use `inject()` instead of constructor injection (modern Angular style)
- Use `input()` and `output()` functions instead of `@Input`/`@Output` decorators
- Lazy load all feature routes to reduce initial bundle size
- Use `track` in `@for` loops for performance with large lists
- Unsubscribe from observables using `takeUntilDestroyed()` or `async` pipe
- Write unit tests for all components and services
- Use environment files for API URLs and configuration
- Use daisyUI semantic colors — never hardcode hex values
- Follow BEM naming for custom CSS classes
- Keep components small and focused (Single Responsibility Principle)
- Do NOT set `standalone: true` in decorators — it is the default in Angular v20+
- Do NOT use `ngClass` or `ngStyle` — use `class` and `style` bindings
- Do NOT use `@HostBinding`/`@HostListener` — use the `host` object in the decorator
- All interactive elements must have loading, error, empty, and success states

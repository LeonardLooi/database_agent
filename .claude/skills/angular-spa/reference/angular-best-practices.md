# Angular & TypeScript Best Practices

## TypeScript
- Use strict type checking (`strict: true` in tsconfig)
- Prefer type inference when the type is obvious
- Avoid the `any` type; use `unknown` when type is uncertain

## Components
- Always use standalone components — do NOT set `standalone: true` in decorators (it is the default in Angular v20+)
- Use `input()` and `output()` functions instead of `@Input`/`@Output` decorators
- Use `signal()` for local state, `computed()` for derived state
- Set `changeDetection: ChangeDetectionStrategy.OnPush` in every `@Component` decorator
- Prefer inline templates for small components
- Do NOT use `@HostBinding`/`@HostListener` — use the `host` object in the decorator instead
- Do NOT use `ngClass` — use `class` bindings instead
- Do NOT use `ngStyle` — use `style` bindings instead
- Use `NgOptimizedImage` for all static images
- All interactive elements must have loading, error, empty, and success states

## Templates
- Use native control flow: `@if`, `@for`, `@switch`, `@defer` — never `*ngIf`, `*ngFor`, `*ngSwitch`
- Use `track` in `@for` loops for performance (e.g., `@for (item of items(); track item.id)`)
- Keep templates simple; avoid complex logic
- Use the async pipe to handle observables in templates
- Do not write arrow functions in templates (not supported)
- Do not assume globals like `new Date()` are available in templates

## State Management
- Use signals for local component state
- Use `computed()` for derived state
- Keep state transformations pure and predictable
- Do NOT use `mutate` on signals — use `update` or `set` instead

## Services
- Design services around a single responsibility
- Use `providedIn: 'root'` for singleton services
- Use the `inject()` function instead of constructor injection

## Forms
- Prefer Reactive forms over Template-driven forms

## Zoneless (Angular 21 default)
- Angular 21 is zoneless by default — do NOT add `provideZoneChangeDetection()` or import `zone.js`
- Do NOT install `zone.js` as a dependency
- Do NOT add `provideZonelessChangeDetection()` either — it is the default and unnecessary in v21+

## Pitfalls

### Angular 21+ is Zoneless — Never Import zone.js

Angular 21 uses signal-based change detection. Zone.js must NOT be used.

❌ FORBIDDEN in Angular 21+:
- `import 'zone.js'` anywhere (main.ts, polyfills, angular.json)
- `provideZoneChangeDetection()` in app.config.ts
- `NgZone` injection

✅ CORRECT bootstrap (Angular 21):
```typescript
// main.ts
bootstrapApplication(AppComponent, appConfig);

// app.config.ts
export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),
    provideHttpClient(),
    // NO provideZoneChangeDetection()
  ],
};
```

- Use `ChangeDetectionStrategy.OnPush` on all components
- Use `signal()`, `computed()`, `effect()` for reactive state
- Use `@if`, `@for`, `@switch` control flow blocks (NOT *ngIf, *ngFor)

## Accessibility (WCAG 2.1 AA minimum)
- Must pass all AXE checks
- Must follow WCAG AA minimums: focus management, color contrast, ARIA attributes
- Text contrast >= 4.5:1, UI component contrast >= 3:1
- Touch targets >= 44x44px on mobile
- All icon-only buttons need `aria-label`
- Keyboard navigable: Tab, Enter, Space, Arrow keys
- `aria-live="polite"` for dynamic content updates
- `prefers-reduced-motion` respected for all animations

## Testing
- Use `provideZonelessChangeDetection()` in TestBed (required for tests even though it's the app default)
- Use `await fixture.whenStable()` instead of `fixture.detectChanges()` for zoneless
- Use `provideHttpClient()` and `provideHttpClientTesting()` for HTTP mocking
- See `angular-templates.md` for full component and service test templates

> **Canonical source:** https://angular.dev/style-guide — PropertyHarbor strictly follows this guide. When in doubt, the official style guide takes precedence over any convention listed here.

# Angular Conventions & Project Structure

## Style Guide Quick Reference (must-follow rules)

Source: https://angular.dev/style-guide

### File Naming

- Separate words in file names with hyphens: `user-profile.component.ts`, not `UserProfile.component.ts`
- File name must reflect the primary class/concept — avoid `helpers.ts`, `utils.ts`, `common.ts`
- Test files use `.spec.ts` matching the source: `user-profile.component.spec.ts`
- Component file group shares the same base name: `user-profile.ts`, `user-profile.html`, `user-profile.css`
- Named pattern: `<feature>.<type>.ts` — e.g. `hero-list.component.ts`, `auth.service.ts`, `app.routes.ts`

### Class Naming

- Components: `UpperCamelCase` + `Component` suffix — `UserProfileComponent`
- Services: `UpperCamelCase` + `Service` suffix — `AuthService`, `UserService`
- Directives: `UpperCamelCase` + `Directive` suffix — `TooltipDirective`
- Pipes: `UpperCamelCase` + `Pipe` suffix — `DateFormatPipe`
- Guards: `UpperCamelCase` + `Guard` suffix — `AuthGuard`
- Interfaces: `UpperCamelCase`, no `I` prefix — `User`, not `IUser`
- Enums: `UpperCamelCase` — `UserRole`

### One Component Per File

Each file must focus on a single concept: one component, one service, one directive, one pipe per file. Never combine multiple components in the same `.ts` file.

### Folder / Feature Structure

Organize by **feature area**, not by code type. Avoid flat `components/`, `directives/`, `services/` directories.

```
src/app/
├── core/             # Singletons: auth, interceptors, guards (imported once in AppModule/config)
├── shared/           # Reusable components, pipes, directives used across features
└── features/
    ├── show-times/   # Feature folder — all related files co-located
    │   ├── show-times.component.ts
    │   ├── show-times.component.html
    │   ├── show-times.component.css
    │   └── show-times.component.spec.ts
    └── reserve-tickets/
```

Co-locate closely related files (component + template + styles + spec) in the same directory.

### `@Injectable` / Dependency Injection

- Use `providedIn: 'root'` on `@Injectable` for singleton services — avoids manual registration
- Prefer the `inject()` function over constructor parameter injection for clarity and tree-shakability
- Group injected dependencies at the top of class declarations before methods

### Selector / Prefix Conventions

- Component selectors: use a consistent app-specific prefix (e.g., `app-`, `ph-` for PropertyHarbor) in `kebab-case`
- Directive selectors: `camelCase` attribute selector with prefix: `[phTooltip]`
- Never use generic selectors like `div`, `span`, `button` as component selectors

### Class Member Organization

Angular-specific members first: inputs → outputs → queries → injected deps → lifecycle hooks → public methods → protected/private methods.

Use `protected` for template-only members; `readonly` for properties initialized by Angular (`input()`, `model()`, `viewChild()`).

### Event Handler Naming

Name handlers for the **action performed**, not the triggering event: `saveUserData()`, not `handleClick()` or `onButtonClick()`.

## TypeScript

- Use strict type checking (`strict: true` in tsconfig)
- Prefer type inference when the type is obvious
- Avoid the `any` type; use `unknown` when type is uncertain

## Zoneless (Angular 21 default)

- Angular 21 is zoneless by default — do NOT add `provideZoneChangeDetection()` or import `zone.js`
- Do NOT install `zone.js` as a dependency
- Do NOT add `provideZonelessChangeDetection()` either — it is the default and unnecessary in v21+

## Components

- Standalone components (no NgModules unless legacy) — do NOT set `standalone: true` in decorators (default in v20+)
- `ChangeDetectionStrategy.OnPush` on all components
- Prefer inline templates for small components, external for large ones
- Use `signal()`, `computed()`, `effect()` for component state — do NOT use `mutate` on signals
- Use `inject()` function over constructor injection
- Use `input()` and `output()` functions — NOT `@Input`/`@Output` decorators
- Use `NgOptimizedImage` for all static images
- Do NOT use `@HostBinding`/`@HostListener` — use the `host` object in the decorator
- Do NOT use `ngClass`/`ngStyle` — use `class`/`style` bindings
- All interactive elements must have loading, error, empty, and success states

### Component Classification (Smart vs Dumb)

Every component must be classified before implementation:

| Type | Location | Can inject? | Can own state? | Receives data via |
|------|----------|-------------|----------------|-------------------|
| **Smart (Container)** | `features/` | YES | YES | Services, `resource()` |
| **Dumb (Presentational)** | `shared/components/` | NO | Local UI only | `input()` only |

Rule: If a component lives in `shared/components/`, it MUST have zero `inject()` calls.
Full pattern guide: `smart-dumb-components.md`

## Templates

- Use native control flow: `@if`, `@for`, `@switch`, `@defer` — never `*ngIf`, `*ngFor`, `*ngSwitch`
- Use `track` in `@for` loops (not `trackBy`)
- Keep templates simple; avoid complex logic
- Do not write arrow functions in templates (not supported)
- Do not assume globals like `new Date()` are available in templates
- Use the async pipe for observables in templates

## Services & Routing

- Design services around a single responsibility
- Use `providedIn: 'root'` for singleton services
- Use `inject()` instead of constructor injection
- Use `HttpClient` with RxJS operators — return `Observable<T>` from services
- Feature routes as separate `*.routes.ts` files with `loadComponent` / `loadChildren`
- Use functional guards (`CanActivateFn`) and interceptors (`HttpInterceptorFn`)

## Forms

- Prefer Reactive forms over Template-driven forms

## Styling

- **daisyUI semantic colors only** — never hardcode hex values (`bg-primary`, not `bg-[#3b82f6]`)
- **TailwindCSS 4.x** uses CSS-native config (`@theme {}` in CSS, no `tailwind.config.js`)
- **PostCSS config** must be `.postcssrc.json` — Angular's `@angular/build:application` builder ignores `postcss.config.js`
- **Global styles** must be `.css` (not `.scss`) — Sass intercepts TailwindCSS 4.x directives (`@import`, `@theme`, `@plugin`)
- **Mobile-first** — start with base styles, add `sm:`, `md:`, `lg:` breakpoints
- **Spacing**: 4px base unit (4, 8, 12, 16, 24, 32, 48, 64)
- **BEM Naming** for custom CSS: `.block__element--modifier`

### Machine Enforcement

Design rules are enforced automatically:

| Rule File | What It Catches | Action |
|---|---|---|
| `hookify.design-no-hex-angular.local.md` | `bg-[#hex]`, `text-[#hex]`, `color: #hex` in `src/**/*.{html,scss,css,ts}` | warn |
| `hookify.design-no-raw-spacing-angular.local.md` | `mt-3`, `px-4`, `gap-2` numeric utilities in `src/**/*.html` | warn |

Lint commands:
- `ng lint` — ESLint rules including Angular-specific checks
- `/lint-design-system` — Orchestrator scanning for hardcoded colors and raw spacing

Scope: `src/app/` only. Test files, generated code, and node_modules are excluded.

Exception marker: `<!-- ignore-design: [reason] -->` in templates, `// ignore-design: [reason]` in TypeScript/SCSS.

## Accessibility (WCAG 2.1 AA)

- Must pass all AXE checks
- Focus management, color contrast, ARIA attributes
- Text contrast >= 4.5:1, UI component contrast >= 3:1
- Touch targets >= 44x44px on mobile
- All icon-only buttons need `aria-label`
- Keyboard navigable: Tab, Enter, Space, Arrow keys
- `aria-live="polite"` for dynamic content updates
- `prefers-reduced-motion` respected for all animations

## Testing

- Use `provideZonelessChangeDetection()` in TestBed (required for tests)
- Use `await fixture.whenStable()` instead of `fixture.detectChanges()`
- Use `provideHttpClient()` and `provideHttpClientTesting()` for HTTP mocking

## Design Principles

1. **Visual hierarchy** — size, color, spacing, contrast guide attention
2. **Consistency** — reuse daisyUI components, don't invent custom variants
3. **Feedback** — instant response (<100ms hover/click), loading states for >300ms async
4. **Progressive disclosure** — primary actions visible, secondary behind menus/accordions
5. **Affordance** — buttons look clickable, inputs have borders, interactive elements change cursor

## Key Patterns

| Pattern | Description |
|---------|-------------|
| **Standalone Component** | Default in Angular v20+ — do NOT set `standalone: true` in decorators |
| **Signals** | Use `signal()`, `computed()`, `effect()` for reactive state |
| **input() / output()** | Use function-based `input()` and `output()` — not `@Input`/`@Output` decorators |
| **inject() Function** | Prefer `inject()` over constructor injection |
| **OnPush Change Detection** | Use `ChangeDetectionStrategy.OnPush` on all components |
| **Zoneless** | Angular 21 default — no `zone.js`, no zone providers needed |
| **Lazy Loading** | Use `loadComponent` for routes, `loadChildren` for feature routes |
| **Functional Interceptors** | Use `HttpInterceptorFn` instead of class-based interceptors |
| **Functional Guards** | Use `CanActivateFn` instead of class-based guards |
| **Control Flow Syntax** | Use `@if`, `@for`, `@switch`, `@defer` — never `*ngIf`/`*ngFor` |
| **RxJS Observables** | Return `Observable<T>` from services, subscribe in components |

## Folder Structure

```
src/app/
├── core/               # Singletons: auth, interceptors, guards
│   ├── services/
│   ├── interceptors/
│   └── guards/
├── shared/             # Reusable components, pipes, directives
│   ├── components/
│   ├── pipes/
│   └── directives/
├── features/           # Feature modules (lazy loaded)
│   ├── dashboard/
│   │   ├── dashboard.component.ts
│   │   ├── dashboard.component.html
│   │   ├── dashboard.component.scss
│   │   └── dashboard.component.spec.ts
│   ├── users/
│   │   ├── users.routes.ts
│   │   ├── user-list.component.ts
│   │   └── user-detail.component.ts
│   └── settings/
├── app.ts
├── app.html
├── app.routes.ts
└── app.config.ts
```

## Common Commands

```bash
ng serve                             # Dev server at localhost:4200
ng build --configuration=production  # Production build
ng test                              # Unit tests (Karma/Jest)
ng generate component <name>         # Scaffold component
ng generate service <name>           # Scaffold service
ng lint                              # Run linter
npx tsc --noEmit                     # Type check only
```

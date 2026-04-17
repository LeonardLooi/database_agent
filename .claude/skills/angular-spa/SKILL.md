---
name: angular-spa
description: "Angular 21.x SPA development skill with TailwindCSS 4.x and daisyUI 5.5.5. Use when building Angular standalone components, services, lazy-loaded routes, unit tests, or creating UI with TailwindCSS + daisyUI. Covers component scaffolding, UI/UX design, accessibility audits, and design systems."
allowed-tools: Read, Edit, Write, Glob, Grep, Bash, WebFetch, mcp__context7__resolve-library-id, mcp__context7__query-docs
metadata:
  triggers: Angular, Angular 21, standalone components, Angular SPA, TailwindCSS, daisyUI, Angular component, Angular service, lazy-loaded route, Angular testing
  related-skills: frontend-design, ui-standards-tokens, browser-testing, openapi-spec-generation
  domain: frontend
  role: specialist
  scope: implementation
  output-format: code
last-reviewed: "2026-03-14"
---

## Iron Law

**NO ANGULAR CODE WITHOUT READING `reference/angular-conventions.md` FIRST — conventions, folder structure, and daisyUI token rules are all there**

**STYLE LAW:** Strictly follow https://angular.dev/style-guide for ALL naming, file structure, and code organization. See `reference/angular-conventions.md` for the quick reference.

**ANIMATION LAW (web/property-harbor):** Use `@angular/animations` for ALL interactive animations. Never raw CSS transitions on stateful elements. See `reference/angular-animations.md`.

# Angular 21.x SPA Development Skill

> **Tech Stack**: Angular 21+, TailwindCSS 4.x, daisyUI 5.5.5

## Conventions & Structure

> For code conventions, styling rules, design principles, key patterns, folder structure, and common commands, read `reference/angular-conventions.md`

## Documentation Sources

Before generating code, consult these sources for current syntax and APIs:

| Source | URL / Tool | Purpose |
|--------|-----------|---------|
| Angular v21 | `angular-cli` MCP (ng mcp) | Workspace-aware help, schematics, builds, best practices |
| Angular v21 | `https://angular.dev/assets/context/llms-full.txt` | Static docs bundle — API reference, deprecated features |
| daisyUI v5.5.5 | `https://daisyui.com/llms.txt` | Component reference, color system, themes |
| TailwindCSS / RxJS | `Context7` MCP | Latest syntax, utilities, operators |
| Angular + Tailwind official guide | `https://angular.dev/guide/tailwind` | Canonical install steps, `ng add tailwindcss`, build integration |

Cross-check all Angular APIs and CLI flags against fetched docs — do NOT use deprecated or removed features.

> For Angular & TypeScript best practices, read reference/angular-best-practices.md

## Quick Scaffold — New Angular Project

```bash
npx @angular/cli@latest new my-app --style=scss --ssr=false
cd my-app
```

Do NOT pass `--standalone` (removed/default since v19). Verify flags against fetched docs.

## Before Writing Any UI Code

Before creating or modifying any component template or styles:

1. **Read `reference/daisyui-v5-components.md`** — for semantic color tokens and component patterns
2. **Read `reference/tailwind-v4-config.md`** — for TailwindCSS 4.x setup constraints
3. **Verify token awareness** — can you name the color token (`bg-primary`, `text-base-content`), spacing base (4px), and typography approach you will use?
4. If not → read the reference files before writing any template or style code
5. For accessibility: read `reference/accessibility-checklist.md` before adding interactive elements

## Process

1. **Understand Requirements** — Clarify feature scope, API endpoints, data models, and UI requirements
2. **Scaffold Structure** — Create feature folder under `src/app/features/<feature-name>/`
3. **Generate Component** — Read `reference/angular-templates.md` for templates; create with signals-based state
4. **Create Service** — Read `reference/angular-templates.md` for service template; implement API calls with HttpClient + RxJS
5. **Configure Routes** — Add lazy-loaded route using `loadComponent` in `app.routes.ts` or feature routes
6. **Write Tests** — Read `reference/angular-templates.md` for test templates; write unit tests with zoneless TestBed
7. **Style Component** — Use daisyUI components + TailwindCSS utilities; fallback to SCSS with BEM naming
8. **Verify Build** — Run `ng build` to ensure no compilation errors

## Reference Files

Detailed patterns are in `reference/`:

### Angular Best Practices & Code Templates
- `angular-best-practices.md` — TypeScript, component, template, state management, services, forms, zoneless, accessibility, and testing best practices
- `angular-templates.md` — Standalone component, service, lazy routes, app.config, interceptor, guard, and test templates
- `angular-troubleshooting.md` — Common errors (NG0908, NullInjectorError, blank screen), CLI commands, and best practices

### UI/UX & Design System
- `tailwind-v4-config.md` — TailwindCSS 4.x setup, breaking changes from v3
- `daisyui-v5-components.md` — Full component reference, color system, themes, quick setup patterns
- `angular-forms-fields.md` — Input fields, select, textarea, checkbox, radio patterns
- `angular-forms-validation.md` — Validation patterns, error messages, async validators
- `angular-forms-advanced.md` — Multi-step forms, dynamic fields, form arrays
- `angular-ui-tables.md` — Table and grid patterns with sorting, filtering, pagination
- `angular-ui-lists.md` — List, card, and feed UI patterns
- `angular-ui-navigation.md` — Navigation, breadcrumbs, tabs, and sidebar patterns
- `angular-ui-feedback-components.md` — Toasts, dialogs, themes, error handling, utilities
- `accessibility-checklist.md` — WCAG 2.1 AA checklist, ARIA patterns, test protocol
- `angular-aria.md` — Angular CDK accessible headless components (FocusTrap, ListKeyManager, LiveAnnouncer, Accordion, Combobox)
- `component-harnesses.md` — Angular CDK component harnesses for stable UI testing
- `testing-vitest.md` — Vitest setup, zoneless TestBed, testing Signals and resource(), migration from Karma
- `e2e-cypress.md` — Cypress E2E setup, component testing, custom commands, data-cy convention
- `smart-dumb-components.md` — Smart (container) vs Dumb (presentational) component pattern, decision tree, signal-based examples, hard rules, file location enforcement
- `angular-animations.md` — Angular Animations API (`animate.enter`/`animate.leave`, `trigger()`, `state()`, `keyframes()`, `stagger()`), timing standards, PropertyHarbor animation rules
- `user-research.md` — Persona templates, journey mapping, usability testing, SUS survey

## Anti-Patterns — What to Avoid

### Architecture
- **NEVER** create `NgModule` — Angular 21 is fully standalone; all components, pipes, and directives are standalone by default
- **NEVER** call HTTP or business logic directly in a component — delegate to an injectable service

### State & Change Detection
- **NEVER** use `@Input()` / `@Output()` decorators for new code — use `input()`, `output()`, and `model()` signals (Angular 21 standard)
- **NEVER** use `BehaviorSubject` for component state — use `signal()` and `computed()`
- **NEVER** rely on default change detection (`ChangeDetectionStrategy.Default`) — always use `OnPush` with signals

### Templates
- **NEVER** use `*ngIf`, `*ngFor`, `*ngSwitch` structural directives — use `@if`, `@for`, `@switch` control flow (Angular 17+, standard in v21)
- **NEVER** import `CommonModule` in standalone components — it is a compatibility shim; import nothing or use control flow syntax

### Dependency Injection
- **NEVER** inject services via constructor parameters — use the `inject()` function in Angular 21
- **NEVER** import `HttpClientModule` — use `provideHttpClient()` in `app.config.ts` (functional API)

### Subscriptions & Memory
- **NEVER** subscribe manually without `takeUntilDestroyed(destroyRef)` — memory leaks in long-lived components
- **NEVER** use `ngOnDestroy` to unsubscribe — use `DestroyRef` and `takeUntilDestroyed()` instead

### DOM & Styling
- **NEVER** use `document.getElementById` or direct DOM manipulation — use `viewChild()` signal or Angular CDK
- **NEVER** use inline `style=""` attributes — use TailwindCSS utilities or SCSS

### Design Tokens
- **NEVER** use `style="color: #3B82F6"` inline — use `class="text-primary"`
- **NEVER** use hardcoded Tailwind primitive color classes like `bg-blue-500` — use semantic `bg-primary`
- **NEVER** use `style="padding: 16px"` — use `class="p-4"`
- **NEVER** use `style="font-size: 16px"` — use `class="text-base"`

## Error Handling

**Build failures (`NG0908`, `NullInjectorError`)**: Read `reference/angular-troubleshooting.md` for common errors and fixes.

**TailwindCSS not applied**: Verify `.postcssrc.json` exists (not `postcss.config.js`) and global styles use `.css` (not `.scss`).

**Blank screen on load**: Check browser console for lazy-loading errors. Verify route paths and `loadComponent` imports.

## Common Commands

```bash
ng serve                          # Dev server (http://localhost:4200)
ng test --watch=false             # Run unit tests once (no watch)
ng test                           # Run unit tests in watch mode
ng build                          # Production build
ng lint                           # ESLint check
ng generate component features/my-feature/my-component --standalone   # Scaffold component
ng generate service features/my-feature/my-service                    # Scaffold service
```

## Design Token System

Full token definitions are in `.claude/skills/ui-standards-tokens/reference/ui-design-tokens.md`. This section covers Angular-specific usage.

### Token Hierarchy (3 Tiers)

```
Primitive → Semantic → Component
```

```css
/* Primitive */
--color-blue-500: #3B82F6;

/* Semantic */
--color-primary: var(--color-blue-500);

/* Component */
--button-bg-primary: var(--color-primary);
```

Never use primitive tokens directly in component CSS. Components reference component tokens; component tokens reference semantic tokens.

### daisyUI Token Mapping

| Category | daisyUI / Tailwind classes |
|---|---|
| Colors | `bg-primary`, `text-base-content`, `bg-base-100/200/300`, `text-error`, `bg-success` |
| Spacing | `p-2` = 8px, `p-4` = 16px, `p-6` = 24px (4px base scale) |
| Typography | `text-sm`, `text-base`, `text-lg`, `font-semibold`, `font-bold` |
| Borders | `rounded-sm`, `rounded-md`, `rounded-lg`, `rounded-full`, `border border-base-300` |
| Shadows | `shadow-sm`, `shadow-md`, `shadow-xl` |
| Motion | `transition-all duration-200` |
| Z-index | custom CSS vars: `--z-dropdown: 1000`, `--z-modal: 1050`, `--z-tooltip: 1070` |

### Theme Switching

```typescript
// theme.service.ts
import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  setTheme(theme: 'light' | 'dark' | 'custom'): void {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }

  getTheme(): string {
    return localStorage.getItem('theme') ?? 'light';
  }
}
```

daisyUI v5.5.5 uses the `data-theme` attribute on `<html>`. All daisyUI semantic classes switch automatically — no additional CSS is needed per component.

## Verify

```bash
ng serve                   # Starts at http://localhost:4200 — no errors in terminal
ng test --watch=false      # All unit tests pass
ng build                   # Exit code 0, no NG build errors
npx ng lint                # Zero lint violations
```

- [ ] App serves without console errors
- [ ] All Vitest unit tests pass (>90% coverage enforced)
- [ ] Production build completes successfully
- [ ] No TypeScript errors (`tsc --noEmit`)
- [ ] Shared components in `shared/components/` have zero `inject()` calls (dumb rule)
- [ ] Service-injecting components live in `pages/` or `features/` (smart rule)

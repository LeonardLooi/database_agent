---
name: web-performance-optimization
description: "Optimize Angular 21.x web application performance including Core Web Vitals, bundle size, lazy loading with @defer, NgOptimizedImage, OnPush+Signals, SSR TransferState, and Angular CLI build optimization. Use when diagnosing slow Angular apps, preparing for Lighthouse audits, or reducing bundle size — always measure with profiling tools before making changes."
risk: low
source: community (adapted for Angular 21.x)
date_added: "2026-02-27"
updated: "2026-03-15"
last-reviewed: "2026-03-15"
allowed-tools: "Read, Grep, Glob, Bash, Edit, Write"
---

## Iron Law

**NO PERFORMANCE OPTIMIZATION WITHOUT MEASURING FIRST — run Lighthouse and `ng build --stats-json` before writing a single optimization**

Profile before optimizing. Every change must have a before/after metric. Do not optimize based on guesswork.

# Web Performance Optimization — Angular 21.x

## Overview

Help developers optimize Angular 21.x SPA performance to improve user experience, SEO rankings, and Core Web Vitals scores. This skill provides systematic approaches to measure, analyze, and improve loading speed, runtime performance, and bundle size — all grounded in Angular-native patterns (signals, `@defer`, `NgOptimizedImage`, lazy routes, SSR TransferState).

## When to Use This Skill

- Angular SPA loads slowly or scores poorly on Lighthouse
- Optimizing for Core Web Vitals (LCP, FID/INP, CLS)
- Reducing JavaScript bundle size output by `ng build`
- Improving Time to Interactive (TTI) or First Contentful Paint (FCP)
- Optimizing images and assets inside Angular templates
- Implementing lazy loading via routes or `@defer` blocks
- Debugging Angular change detection performance
- Preparing for performance audits on an Angular production build

## How It Works

### Step 1: Measure Current Performance

Establish baseline metrics before touching any code:

- Run Lighthouse audit (Chrome DevTools → Lighthouse tab)
- Measure Core Web Vitals: LCP, INP (replaced FID in 2024), CLS
- Inspect Angular bundle with `ng build --configuration=production --stats-json`
- Analyze bundle composition: `npx webpack-bundle-analyzer dist/browser/stats.json`
- Check network waterfall in Chrome DevTools → Network tab
- Profile change detection with Angular DevTools browser extension

### Step 2: Identify Issues

Angular-specific performance bottlenecks to look for:

- Large initial bundle — missing lazy routes or barrel file imports pulling everything in
- Default change detection (`ChangeDetectionStrategy.Default`) triggering excessive re-renders
- `BehaviorSubject` + `async` pipe causing unnecessary subscriptions instead of signals
- Images without `ngSrc` (NgOptimizedImage) missing auto-sizing and LCP hints
- Below-fold heavy components not wrapped in `@defer` blocks
- Double HTTP fetches in SSR (server + client both calling the same endpoint) — missing TransferState
- Third-party scripts loaded synchronously in `index.html`

### Step 3: Prioritize Optimizations

Focus on highest-impact Angular improvements first:

1. **Critical rendering path** — `NgOptimizedImage` with `priority` on LCP image, `<link rel="preload">` for fonts
2. **Bundle size** — lazy routes (`loadComponent`/`loadChildren`), `@defer` for below-fold components
3. **Runtime rendering** — `OnPush` + signals on all components, eliminate `Default` change detection
4. **Image pipeline** — convert to AVIF/WebP, serve responsive srcsets via `NgOptimizedImage`
5. **SSR double-fetch** — TransferState to hydrate state from server render without re-fetching

### Step 4: Implement Optimizations

Apply improvements in priority order — measure after each step.

### Step 5: Verify Improvements

- Re-run Lighthouse — compare scores before/after
- Re-run `ng build --stats-json` — compare bundle sizes
- Verify no layout shifts introduced (Chrome DevTools → Rendering → Layout Shift Regions)
- Test on throttled mobile: Chrome DevTools → Network 3G + CPU 4x slowdown
- Monitor INP in PageSpeed Insights with real-user data after deploy

---

## Examples

> See [references/optimization-checklists.md](references/optimization-checklists.md) for full worked examples with before/after code and measured results.

- **Example 1:** Fixing Core Web Vitals (LCP, INP, CLS) — NgOptimizedImage, OnPush+Signals, skeleton loaders
- **Example 2:** Reducing bundle size 59% — dependency replacement, lazy routes, `@defer`, build budgets
- **Example 3:** Image pipeline (AVIF/WebP with `sharp`) + CDN loader configuration

---

## Best Practices

### Do This

- **Measure First** — always run Lighthouse and `ng build --stats-json` before any optimization
- **OnPush Everywhere** — every component must declare `ChangeDetectionStrategy.OnPush`
- **Signals for State** — use `signal()` and `computed()` instead of `BehaviorSubject` + `async` pipe
- **Lazy Routes** — use `loadComponent`/`loadChildren` for every feature — nothing should be eagerly imported in `app.routes.ts`
- **@defer for Below-Fold** — any component not visible on first paint belongs in an `@defer (on viewport)` block
- **NgOptimizedImage** — replace every `<img>` in Angular templates with `ngSrc`; never bypass it
- **Build Budgets** — set `maximumWarning: 500kb` / `maximumError: 1mb` in `angular.json` so CI fails before a bloated build ships
- **Preload Critical Resources** — `<link rel="preload">` for critical fonts; `priority` attribute on LCP image
- **TransferState in SSR** — prevent double HTTP fetch by serializing API responses on the server and rehydrating on the client
- **Use CDN** — serve `dist/browser/` from a CDN with immutable cache headers

### Do Not Do This

- **Do not use `ChangeDetectionStrategy.Default`** — this is the single largest Angular runtime performance killer
- **Do not import barrel files (`index.ts`)** in feature modules — they pull in everything, killing tree shaking
- **Do not lazy-load too granularly** — chunks under 10KB create more HTTP overhead than they save; colocate small components
- **Do not block rendering** — no synchronous `<script>` in `index.html`; use `defer` or post-bootstrap dynamic injection
- **Do not skip `width`/`height`** on `ngSrc` images — NgOptimizedImage will throw in dev mode, and CLS will spike in prod
- **Do not optimize without evidence** — profile first with Chrome DevTools and Angular DevTools; fix the proven bottleneck

---

## Common Pitfalls

### Problem: Good Desktop Score, Poor Mobile Score
**Symptoms:** Lighthouse passes on desktop, fails on mobile throttling
**Solution:**
- Test with CPU 4x slowdown + 3G in Chrome DevTools
- Check INP: Angular Default change detection collapses on slow CPUs — switch all components to OnPush + signals
- Remove `@defer` triggers that never fire on mobile (e.g., hover-based triggers on touch devices)
```bash
lighthouse https://yoursite.com --throttling.cpuSlowdownMultiplier=4 --preset=desktop
```

### Problem: Bundle Size Exceeds angular.json Budget
**Symptoms:** `ng build` exits with "ERROR: bundle initial exceeded maximum budget"
**Solution:**
- Run bundle analyzer to find the culprit: `npx webpack-bundle-analyzer dist/browser/stats.json`
- Convert eager feature imports to lazy routes
- Replace heavy libraries (moment → date-fns, full lodash → lodash-es cherry-picks)
- Wrap heavy components in `@defer`
```bash
ng build --configuration=production --stats-json
npx webpack-bundle-analyzer dist/browser/stats.json
```

### Problem: Images Cause Layout Shifts (High CLS)
**Symptoms:** CLS > 0.1 in Lighthouse, content jumps on load
**Solution:**
- Use `ngSrc` — NgOptimizedImage requires `width`/`height` and enforces them at build time
- For dynamic image lists, render skeleton placeholders at the correct height before data arrives
```css
/* Prevent CLS on any image not using NgOptimizedImage */
img {
  aspect-ratio: attr(width) / attr(height);
  width: 100%;
  height: auto;
}
```

### Problem: Slow TTFB with Angular SSR
**Symptoms:** Time to First Byte > 600ms, server HTML arrives late
**Solution:**
- Ensure API responses are cached server-side (Redis, CDN edge cache)
- Use `TransferState` to avoid re-fetching data the server already fetched
- Enable incremental hydration with `withIncrementalHydration()` — defer hydration of below-fold components
```typescript
// app.config.ts
import { provideClientHydration, withIncrementalHydration } from '@angular/platform-browser';

export const appConfig: ApplicationConfig = {
  providers: [
    provideClientHydration(withIncrementalHydration())
  ]
};
```

### Problem: SSR Double HTTP Fetch
**Symptoms:** Network tab shows the same API call twice (once server, once client)
**Solution:** Use TransferState — serialize data on the server, read it on the client without re-fetching
```typescript
// product.service.ts
import { Injectable, inject, PLATFORM_ID } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { TransferState, makeStateKey } from '@angular/core';
import { isPlatformServer } from '@angular/common';
import { Observable, of } from 'rxjs';
import { tap } from 'rxjs/operators';

const PRODUCTS_KEY = makeStateKey<Product[]>('products');

@Injectable({ providedIn: 'root' })
export class ProductService {
  private http = inject(HttpClient);
  private transferState = inject(TransferState);
  private platformId = inject(PLATFORM_ID);

  getProducts(): Observable<Product[]> {
    if (this.transferState.hasKey(PRODUCTS_KEY)) {
      const products = this.transferState.get(PRODUCTS_KEY, []);
      this.transferState.remove(PRODUCTS_KEY);
      return of(products);
    }

    return this.http.get<Product[]>('/api/products').pipe(
      tap(products => {
        if (isPlatformServer(this.platformId)) {
          this.transferState.set(PRODUCTS_KEY, products);
        }
      })
    );
  }
}
```

---

## Performance Checklist

> See [references/optimization-checklists.md](references/optimization-checklists.md) for the full checklist (Angular Architecture, Bundle Size, Images, CSS, Core Web Vitals targets, SSR).

**Critical items:**
- [ ] `ChangeDetectionStrategy.OnPush` on ALL components — no exceptions
- [ ] All feature routes use `loadComponent` or `loadChildren`
- [ ] LCP image has `priority` attribute; all other `ngSrc` images do not
- [ ] `TransferState` used for all SSR API responses

---

## Performance Tools

> See [references/optimization-checklists.md](references/optimization-checklists.md) for full tool list (Measurement, Bundle Analysis, Image Optimization, Monitoring).

- **Lighthouse** — Chrome DevTools → Lighthouse tab
- **Angular DevTools** — Component tree profiler, change detection inspector
- `ng build --configuration=production --stats-json` + `npx webpack-bundle-analyzer dist/browser/stats.json`

---

## Related Skills

- `angular-spa` — Angular component scaffolding, lazy routing, and daisyUI styling
- `angular-best-practices` — OnPush, signals, rendering performance, and SSR hydration patterns
- `angular` — Angular 21.x core API reference: Signals, `@defer`, TransferState, incremental hydration
- `browser-testing` — Chrome DevTools performance profiling via MCP; record traces, inspect long tasks
- `systematic-debugging` — Root-cause methodology for performance regressions

---

## Additional Resources

- [NgOptimizedImage Guide](https://angular.dev/guide/image-optimization) — official directive reference
- [@defer Blocks](https://angular.dev/guide/defer) — all trigger types (`on viewport`, `on idle`, `on interaction`, `when`)
- [Angular SSR](https://angular.dev/guide/ssr) — TransferState, incremental hydration, server rendering
- [Core Web Vitals](https://web.dev/vitals/) — LCP, INP, CLS definitions and thresholds
- [Web.dev Performance](https://web.dev/performance/) — General web performance techniques

---

**Key principle:** Measure before optimizing. `ng build --stats-json` + `webpack-bundle-analyzer` takes 2 minutes and reveals exactly where your bundle weight is — every other optimization is guesswork without it.

> **Official Angular+Tailwind guide:** https://angular.dev/guide/tailwind

# TailwindCSS v4.x Configuration

## Angular Official Setup (from angular.dev)

Angular's official guide (https://angular.dev/guide/tailwind) recommends:

### Automated Setup (recommended)

```bash
ng add tailwindcss
```

This single command installs dependencies, creates `.postcssrc.json`, and imports Tailwind into your styles automatically. Use this for new projects.

### Manual Setup

```bash
npm install tailwindcss @tailwindcss/postcss postcss
```

Create `.postcssrc.json` in project root:
```json
{
  "plugins": {
    "@tailwindcss/postcss": {}
  }
}
```

For CSS projects, add to `src/styles.css`:
```css
@import 'tailwindcss';
```

For SCSS projects, add to `src/styles.scss`:
```scss
@use 'tailwindcss';
```

### Differences from our PropertyHarbor setup

| Angular Official Guide | PropertyHarbor (this project) | Reason |
|------------------------|-------------------------------|--------|
| `ng add tailwindcss` automated | Manual setup | More control over daisyUI integration |
| SCSS `@use 'tailwindcss'` supported | CSS only (`src/styles.css`) | Sass intercepts `@import`/`@theme`/`@plugin` — CSS is required |
| `@import 'tailwindcss'` | `@import "tailwindcss"` + `@import "daisyui/daisyui.css"` | daisyUI added as direct CSS import |
| No mention of `@source` | `@source "./**/*.ts"` required | Angular build pipeline doesn't auto-scan TS inline templates |

> Angular 21 does **not** use Tailwind v4 by default — it must be installed explicitly via `ng add tailwindcss` or manual setup. The `ng add` command installs Tailwind v4 when run in Angular 17+ projects using the `@angular/build:application` (esbuild) builder.

## CSS-Native Configuration (No tailwind.config.js)

TailwindCSS v4 is a complete rewrite using CSS-native configuration:

```css
/* src/styles.css (NOT .scss — TailwindCSS 4.x directives conflict with Sass) */
@import "tailwindcss";

@theme {
  /* Typography */
  --font-sans: "Inter", "system-ui", sans-serif;
  --font-mono: "JetBrains Mono", monospace;

  /* Custom spacing */
  --spacing-18: 4.5rem;
  --spacing-22: 5.5rem;

  /* Custom breakpoints */
  --breakpoint-3xl: 1920px;

  /* Animation durations */
  --duration-instant: 50ms;
  --duration-quick: 150ms;
  --duration-standard: 250ms;
}

@plugin "daisyui" {
  themes: light --default, dark --prefersdark, corporate, business;
}
```
> **Note:** Do NOT add `@import "daisyui"` — daisyUI is loaded via the `@plugin` directive in TailwindCSS 4.x. The global stylesheet must be `.css` (not `.scss`) to avoid Sass intercepting CSS-native directives like `@import`, `@theme`, and `@plugin`.

## Breaking Changes from v3

| v3 Syntax | v4 Syntax | Notes |
|-----------|-----------|-------|
| `tailwind.config.js` | `@theme { }` in CSS | No JS config file |
| `@apply` directive | Still works, but discouraged | Use CSS variables instead |
| `theme.extend` | `@theme { --custom: value }` | CSS custom properties |
| `screens` config | `--breakpoint-*` variables | CSS-native breakpoints |
| `colors` config | Use daisyUI semantic colors | Don't define custom colors |

## PostCSS Configuration

> **CRITICAL:** Angular's `@angular/build:application` builder only reads `.postcssrc.json`. It **ignores** `postcss.config.js` / `.mjs` / `.cjs`. If you use the wrong file name, PostCSS plugins will not run and TailwindCSS utilities + daisyUI components will be missing from the output CSS.

```json
// .postcssrc.json (in project root, next to angular.json)
{
  "plugins": {
    "@tailwindcss/postcss": {}
  }
}
```

## Angular Integration

```json
// angular.json (styles array)
{
  "styles": [
    "src/styles.css"
  ]
}
```

## daisyUI v5 Import (CRITICAL)

> **Do NOT use `@plugin "daisyui"` in TailwindCSS 4.x with Angular.** The `@plugin` directive requires the daisyUI PostCSS plugin which is not bundled with `@tailwindcss/postcss` in Angular builds. It silently fails — no styles applied.

```css
/* src/styles.css — correct for Angular + TailwindCSS v4 + daisyUI v5 */
@import "tailwindcss";
@import "daisyui/daisyui.css";   /* Direct CSS import — always works */
```

Install:
```bash
npm install daisyui@latest
```

## TailwindCSS v4 Utility Class Scanning in Angular (CRITICAL)

> **TailwindCSS v4 with `@tailwindcss/postcss` does NOT auto-scan Angular inline templates in `.ts` files.** Utility classes used only in TypeScript template strings (e.g. `px-6`, `mx-auto`, `max-w-4xl`) will NOT be generated — only daisyUI component classes (from the direct CSS import) will work.

**Symptom:** daisyUI buttons/badges/cards render correctly, but spacing/layout/typography utilities (padding, margin, flex, grid, max-width) are completely missing.

**Fix — add explicit source directives:**
```css
/* src/styles.css */
@import "tailwindcss";
@import "daisyui/daisyui.css";
@source "./**/*.ts";
@source "./**/*.html";
```

**If `@source` still doesn't work** (path resolution can be inconsistent with PostCSS), safelist critical utilities directly in `styles.css`:
```css
@layer utilities {
  .px-4 { padding-left: 1rem; padding-right: 1rem; }
  .px-6 { padding-left: 1.5rem; padding-right: 1.5rem; }
  .mx-auto { margin-left: auto; margin-right: auto; }
  .max-w-4xl { max-width: 56rem; }
  /* ...add any utilities used in TypeScript template strings */
}
```

**Root cause:** `@tailwindcss/postcss` runs PostCSS transforms but its content scanner is invoked differently than the Tailwind CLI. Angular's build pipeline does not pass TypeScript source paths to the PostCSS plugin's scanner by default.

## Verification Checklist

### DaisyUI + Tailwind v4 — Setup Verification Checklist

After scaffolding, ALWAYS verify these before writing any UI components:

1. **Packages installed** — check package.json:
   - `tailwindcss` (v4.x)
   - `@tailwindcss/postcss`
   - `daisyui` (v5.x)

2. **CSS entry point** (`src/styles.css`) must contain:
   ```css
   @import "tailwindcss";
   @import "daisyui/daisyui.css";
   @source "./**/*.ts";
   @source "./**/*.html";
   ```
   ❌ Old Tailwind v3 syntax is WRONG for v4:
   ```css
   /* DO NOT USE */
   @tailwind base;
   @tailwind components;
   @tailwind utilities;
   ```
   ❌ Do NOT use `@plugin "daisyui"` — it silently fails in Angular builds (see daisyUI v5 Import section above).

3. **Angular JSON styles** — `angular.json` must reference `src/styles.css`:
   ```json
   "styles": ["src/styles.css"]
   ```

4. **PostCSS config** — `.postcssrc.json` (not `postcss.config.js`) must exist in the project root:
   ```json
   {
     "plugins": {
       "@tailwindcss/postcss": {}
     }
   }
   ```

5. **Smoke test after scaffold**: Open the app and confirm a `<button class="btn btn-neutral">Test</button>` renders with DaisyUI styling. If it renders as a plain browser button, styles are broken — fix before writing any feature UI.

## Breakpoints

```css
sm:   640px    /* Small tablets */
md:   768px    /* Tablets */
lg:   1024px   /* Small laptops */
xl:   1280px   /* Desktop */
2xl:  1536px   /* Large desktop */
```

Usage:
```html
<div class="p-4 md:p-6 lg:p-8">
  <!-- 16px mobile, 24px tablet, 32px desktop -->
</div>
```

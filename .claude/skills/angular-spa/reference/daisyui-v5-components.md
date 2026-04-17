# daisyUI v5.5.5 Component Reference

## Quick Reference

### TailwindCSS 4.x Setup

```css
/* src/styles.css (NOT .scss — TailwindCSS 4.x directives conflict with Sass) */
@import "tailwindcss";

@theme {
  --font-sans: "Inter", "system-ui", sans-serif;
}

@plugin "daisyui" {
  themes: light --default, dark --prefersdark, corporate, business;
}
```
> **Note:** Do NOT add `@import "daisyui"` — daisyUI is loaded via the `@plugin` directive in TailwindCSS 4.x.

### daisyUI v5.5.5 Modal (required pattern)

```html
<dialog id="my_modal" class="modal">
  <div class="modal-box">
    <h3 class="text-lg font-bold">Title</h3>
    <p class="py-4">Content</p>
    <div class="modal-action">
      <form method="dialog"><button class="btn">Close</button></form>
    </div>
  </div>
  <form method="dialog" class="modal-backdrop"><button>close</button></form>
</dialog>
```

### daisyUI v5.5.5 Drawer (required pattern)

```html
<div class="drawer lg:drawer-open">
  <input id="drawer" type="checkbox" class="drawer-toggle" />
  <div class="drawer-content"><!-- page content --></div>
  <div class="drawer-side">
    <label for="drawer" aria-label="close sidebar" class="drawer-overlay"></label>
    <ul class="menu bg-base-200 min-h-full w-80 p-4"><!-- nav items --></ul>
  </div>
</div>
```

### Color System Quick Reference

```
bg-base-100/200/300     — backgrounds
bg-primary/secondary/accent — brand colors
bg-info/success/warning/error — states
text-base-content       — primary text
text-base-content/60    — secondary text
border-base-300         — default borders
```

## Theme System

```html
<!-- Set theme on HTML element -->
<html lang="en" data-theme="light">

<!-- Angular theme binding -->
<html lang="en" [attr.data-theme]="currentTheme()">
```

## Color System

```css
/* Backgrounds — USE ONLY THESE */
bg-base-100       /* Primary background */
bg-base-200       /* Secondary background */
bg-base-300       /* Tertiary background */
bg-neutral        /* Dark neutral */
bg-primary        /* Brand primary */
bg-secondary      /* Brand secondary */
bg-accent         /* Accent color */
bg-info           /* Informational */
bg-success        /* Success state */
bg-warning        /* Warning state */
bg-error          /* Error state */

/* Text */
text-base-content        /* Primary text */
text-base-content/60     /* Secondary text */
text-base-content/40     /* Muted text */
text-primary-content     /* Text on primary bg */

/* Borders */
border-base-300          /* Default border */
border-base-content/20   /* Subtle border */
border-primary           /* Primary border */
border-error             /* Error border */

/* NEVER use hardcoded hex: bg-[#3b82f6] */
```

## Changes from v4 to v5

| Component | v4 | v5.5.5 | Notes |
|-----------|-----|--------|-------|
| Button soft | N/A | `btn-soft` | New: subtle background variant |
| Button XL | N/A | `btn-xl` | New size |
| Modal backdrop | Auto | Explicit | Add `modal-backdrop` form |
| Drawer overlay | Auto | Explicit | Requires `drawer-overlay` label |
| Loading | `loading` | `loading loading-spinner` | Must specify loader type |

## Required Patterns (v5.5.5)

### Modal
```html
<dialog id="my_modal" class="modal">
  <div class="modal-box">
    <h3 class="text-lg font-bold">Title</h3>
    <p class="py-4">Content</p>
    <div class="modal-action">
      <form method="dialog"><button class="btn">Close</button></form>
    </div>
  </div>
  <form method="dialog" class="modal-backdrop"><button>close</button></form>
</dialog>
```

### Drawer
```html
<div class="drawer lg:drawer-open">
  <input id="my-drawer" type="checkbox" class="drawer-toggle" />
  <div class="drawer-content">
    <label for="my-drawer" class="btn btn-primary drawer-button lg:hidden">Open</label>
  </div>
  <div class="drawer-side">
    <label for="my-drawer" aria-label="close sidebar" class="drawer-overlay"></label>
    <ul class="menu bg-base-200 text-base-content min-h-full w-80 p-4">
      <li><a>Item</a></li>
    </ul>
  </div>
</div>
```

### Loading States
```html
<button class="btn btn-primary">
  <span class="loading loading-spinner loading-sm"></span>
  Loading...
</button>

<!-- Variants: loading-spinner, loading-dots, loading-ring, loading-ball, loading-bars, loading-infinity -->
<!-- Sizes: loading-xs, loading-sm, loading-md, loading-lg -->
```

### Theme Controller (CSS-only theme switching)
```html
<!-- Dark/light toggle with swap -->
<label class="swap swap-rotate">
  <input type="checkbox" class="theme-controller" value="dark" />
  <svg class="swap-off h-8 w-8 fill-current" viewBox="0 0 24 24"><!-- sun --></svg>
  <svg class="swap-on h-8 w-8 fill-current" viewBox="0 0 24 24"><!-- moon --></svg>
</label>

<!-- Radio buttons for multiple themes -->
<input type="radio" name="theme" class="btn theme-controller" aria-label="Light" value="light" />
<input type="radio" name="theme" class="btn theme-controller" aria-label="Dark" value="dark" />
```

## Complete Component Listing

### Actions
`btn`, `dropdown`, `fab` (new), `modal`, `swap`, `theme-controller`

### Data Display
`accordion`, `avatar`, `badge`, `card`, `carousel`, `chat`, `collapse`, `countdown`, `diff`, `hover-3d` (new), `hover-gallery` (new), `kbd`, `list` (new), `stat`, `status` (new), `table`, `text-rotate` (new), `timeline`

### Navigation
`breadcrumbs`, `dock` (new), `link`, `menu`, `navbar`, `pagination`, `steps`, `tabs`

### Feedback
`alert`, `loading`, `progress`, `radial-progress`, `skeleton`, `toast`, `tooltip`

### Data Input
`checkbox`, `fieldset` (new), `file-input`, `filter` (new), `label` (new), `radio`, `range`, `rating`, `select`, `input`, `textarea`, `toggle`, `validator` (new)

### Layout
`divider`, `drawer`, `footer`, `hero`, `indicator`, `join`, `mask`, `stack`

## Common Patterns

```html
<!-- Buttons -->
<button class="btn btn-primary">Primary</button>
<button class="btn btn-outline btn-primary">Outline</button>
<button class="btn btn-ghost">Ghost</button>
<button class="btn btn-soft">Soft (v5)</button>

<!-- Card -->
<div class="card bg-base-100 shadow-xl">
  <div class="card-body">
    <h2 class="card-title">Title</h2>
    <p>Content</p>
    <div class="card-actions justify-end">
      <button class="btn btn-primary">Action</button>
    </div>
  </div>
</div>

<!-- Alert -->
<div class="alert alert-info"><span>Info message</span></div>
<div class="alert alert-soft alert-info">Soft style (v5)</div>

<!-- Skeleton -->
<div class="skeleton h-4 w-full"></div>
<div class="skeleton h-4 w-3/4"></div>
<div class="skeleton h-32 w-full"></div>

<!-- Fieldset (v5) -->
<fieldset class="fieldset bg-base-100 border-base-300 rounded-box border p-4">
  <legend class="fieldset-legend">Account</legend>
  <label class="label">Email</label>
  <input type="email" class="input" />
</fieldset>

<!-- Validator (v5) -->
<div class="validator">
  <input type="email" class="input" required />
  <span class="validator-hint">Please enter a valid email</span>
</div>

<!-- Filter (v5) -->
<div class="filter">
  <input type="radio" name="filter" class="filter-btn" aria-label="All" />
  <input type="radio" name="filter" class="filter-btn" aria-label="Active" />
  <button class="filter-reset">x</button>
</div>

<!-- Dock (v5) -->
<div class="dock">
  <button class="dock-item dock-active"><span class="dock-label">Home</span></button>
  <button class="dock-item"><span class="dock-label">Search</span></button>
</div>

<!-- List (v5) -->
<ul class="list bg-base-100 rounded-box shadow-md">
  <li class="list-row">
    <div><img class="size-10 rounded-box" src="avatar.jpg" /></div>
    <div>
      <div>Title</div>
      <div class="text-xs opacity-60">Subtitle</div>
    </div>
  </li>
</ul>

<!-- Status (v5) -->
<div class="status status-success"></div>
<div class="status status-error"></div>

<!-- Tabs -->
<div role="tablist" class="tabs tabs-boxed">
  <a role="tab" class="tab tab-active">Tab 1</a>
  <a role="tab" class="tab">Tab 2</a>
</div>

<!-- Steps -->
<ul class="steps">
  <li class="step step-primary">Register</li>
  <li class="step step-primary">Choose plan</li>
  <li class="step">Purchase</li>
</ul>

<!-- Dropdown -->
<div class="dropdown">
  <div tabindex="0" role="button" class="btn m-1">Click</div>
  <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-10 w-52 p-2 shadow">
    <li><a>Item 1</a></li>
  </ul>
</div>

<!-- Toast -->
<div class="toast toast-end">
  <div class="alert alert-success">Message sent!</div>
</div>

<!-- Breadcrumbs -->
<div class="breadcrumbs text-sm">
  <ul><li><a>Home</a></li><li><a>Docs</a></li><li>Current</li></ul>
</div>

<!-- Avatar group -->
<div class="avatar-group -space-x-6">
  <div class="avatar"><div class="w-12"><img src="1.jpg" /></div></div>
  <div class="avatar placeholder"><div class="bg-neutral text-neutral-content w-12"><span>+99</span></div></div>
</div>

<!-- Form inputs -->
<input type="text" class="input input-bordered w-full" placeholder="Text" />
<select class="select select-bordered w-full"><option>Option</option></select>
<textarea class="textarea textarea-bordered w-full"></textarea>
<input type="checkbox" class="checkbox" />
<input type="radio" name="r" class="radio" />
<input type="checkbox" class="toggle" />
<input type="range" class="range" min="0" max="100" />
<input type="file" class="file-input file-input-bordered w-full" />

<!-- Rating -->
<div class="rating">
  <input type="radio" name="rating" class="mask mask-star" />
  <input type="radio" name="rating" class="mask mask-star" checked />
  <input type="radio" name="rating" class="mask mask-star" />
</div>
```

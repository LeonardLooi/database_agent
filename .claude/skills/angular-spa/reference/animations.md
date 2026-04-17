# Animation Guidelines

## Timing Standards

| Type | Duration | Easing | Use Case |
|------|----------|--------|----------|
| Instant | 50-100ms | `ease-out` | Hover, click feedback |
| Quick | 100-200ms | `ease-out` | Dropdown, tooltip |
| Standard | 200-300ms | `ease-in-out` | Modal, sidebar, accordion |
| Emphasis | 300-500ms | `ease-in-out` | Onboarding, celebrations |

If the animation feels slow, it IS slow. Target 150-250ms for most interactions.

## DaisyUI / Tailwind Animation Classes

```html
<!-- Button feedback -->
<button class="btn btn-primary transition-transform duration-100 hover:scale-[1.02] active:scale-[0.98]">
  Submit
</button>

<!-- Card hover lift -->
<div class="card bg-base-100 shadow-md transition-all duration-200 hover:shadow-xl hover:-translate-y-1">
  ...
</div>
```

## Custom Keyframes (add to styles.css)

```css
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes scaleIn {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes slideDown {
  from { opacity: 0; transform: translateY(-16px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes slideInRight {
  from { opacity: 0; transform: translateX(16px); }
  to { opacity: 1; transform: translateX(0); }
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-4px); }
  75% { transform: translateX(4px); }
}

/* CRITICAL: Respect reduced motion preference */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

## Utility Classes

```css
.animate-fade-in { animation: fadeIn 300ms ease-out; }
.animate-scale-in { animation: scaleIn 200ms ease-out; }
.animate-slide-up { animation: slideUp 250ms ease-out; }
.animate-shake { animation: shake 400ms ease-in-out; }
```

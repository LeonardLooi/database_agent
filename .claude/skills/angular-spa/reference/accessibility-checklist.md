# Accessibility Checklist (WCAG 2.1 AA)

## Perceivable

- [ ] All images have descriptive `alt` text (or `alt=""` for decorative)
- [ ] Text contrast ratio >= 4.5:1 (3:1 for large text >= 18px bold or >= 24px)
- [ ] UI component contrast >= 3:1 against background
- [ ] Color is NOT the only indicator (add icons, text, patterns)
- [ ] Content can be resized to 200% without loss of functionality

## Operable

- [ ] All interactive elements are keyboard accessible (Tab, Enter, Space, Arrows)
- [ ] Focus indicators are clearly visible (min 2px, high contrast)
- [ ] Skip link provided: "Skip to main content" (first focusable element)
- [ ] No keyboard traps
- [ ] Touch targets >= 44x44px on mobile
- [ ] No time limits (or user can extend/disable)
- [ ] No auto-playing content that cannot be paused

## Understandable

- [ ] Page language declared: `<html lang="en">`
- [ ] Form inputs have visible labels (not just placeholder text)
- [ ] Error messages are specific and near the error source
- [ ] Consistent navigation across all pages
- [ ] Form validation errors are announced to screen readers

## Robust

- [ ] Semantic HTML: `<header>`, `<nav>`, `<main>`, `<aside>`, `<footer>`
- [ ] Headings follow logical hierarchy (h1 > h2 > h3, no skipping)
- [ ] ARIA labels on icon-only buttons: `aria-label="Close"`
- [ ] Tables have proper `<th>` headers with `scope` attribute
- [ ] Dynamic content updates announced: `aria-live="polite"`
- [ ] Focus managed after dynamic changes (modal open/close)

## Quick Test Protocol

1. **Keyboard**: Tab through entire UI — all interactive elements reachable
2. **Focus**: Ensure focus ring is always visible
3. **Zoom**: Browser at 200% — nothing breaks or overlaps
4. **Color**: Grayscale mode — all information still conveyed
5. **Screen Reader**: Test with VoiceOver (Mac) or NVDA (Windows)

## Common ARIA Patterns

```html
<!-- Icon-only button -->
<button class="btn btn-circle btn-ghost" aria-label="Close dialog">
  <svg>...</svg>
</button>

<!-- Loading state -->
<button class="btn" [attr.aria-busy]="loading()">
  @if (loading()) { <span class="loading loading-spinner"></span> }
  Submit
</button>

<!-- Live region for dynamic updates -->
<div aria-live="polite" aria-atomic="true" class="sr-only">
  {{ statusMessage() }}
</div>

<!-- Modal dialog -->
<dialog role="dialog" aria-modal="true" aria-labelledby="modal-title">
  <h2 id="modal-title">Dialog Title</h2>
</dialog>

<!-- Navigation landmark -->
<nav aria-label="Main navigation">...</nav>

<!-- Required form field -->
<input type="email" aria-required="true" aria-invalid="true" aria-describedby="email-error" />
<span id="email-error" role="alert">Please enter a valid email</span>
```

# Angular Animations

> Official docs: https://angular.dev/guide/animations

## Angular Animation API — Two Systems (Angular 21)

Angular 21 supports two animation systems. Prefer `animate.enter` / `animate.leave` for new code.

| System | Package | When to use |
|--------|---------|-------------|
| `animate.enter` / `animate.leave` | Compiler-built-in (Angular 21+) | New code — enter/leave transitions, CSS-class-based |
| `trigger()` / `state()` / `transition()` | `@angular/animations` | Stateful multi-step animations, stagger, route transitions |

---

## System 1 — `animate.enter` / `animate.leave` (Angular 21, preferred)

These are compiler-supported APIs. No imports needed — the Angular compiler handles them directly.

### Basic Usage

```html
<!-- Apply CSS class when element enters DOM -->
<div animate.enter="fade-in">Content</div>

<!-- Apply CSS class when element leaves DOM -->
<div animate.leave="fade-out">Content</div>

<!-- Both together -->
<div animate.enter="slide-up" animate.leave="fade-out">Content</div>
```

### With AnimationCallbackEvent (required for leave animations using third-party libs)

```typescript
import { Component } from '@angular/core';
import { AnimationCallbackEvent } from '@angular/animations';

@Component({
  selector: 'app-card',
  standalone: true,
  template: `
    <div
      animate.enter="fade-in"
      animate.leave="(event) => onLeave(event)"
    >
      Card content
    </div>
  `,
})
export class CardComponent {
  onLeave(event: AnimationCallbackEvent): void {
    // GSAP, anime.js, or custom JS animation here
    // MUST call animationComplete() when done so Angular removes the element
    event.animationComplete();
  }
}
```

### CSS for animate.enter / animate.leave

Define animation classes in `styles.css` (global) or component SCSS using `@keyframes`. Example:

```css
.fade-in  { animation: fadeIn  200ms ease-out forwards; }
.fade-out { animation: fadeOut 200ms ease-in  forwards; }
.slide-up { animation: slideUp 250ms ease-out forwards; }

/* Always include reduced-motion guard */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## System 2 — `@angular/animations` (trigger/state/transition)

Use for stateful animations, route transitions, list stagger, or when you need programmatic control.

### Imports

```typescript
import {
  trigger,
  state,
  style,
  transition,
  animate,
  keyframes,
  query,
  stagger,
  AnimationEvent,
} from '@angular/animations';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
```

### Bootstrap — `app.config.ts`

```typescript
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
// providers: [provideAnimationsAsync()]
```

### Attach to Component Decorator

```typescript
@Component({
  selector: 'app-example',
  standalone: true,
  template: `<div [@fadeInOut]="state">Content</div>`,
  animations: [
    trigger('fadeInOut', [
      state('void', style({ opacity: 0 })),
      state('*', style({ opacity: 1 })),
      transition(':enter', animate('200ms ease-out')),
      transition(':leave', animate('150ms ease-in')),
    ]),
  ],
})
export class ExampleComponent {
  state = 'active';
}
```

### Template Binding Syntax

```html
<!-- Bind to a trigger -->
<div [@triggerName]="expressionValue">...</div>

<!-- Enter/leave shorthands -->
<div [@fadeInOut]>...</div>  <!-- triggers :enter and :leave -->

<!-- Disabled animations -->
<div [@.disabled]="animationsDisabled">...</div>
```

### `trigger()` — Define a named animation

```typescript
trigger('myTrigger', [
  state(...),
  transition(...),
])
```

### `state()` — Define a named state with styles

```typescript
state('open', style({
  height: '200px',
  opacity: 1,
  backgroundColor: 'yellow',
})),
state('closed', style({
  height: '100px',
  opacity: 0.8,
  backgroundColor: 'blue',
})),
```

### `transition()` — Define transitions between states

```typescript
// Named states
transition('open => closed', animate('300ms ease-in')),
transition('closed => open', animate('300ms ease-out')),
transition('open <=> closed', animate('300ms ease-in-out')),  // bidirectional

// Enter / leave shorthands
transition(':enter', animate('200ms ease-out')),  // void => *
transition(':leave', animate('150ms ease-in')),   // * => void

// Any-to-any
transition('* => *', animate('200ms')),
```

### `animate()` — Define duration, delay, easing

```typescript
animate('300ms')                    // duration only
animate('300ms ease-in')            // duration + easing
animate('300ms 100ms ease-in-out')  // duration + delay + easing
animate('300ms', style({ opacity: 0 }))  // duration + final style
```

### `keyframes()` — Multi-step animations

```typescript
transition(':enter', [
  animate('500ms ease-in', keyframes([
    style({ opacity: 0, transform: 'translateY(-20px)', offset: 0 }),
    style({ opacity: 0.5, transform: 'translateY(10px)', offset: 0.6 }),
    style({ opacity: 1, transform: 'translateY(0)', offset: 1 }),
  ])),
]),
```

### `AnimationEvent` — Callbacks on start/done

```typescript
@Component({
  template: `
    <div
      [@fadeInOut]="state"
      (@fadeInOut.start)="onStart($event)"
      (@fadeInOut.done)="onDone($event)"
    >
      Content
    </div>
  `,
})
export class ExampleComponent {
  onStart(event: AnimationEvent): void {
    // event.triggerName, event.fromState, event.toState, event.totalTime
  }

  onDone(event: AnimationEvent): void {
    if (event.toState === 'closed') {
      // cleanup or follow-on logic
    }
  }
}
```

### `query()` + `stagger()` — List animations

```typescript
trigger('listAnimation', [
  transition('* => *', [
    query(':enter', [
      style({ opacity: 0, transform: 'translateY(-10px)' }),
      stagger(60, [
        animate('300ms ease-out', style({ opacity: 1, transform: 'translateY(0)' })),
      ]),
    ], { optional: true }),
    query(':leave', [
      stagger(40, [
        animate('200ms ease-in', style({ opacity: 0, transform: 'translateY(-10px)' })),
      ]),
    ], { optional: true }),
  ]),
]),
```

Template usage for list stagger:

```html
<ul [@listAnimation]="items.length">
  @for (item of items(); track item.id) {
    <li>{{ item.name }}</li>
  }
</ul>
```

---

## Timing Standards

| Type | Duration | Easing | Use Case |
|------|----------|--------|----------|
| Instant | 50–100ms | `ease-out` | Hover, click feedback |
| Quick | 100–200ms | `ease-out` | Dropdown, tooltip |
| Standard | 200–300ms | `ease-in-out` | Modal, sidebar, accordion |
| Emphasis | 300–500ms | `ease-in-out` | Onboarding, celebrations |

If the animation feels slow, it IS slow. Target 150–250ms for most interactions.

---

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

## PropertyHarbor Rule: Angular Animations Only

**MANDATORY for web/property-harbor:** Use Angular Animations for ALL animations.

- **NEW CODE:** Use `animate.enter` / `animate.leave` (compiler API) for enter/leave transitions
- **STATEFUL / COMPLEX:** Use `@angular/animations` (`trigger()`, `state()`, etc.) for multi-step or stateful animations
- **NEVER** use raw CSS `transition:` or `animation:` for interactive state changes on dynamic elements
- **NEVER** use JavaScript `setTimeout` for animation timing
- **CSS keyframes in `styles.css` are allowed ONLY** for static decorative animations (e.g. gradient bg, spinner) — not for enter/leave or state-driven transitions
- All component enter/leave, route transitions, and interactive animations → Angular Animations

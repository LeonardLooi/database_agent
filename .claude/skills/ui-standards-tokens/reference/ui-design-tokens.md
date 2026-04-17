# UI Design Tokens

## Spacing Tokens
```dart
class AppSpacing {
  static const double xs = 4;
  static const double sm = 8;
  static const double md = 16;
  static const double lg = 24;
  static const double xl = 32;
  static const double xxl = 48;
}
```

## Radius Tokens
```dart
class AppRadius {
  static const double none = 0;
  static const double sm = 4;
  static const double md = 8;
  static const double lg = 16;
  static const double xl = 24;
  static const double full = 999;
}
```

## Size Tokens
```dart
class AppSize {
  static const double iconSm = 16;
  static const double icon = 24;
  static const double iconLg = 32;
  static const double touchTarget = 48;
  static const double avatar = 40;
  static const double avatarLg = 64;
}
```

## Theme Usage

### Colors
```dart
// Never
Color(0xFF2196F3)
Colors.blue

// Always
Theme.of(context).colorScheme.primary
Theme.of(context).colorScheme.onSurface
Theme.of(context).colorScheme.surfaceContainerHighest
```

### Typography
```dart
// Never
TextStyle(fontSize: 16, fontWeight: FontWeight.bold)

// Always
Theme.of(context).textTheme.titleMedium
Theme.of(context).textTheme.bodyLarge?.copyWith(
  fontWeight: FontWeight.bold,
)
```

## Responsive Breakpoints

| Breakpoint | Width | Layout |
|------------|-------|--------|
| Mobile | < 600px | Single column |
| Tablet | 600-1199px | Two columns |
| Desktop | >= 1200px | Multi-column |

```dart
class ResponsiveLayout extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        if (constraints.maxWidth >= 1200) {
          return DesktopLayout();
        } else if (constraints.maxWidth >= 600) {
          return TabletLayout();
        }
        return MobileLayout();
      },
    );
  }
}
```

---

## Design Token Taxonomy (7 Categories)

Each category is shown with Flutter (Dart) and Angular (CSS variables) equivalents.

### 1. Color Tokens (3-Tier Hierarchy)

```
Primitive → Semantic → Component
```

- **Flutter:** `ThemeData.colorScheme` exposes Material 3 color roles — `primary`, `onPrimary`, `secondary`, `surface`, `error`, `surfaceContainerHighest`, etc.
- **Angular/CSS:**
  ```css
  /* Primitive */
  --color-blue-500: #3B82F6;

  /* Semantic */
  --color-primary: var(--color-blue-500);

  /* Component */
  --button-bg-primary: var(--color-primary);
  ```
- **Rule:** NEVER use primitive colors directly in components — always go through the semantic layer.

### 2. Spacing Tokens

- **Flutter:** `AppSpacing.xs/sm/md/lg/xl/xxl` (see above). All values follow a 4px base scale.
- **Angular/CSS:**
  ```css
  /* Primitive */
  --space-1: 4px;
  --space-2: 8px;
  --space-4: 16px;
  --space-6: 24px;
  --space-8: 32px;

  /* Semantic */
  --spacing-sm: var(--space-2);
  --spacing-md: var(--space-4);
  --spacing-lg: var(--space-6);
  ```
  Tailwind mapping: `p-2` = 8px, `p-4` = 16px, `p-6` = 24px.

### 3. Typography Tokens

- **Flutter:** `Theme.of(context).textTheme.*` — 15 roles from `displayLarge` down to `labelSmall`. Never use raw `TextStyle(fontSize: ...)`.
- **Angular/CSS:**
  ```css
  --font-sans: 'Inter', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
  --font-size-sm: 0.875rem;
  --font-size-base: 1rem;
  --font-size-lg: 1.125rem;
  --font-size-xl: 1.25rem;
  --font-weight-normal: 400;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;
  ```
  Never use hardcoded `px` font sizes in Angular component CSS.

### 4. Border & Radius Tokens

- **Flutter:** `AppRadius.sm/md/lg/xl/full` (see above).
- **Angular/CSS:**
  ```css
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-full: 9999px;
  ```
  daisyUI mapping: `rounded-sm`, `rounded-md`, `rounded-lg`, `rounded-full`.

### 5. Shadow Tokens

- **Flutter:** `Theme.of(context).cardTheme.elevation` for card elevation, or `BoxShadow` via `ThemeData` extensions. Never hardcode `BoxShadow` values inline.
- **Angular/CSS:**
  ```css
  --shadow-sm: 0 1px 2px rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px rgb(0 0 0 / 0.1);
  --shadow-focus-primary: 0 0 0 3px var(--color-primary);
  ```
  daisyUI utilities: `shadow-sm`, `shadow-md`, `shadow-xl`.

### 6. Motion Tokens

- **Flutter:**
  ```dart
  const Duration fast   = Duration(milliseconds: 150);
  const Duration normal = Duration(milliseconds: 200);
  const Duration slow   = Duration(milliseconds: 300);
  ```
  Always respect `MediaQuery.of(context).disableAnimations` — skip or shorten animations when true.
- **Angular/CSS:**
  ```css
  --duration-fast: 150ms;
  --duration-normal: 200ms;
  --duration-slow: 300ms;
  --ease-out: cubic-bezier(0, 0, 0.2, 1);

  @media (prefers-reduced-motion: reduce) {
    --duration-fast: 0ms;
    --duration-normal: 0ms;
    --duration-slow: 0ms;
  }
  ```

### 7. Z-Index Tokens (Angular Only)

Flutter uses `Stack` and `Overlay` for layering — there are no z-index tokens.

```css
--z-dropdown:       1000;
--z-modal-backdrop: 1040;
--z-modal:          1050;
--z-tooltip:        1070;
```

---

## Token Naming Convention

Component token format (both platforms):

```
{component}-{property}-{variant?}-{state?}
```

| CSS Variable | Flutter equivalent |
|---|---|
| `--button-bg-primary` | `colorScheme.primary` |
| `--button-bg-primary-hover` | `colorScheme.primary.withOpacity(0.9)` |
| `--input-border-color-focus` | `colorScheme.primary` |
| `--card-surface` | `colorScheme.surfaceContainerHighest` |

---

## Theme Switching

### Angular (CSS custom properties)

```css
:root {
  --color-primary: #3B82F6;
  --color-background: #FFFFFF;
}

:root[data-theme="dark"] {
  --color-primary: #60A5FA;
  --color-background: #111827;
}
```

### Flutter (ThemeData / brightness)

```dart
MaterialApp(
  themeMode: ThemeMode.system, // or .light / .dark
  theme: ThemeData(
    colorScheme: ColorScheme.fromSeed(
      seedColor: Colors.blue,
      brightness: Brightness.light,
    ),
  ),
  darkTheme: ThemeData(
    colorScheme: ColorScheme.fromSeed(
      seedColor: Colors.blue,
      brightness: Brightness.dark,
    ),
  ),
)
```

---

## Accessibility: WCAG Contrast Requirements

| Context | Minimum ratio |
|---|---|
| Normal text (< 18px or < 14px bold) | 4.5:1 |
| Large text (>= 18px, or >= 14px bold) | 3:1 |
| UI components (buttons, inputs, focus rings) | 3:1 |
| High-contrast theme target (WCAG AAA) | 7:1 |

Flutter: `ColorScheme.fromSeed` generates Material 3 tonal palettes designed to meet WCAG AA by default. Do not override role colors with arbitrary hex values — doing so breaks the contrast guarantees.

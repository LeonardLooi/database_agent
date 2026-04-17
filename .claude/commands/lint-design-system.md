---
description: Scan changed files for design system violations — detects hardcoded colors, raw spacing, inline typography, and touch target issues across Flutter and Angular
allowed-tools: Bash, Glob, Grep, Read
---

# /lint-design-system

Scan changed files for design system violations. Detects hardcoded colors, raw spacing values, inline typography, and touch target issues.

## Process

### 1. Detect Stack

Determine which stack to scan:
- If `*.dart` files exist in `lib/` → run Flutter checks
- If `*.html`, `*.scss`, `*.ts` files exist in `src/` → run Angular checks
- If both → run both

### 2. Flutter Design Checks

Scan `lib/**/*.dart` (exclude `*.g.dart`, `*.freezed.dart`):

| Check | Pattern | Violation |
|---|---|---|
| Hardcoded colors | `Color(0x...)`, `Colors.xxx` | Use `Theme.of(context).colorScheme` tokens |
| Raw spacing | `EdgeInsets.all(N)`, `SizedBox(height: N)` with numeric literals | Use `AppSpacing.xs/sm/md/lg/xl/xxl` |
| Raw TextStyle | `TextStyle(fontSize: N)` | Use `Theme.of(context).textTheme` |
| Small touch targets | `SizedBox` with width/height < 48 wrapping `GestureDetector`/`InkWell` | Minimum 48x48dp for interactive elements |

Commands to run:
```bash
# Hardcoded colors
grep -rn "Color(0x\|Colors\." lib/ --include="*.dart" | grep -v ".g.dart" | grep -v ".freezed.dart" | grep -v "test/" | grep -v "// ignore-design"

# Raw spacing
grep -rn "EdgeInsets\.\(all\|symmetric\|only\)([0-9]" lib/ --include="*.dart" | grep -v ".g.dart" | grep -v ".freezed.dart" | grep -v "// ignore-design"

# Raw TextStyle
grep -rn "TextStyle(fontSize:" lib/ --include="*.dart" | grep -v ".g.dart" | grep -v ".freezed.dart" | grep -v "// ignore-design"
```

### 3. Angular Design Checks

Scan `src/app/**/*.{html,scss,css,ts}`:

| Check | Pattern | Violation |
|---|---|---|
| Hardcoded hex colors | `bg-[#...]`, `text-[#...]`, `color: #...` | Use daisyUI semantic tokens (`bg-primary`, `text-base-content`) |
| Hardcoded rgb/hsl colors | `rgb(...)`, `rgba(...)`, `hsl(...)`, `hsla(...)` | Use daisyUI semantic tokens or CSS custom properties |
| Raw spacing utilities | `mt-3`, `px-4`, `gap-2` (numeric) | Use Tailwind's semantic scale or daisyUI component spacing |
| Raw typography | `text-[14px]`, `font-[...]`, `font-size: N` | Use Tailwind typography scale (`text-sm`, `text-lg`) |
| Raw form inputs | `<input>` without `formControl`, bare `<select>` | Use daisyUI form classes + reactive form bindings |
| Inline styles | `style="..."` in templates | Use TailwindCSS utilities or SCSS |

Commands to run:
```bash
# Hardcoded hex
grep -rn "bg-\[#\|text-\[#\|border-\[#\|color:\s*#" src/app/ --include="*.html" --include="*.scss" --include="*.css" | grep -v "// ignore-design" | grep -v "<!-- ignore-design"

# Hardcoded rgb/hsl
grep -rn "rgba\?\s*(\\|hsla\?\s*(" src/app/ --include="*.html" --include="*.scss" --include="*.css" | grep -v "// ignore-design" | grep -v "<!-- ignore-design"

# Raw spacing utilities
grep -rn "\b\(mt\|mb\|ml\|mr\|mx\|my\|pt\|pb\|pl\|pr\|px\|py\|gap\)-[0-9]" src/app/ --include="*.html" | grep -v "<!-- ignore-design"

# Raw typography
grep -rn "text-\[\d\+px\]\|text-\[\d\+rem\]\|font-\[.*\]\|font-size:\s*\d" src/app/ --include="*.html" --include="*.scss" --include="*.css" --include="*.ts" | grep -v "// ignore-design" | grep -v "<!-- ignore-design"

# Raw form inputs (feature templates only)
grep -rn "<input\s\|<select\s\|<textarea\s" src/app/features/ --include="*.html" | grep -v "formControl" | grep -v "<!-- ignore-design"

# Inline styles
grep -rn 'style="' src/app/ --include="*.html" | grep -v "<!-- ignore-design"
```

### 4. Report

Output results in this format:

```
## Design System Lint Report

### Flutter Violations
- [file:line] Hardcoded color: `Colors.blue` → use `Theme.of(context).colorScheme.primary`
- [file:line] Raw spacing: `EdgeInsets.all(16)` → use `EdgeInsets.all(AppSpacing.md)`

### Angular Violations
- [file:line] Hardcoded hex: `bg-[#3b82f6]` → use `bg-primary`
- [file:line] Raw spacing: `mt-3` → use semantic scale

### Summary
- Total violations: [N]
- Status: PASS (0 violations) / FAIL (1+ violations)
```

### 5. Exception Policy

Lines containing `// ignore-design: [reason]` or `<!-- ignore-design: [reason] -->` are excluded from checks. Exceptions should be rare and include a reason.

## Scope

- Flutter: `lib/` only (not `test/`, not generated files)
- Angular: `src/app/` only (not `node_modules/`, not generated files)
- Run this before `/review-code` to catch design drift early

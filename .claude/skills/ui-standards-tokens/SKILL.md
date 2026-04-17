---
name: ui-standards-tokens
description: "This skill provides design token definitions, theming patterns, and UI standards for Flutter applications. Use when auditing UI compliance, implementing design systems, or ensuring consistent token usage."
allowed-tools: Read
metadata:
  triggers: UI standards, design tokens, Flutter UI, Material 3, theming, accessibility, color contrast, token compliance
  related-skills: flutter-mobile, riverpod-patterns, frontend-design
  domain: frontend
  role: specialist
  scope: design
  output-format: document
last-reviewed: "2026-03-15"
---

**Iron Law:** Never use raw color hex values, spacing literals, or inline TextStyles — always reference design tokens; run /lint-design-system before any UI PR.

# UI Standards - Design Tokens & Patterns

Design token system and accessibility patterns for Flutter applications.

**When to use:** Auditing UI compliance, implementing spacing/radius/size tokens, theme usage, accessibility, or responsive layouts.

**Process:**

1. **Identify domain** from user request
2. **Load reference:**
   - Design tokens, theme colors, typography, responsive layouts → Read `reference/ui-design-tokens.md`
   - Accessibility, semantics, focus management, reduced motion → Read `reference/ui-accessibility-patterns.md`
3. **Apply patterns** using loaded reference
4. **Verify:** No hardcoded colors, all touch targets >= 48px, semantic widgets on interactive elements

## Error Handling

**Hardcoded colors detected**: Replace with theme tokens (`Theme.of(context).colorScheme`). Never use hex literals in widget code.

**Touch target too small**: Wrap small widgets in `SizedBox` with minimum 48x48 dp or use `Material` with `InkWell` for proper hit testing.

## Machine Enforcement

Design rules in this skill are enforced automatically at multiple layers:

### Hookify Rules (Claude Code gate — fires on every Write/Edit)

| Rule File | What It Catches | Action |
|---|---|---|
| `hookify.design-no-hardcoded-colors-dart.local.md` | `Color(0xFF...)`, `Colors.blue` in `lib/**/*.dart` | warn |
| `hookify.design-no-raw-spacing-dart.local.md` | `EdgeInsets.all(16)`, `SizedBox(height: 8)` in `lib/**/*.dart` | warn |
| `hookify.design-no-raw-textstyle-dart.local.md` | `TextStyle(fontSize: ...)` in `lib/**/*.dart` | warn |

### Lint Commands

| Command | What It Checks |
|---|---|
| `dart analyze` | Static analysis including unused imports, type errors |
| `/lint-design-system` | Orchestrator: scans for hardcoded colors, raw spacing, raw TextStyles, touch target violations |

### Scope

Enforcement applies to `lib/` directory only. Test files (`test/`), generated code (`*.g.dart`, `*.freezed.dart`), and build output are excluded.

### Exception Marker

When a design rule must be violated intentionally, use:
```dart
// ignore-design: [reason]
```
Exceptions are reviewed like code debt. Periodically audit and remove stale exceptions.

## Scope and Exception Policy

### Enforcement Scope

| Included | Excluded |
|---|---|
| `lib/` (Flutter app code) | `test/` (test files) |
| Widget files, screens, components | `*.g.dart` (generated code) |
| Theme definitions | `*.freezed.dart` (generated models) |
| | Build output, third-party packages |

### Exception Policy

When a design rule must be violated intentionally:

1. Add an inline marker: `// ignore-design: [short reason]`
2. Reason must explain WHY the exception is needed (e.g., "platform-specific iOS styling")
3. Exceptions are reviewed like code debt
4. Periodically audit: search for `ignore-design` and remove stale exceptions
5. If 5+ exceptions accumulate in one file, the design system may need extending — flag it

### Scope for Angular

| Included | Excluded |
|---|---|
| `src/app/` (app components) | `node_modules/` |
| Templates (`.html`) | Test files (`.spec.ts`) |
| Styles (`.scss`, `.css`) | Generated code |
| Component TypeScript (`.ts`) | Configuration files |

Angular exception marker: `<!-- ignore-design: [reason] -->` in templates, `// ignore-design: [reason]` in TS/SCSS.

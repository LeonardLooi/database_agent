---
description: Audit a file or session for WCAG 2.1 AA accessibility violations — ARIA labels, keyboard navigation, focus management, color contrast, form errors. Angular and Flutter supported.
allowed-tools: Read, Grep, Glob, Bash, Agent
---

# /fixing-accessibility

Audit for accessibility violations and produce targeted, minimal fixes.

## Usage

- `/fixing-accessibility` — apply accessibility constraints to all UI work in this session
- `/fixing-accessibility <file>` — audit the specified file and report violations with fixes

## Process

### 1. Load Skill

Load the `accessibility-audit` skill to get platform-specific patterns and checklists.

### 2. Detect Stack

- If argument is a `*.dart` file → Flutter audit (use `flutter-mobile/reference/accessibility-audit-checklist.md`)
- If argument is a `*.html`, `*.ts`, or `*.scss` file → Angular audit (use `angular-spa/reference/accessibility-checklist.md`)
- If no argument → session mode: apply constraints from both checklists to all subsequent UI work

### 3. File Audit Mode (`/fixing-accessibility <file>`)

Dispatch `accessibility-auditor` agent against the specified file.

For each violation found, report:
```
## Accessibility Audit: <file>

### Violations

| Priority | Rule | Line | Snippet | Fix |
|----------|------|------|---------|-----|
| CRITICAL | Accessible name missing | :42 | `<button><svg>...</svg></button>` | Add `aria-label="Close"` to button, `aria-hidden="true"` to SVG |
| HIGH     | aria-invalid not set | :87 | `<input id="email" />` | Add `aria-invalid="true"` and `aria-describedby="email-err"` |

### Summary
- Critical: N
- High: N
- Medium: N
- Low: N
- Status: PASS (0 violations) / FAIL (N violations)
```

### 4. Session Mode (`/fixing-accessibility`)

Apply these constraints to all UI work in this conversation:

**Angular — enforce before writing any interactive element:**
- Every `<button>`, `<a>`, `<input>`, `<select>`, `<textarea>` must have an accessible name
- Icon-only buttons: `aria-label` required, SVG gets `aria-hidden="true"`
- Form errors: `aria-describedby` + `aria-invalid="true"` on the field
- Modals: trap focus, restore on close, `Escape` dismisses
- Dynamic content: `aria-live` for errors and status updates
- No `tabindex > 0`
- Touch targets: minimum 44x44px

**Flutter — enforce before writing any interactive widget:**
- Every `GestureDetector`, `InkWell`, `IconButton` must have a `Semantics` label
- Decorative images: `Semantics(excludeSemantics: true)`
- Errors: `Semantics(liveRegion: true)` for dynamic announcements
- Touch targets: minimum 48x48dp
- Focus traversal: `FocusTraversalGroup` for complex widgets

### 5. Fix Discipline

- Fix only the violation — do not refactor unrelated code
- Prefer native HTML elements over ARIA role-based workarounds
- Do not add ARIA when native semantics already solve the problem
- Do not migrate UI libraries unless requested

## Rule Priority Reference

| Priority | Category | Impact |
|----------|----------|--------|
| 1 | Accessible names | CRITICAL |
| 2 | Keyboard access | CRITICAL |
| 3 | Focus and dialogs | CRITICAL |
| 4 | Semantics | HIGH |
| 5 | Forms and errors | HIGH |
| 6 | Announcements (aria-live) | MEDIUM-HIGH |
| 7 | Contrast and states | MEDIUM |
| 8 | Media and motion | LOW-MEDIUM |

## Related

- `accessibility-audit` skill — full automated test setup (axe-core, flutter_test SemanticsController)
- `accessibility-auditor` agent — deep WCAG 2.1 AA code review with file:line findings
- `docs/workflows/accessibility-audit.md` — 5-phase audit process with CI/CD gate
- `/lint-design-system` — design token compliance (run alongside this for full UI quality gate)

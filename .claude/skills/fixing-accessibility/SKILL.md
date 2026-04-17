---
name: fixing-accessibility
description: Audits and fixes WCAG 2.1 AA accessibility violations in Angular and Flutter — ARIA labels, keyboard navigation, focus management, color contrast, and form error patterns. Use when writing or reviewing UI components, or after completing any screen that has interactive elements.
allowed-tools: Read, Grep, Glob, Bash, Agent
agent: accessibility-auditor
context: fork
metadata:
  triggers: accessibility, a11y, WCAG, ARIA, keyboard nav, screen reader, color contrast, focus management, accessible name, fixing accessibility, accessibility audit
  related-skills: accessibility-audit, angular-spa, flutter-mobile
  domain: accessibility
  role: specialist
  scope: review
  output-format: report
last-reviewed: "2026-03-16"
---

**Iron Law:** Fix only the violation — never refactor unrelated code during an accessibility audit, and prefer native HTML/widget semantics over ARIA role workarounds.

# Fixing Accessibility

Audits and fixes WCAG 2.1 AA accessibility violations in Angular and Flutter. Produces targeted, minimal fixes — no collateral changes.

## When to Use

- After writing any UI screen with interactive elements
- Before opening a PR that touches components
- When a screen reader test reveals issues
- As a pre-submission gate for App Store / Play Store

## Platform Detection

| File type | Audit approach |
|-----------|---------------|
| `*.dart` | Flutter — Semantics widgets, touch targets (48dp), focus traversal |
| `*.html`, `*.ts`, `*.scss` | Angular — ARIA, keyboard nav, touch targets (44px), `aria-live` |
| No argument | Session mode — apply constraints to all subsequent UI work |

## Priority Reference

| Priority | Category | WCAG Level |
|----------|----------|------------|
| 1 | Accessible names (button, icon, input) | AA |
| 2 | Keyboard access — all interactive elements reachable | AA |
| 3 | Focus management — dialogs trap focus, restore on close | AA |
| 4 | Semantics — correct roles and structure | AA |
| 5 | Form errors — `aria-invalid` + `aria-describedby` | AA |
| 6 | Announcements — `aria-live` for dynamic content | AA |
| 7 | Contrast — 4.5:1 normal text, 3:1 large text | AA |

## Fix Discipline

- Fix only the violation — do not refactor unrelated code
- Prefer native HTML elements over ARIA role workarounds
- Do not add ARIA when native semantics already solve the problem

## Output Format

```
## Accessibility Audit: [file or scope]

### Violations
| Priority | Rule | Line | Snippet | Fix |
|----------|------|------|---------|-----|
| CRITICAL | Accessible name missing | :42 | `<button><svg>...</svg></button>` | Add `aria-label="Close"` |

### Summary
- Critical: N | High: N | Medium: N | Low: N
- Status: PASS / FAIL
```

---
name: accessibility-audit
description: WCAG 2.1 AA accessibility audit skill for Angular 21.x and Flutter 3.41.x. Use when auditing UI for accessibility compliance, identifying barriers, establishing automated testing, or preparing compliance evidence. Covers axe-core automated scanning, keyboard navigation, screen reader compatibility, color contrast, cognitive accessibility, and CI/CD integration.
allowed-tools: Read, Grep, Glob, Bash
agent: accessibility-auditor
context: fork
metadata:
  triggers: accessibility audit, WCAG, a11y, screen reader, keyboard navigation, color contrast, focus management, ARIA, Semantics widget, axe, pa11y, inclusive design, accessibility compliance
  related-skills: angular-spa, flutter-mobile, ui-standards-tokens, design-system, browser-testing
  domain: quality
  role: specialist
  scope: review
  output-format: report
  source: "adapted from community (antigravity-awesome-skills)"
last-reviewed: "2026-03-14"
---

# Accessibility Audit

> **Iron Law:** Before auditing any component, READ the actual file first.
> Do not flag violations based on memory — verify at file:line and show evidence.

WCAG 2.1 AA compliance audit for Angular 21.x and Flutter 3.41.x. Use to audit UI components, establish automated testing, identify accessibility barriers, and prepare compliance evidence.

## When to Use

- Auditing Angular or Flutter UI for WCAG 2.1 AA compliance
- Adding automated accessibility tests to CI/CD
- Identifying and remediating accessibility barriers
- Preparing compliance evidence for stakeholders
- Reviewing a PR that adds UI components

## Do Not Use

- For general UI design review without accessibility scope
- For backend services with no UI (Java, NestJS, Python, FastAPI)
- When you cannot access the UI files or artifacts

## Process

1. **Confirm scope** — which components, pages, or user journeys to audit
2. **Run automated scan** — axe-core (Angular) or flutter_test semantics (Flutter) for baseline violations
3. **Perform manual checks** — keyboard, screen reader, focus order, contrast
4. **Map findings to WCAG criteria** — severity (Critical / Important / Suggestion) and WCAG criterion
5. **Provide remediation** — exact code fixes with file:line evidence
6. **Re-test after fixes** — confirm each finding is resolved

## Reference Files

| File | Contents | Load When |
|------|----------|-----------|
| `reference/angular-a11y-automated.md` | axe-core Angular integration, keyboard trap detection, heading structure validation, pa11y | Adding automated a11y tests to Angular project |
| `reference/flutter-a11y-automated.md` | flutter_test semantics testing, SemanticsController patterns, widget test accessibility | Adding automated a11y tests to Flutter project |
| `reference/manual-testing-checklist.md` | Keyboard, screen reader, visual, cognitive manual checklists for both stacks | Running manual audit session |
| `reference/cicd-integration.md` | GitHub Actions workflows for Angular (axe + pa11y) and Flutter (semantic tests) | Integrating a11y into CI/CD pipeline |

## Existing Platform Checklists

These checklists already exist in the workspace — load them during audit:

- **Angular**: `.claude/skills/angular-spa/reference/accessibility-checklist.md` — WCAG 2.1 AA checklist, ARIA patterns
- **Flutter**: `.claude/skills/flutter-mobile/reference/accessibility-audit-checklist.md` — Semantics, contrast, touch targets, focus management
- **UI Patterns**: `.claude/skills/ui-standards-tokens/reference/ui-accessibility-patterns.md` — Flutter Semantics, FocusTraversalGroup, SemanticsService code patterns

## Output Format

```markdown
## Accessibility Audit — [Component/Page Name]

### Critical (Blocks users with disabilities)
- **[A11Y-001]** [Short description]
  - File: `path/to/file.dart:42` or `path/to/component.html:18`
  - WCAG: [criterion, e.g. 1.1.1 Non-text Content]
  - Issue: [what is wrong]
  - Fix: [exact code fix]

### Important (Degrades experience significantly)
- **[A11Y-002]** [Short description]
  - File: `path/to/file:line`
  - WCAG: [criterion]
  - Issue: [what is wrong]
  - Fix: [exact code fix]

### Suggestions (Enhances experience)
- **[A11Y-003]** [Short description]
  - File: `path/to/file:line`
  - Recommendation: [what to add/improve]

### Audit Summary
- Automated scan: [axe violations count] / [flutter semantics findings count]
- Manual checks: [passed/failed per category]
- WCAG 2.1 AA: [PASS / FAIL — N critical, N important]
```

## Agents

- `accessibility-auditor` — WCAG 2.1 compliance, Semantics widgets, touch targets, focus, contrast
- `ui-standards-expert` — design token usage, Material 3 theming, interaction contracts

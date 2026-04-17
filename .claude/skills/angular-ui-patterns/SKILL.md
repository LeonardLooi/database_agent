---
name: angular-ui-patterns
description: "Angular 21.x UI/UX state patterns — loading states (show only when no data), error hierarchy (inline→toast→banner→full-screen), empty states, button loading, form patterns with validation, dialog/modal patterns. Load when building any Angular UI component that handles async data or user actions."
allowed-tools: Read, Edit, Write, Glob, Grep, Bash, WebFetch, mcp__context7__resolve-library-id, mcp__context7__query-docs
metadata:
  triggers: Angular loading state, Angular error state, Angular empty state, Angular skeleton, Angular spinner, Angular form validation, Angular button loading, Angular dialog, Angular async UI, Angular UX patterns
  related-skills: angular-spa, angular, angular-best-practices
  domain: frontend
  role: specialist
  scope: implementation
  output-format: code
last-reviewed: "2026-03-15"
---

## Iron Law

**LOAD `angular-spa` FIRST for daisyUI component classes and TailwindCSS 4.x tokens. This skill provides UI state doctrine — use `angular-spa` reference files for the actual component HTML/CSS.**

## When to Use This Skill

Load this skill when:
- Building any Angular component that fetches async data
- Adding loading, error, or empty states to a list or page
- Implementing form validation with inline field errors
- Adding button loading states or disabling during async operations
- Building confirmation dialogs or modals
- Reviewing a component for missing UI state coverage

## Five Non-Negotiable Principles

1. **Never show stale UI** — Loading states only when actually loading, never over existing data
2. **Always surface errors** — Users must know when something fails; never swallow silently
3. **Optimistic updates** — Make the UI feel instant; roll back on failure
4. **Progressive disclosure** — Use `@defer` to show content as available
5. **Graceful degradation** — Partial data is better than no data

---

## Pattern Selector

What are you building?
- Async list/page → load `reference/loading-control-flow.md`
- Error handling → load `reference/error-handling.md`
- Button with loading → load `reference/button-empty-states.md`
- Form with validation → load `reference/form-dialog-patterns.md`
- Reviewing for mistakes → load `reference/anti-patterns.md`

## Reference Files

| Reference | Load When |
|-----------|-----------|
| [reference/index.md](reference/index.md) | Any time — navigation |
| [reference/loading-control-flow.md](reference/loading-control-flow.md) | Building async list or page |
| [reference/error-handling.md](reference/error-handling.md) | Adding error handling |
| [reference/button-empty-states.md](reference/button-empty-states.md) | Buttons or collections |
| [reference/form-dialog-patterns.md](reference/form-dialog-patterns.md) | Forms or confirmation dialogs |
| [reference/anti-patterns.md](reference/anti-patterns.md) | Reviewing a component |

---

## UI State Checklist

Before completing any UI component:

### UI States

- [ ] Error state handled and shown to user
- [ ] Loading state shown only when no data exists
- [ ] Empty state provided for collections (`@empty` block)
- [ ] Buttons disabled during async operations
- [ ] Buttons show loading indicator when appropriate

### Data & Mutations

- [ ] All async operations have error handling
- [ ] All user actions have feedback (toast/visual)
- [ ] Optimistic updates rollback on failure

### Accessibility

- [ ] Loading states announced to screen readers
- [ ] Error messages linked to form fields
- [ ] Focus management after state changes

---

## daisyUI Integration

This skill provides the doctrine. Use these daisyUI classes from `angular-spa` skill:
- Loading: `class="loading loading-spinner loading-lg"`
- Alert: `class="alert alert-error"` / `class="alert alert-success"`
- Button loading: `class="btn btn-primary loading"`
- Skeleton: `class="skeleton h-4 w-full"`
- Empty state: `class="hero min-h-32"`

---

## Related Skills

- `angular-spa` — workspace skill: daisyUI components, TailwindCSS tokens, conventions
- `angular` — core API reference for signals and control flow
- `angular-best-practices` — performance rules that complement these UI patterns

---
name: scaffold-a2ui
description: Scaffold an A2UI (Agent-to-User Interface) renderer feature module in an existing Angular 21.x app with component catalog, recursive renderer, agent service, and chat page
argument-hint: "[feature name, default: a2ui-chat]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, WebFetch, mcp__context7__resolve-library-id, mcp__context7__query-docs
disable-model-invocation: true
---

# Scaffold A2UI Angular Renderer

Create an A2UI renderer feature module in an existing Angular 21.x project.

**Feature name:** $ARGUMENTS (default to "a2ui-chat" if not provided)

## Pre-requisites

> **Official SDK:** `npm install @a2ui/angular` is the official Angular renderer SDK. If the project
> can use it, prefer the official package over a custom renderer implementation.

1. Read the `a2ui-angular` skill (`SKILL.md` and all `reference/*.md` files) for protocol spec, security rules, component catalog, and renderer patterns.
2. Read the `angular-spa` skill's `reference/angular-conventions.md` for Angular coding standards.
3. Use Context7 MCP to verify Angular signal inputs/outputs API if unsure.

## Steps

1. **Create feature folder structure**
   ```
   src/app/features/<name>/
   +-- models/a2ui.model.ts
   +-- services/a2ui-catalog.service.ts
   +-- services/a2ui-agent.service.ts
   +-- services/a2ui-sanitizer.service.ts
   +-- components/a2ui-renderer/a2ui-renderer.component.ts
   +-- components/a2ui-renderer/a2ui-renderer.component.spec.ts
   +-- components/a2ui-chat/a2ui-chat.component.ts
   +-- components/a2ui-chat/a2ui-chat.component.spec.ts
   +-- <name>.routes.ts
   ```

2. **Create A2UI models** — `A2UIValue`, `A2UIChildren`, `A2UIComponent`, `SurfaceUpdate`, `DataModelUpdate`, `A2UIMessage`, `SurfaceState`, `UserAction`, `ChatMessage` interfaces. `UserAction` is the client→agent message type: `{ name, surfaceId, sourceComponentId, timestamp, context }`. Follow `reference/a2ui-renderer-patterns.md` models section.

3. **Create catalog service** — Allowlist of official A2UI v0.8 component types: `Row`, `Column`, `Text`, `Image`, `Icon`, `Button`, `TextField`, `Checkbox`, `DateTimeInput`, `Card`, `Modal`, `Tabs`, `List`, `Divider`. Follow `reference/a2ui-security.md`.

4. **Create sanitizer service** — URL validation (protocol check), text length limits. Follow `reference/a2ui-security.md`.

5. **Create recursive renderer component** — Maps official A2UI v0.8 types (Row, Column, Text, Image, Icon, Button, TextField, Checkbox, DateTimeInput, Card, Modal, Tabs, List, Divider) to Angular/daisyUI components via `@switch`. Uses signal inputs, `computed()` for child filtering, validates against catalog. Note: Card uses `child` (single id string); layout components use `children.explicitList`. Follow `reference/a2ui-renderer-patterns.md`.

6. **Create agent service** — REST endpoints for `sendMessage` (text → agent) and `sendUserAction(action: UserAction): Observable<SurfaceState>` (button/form actions → agent). `sendUserAction` sends a `UserAction` message and builds `SurfaceState` from the JSONL messages in the response. Optional SSE streaming support. Follow `reference/a2ui-renderer-patterns.md`.

7. **Create chat page component** — Message history with chat bubbles, A2UI renderer for agent responses, text input, loading state, action handling. Follow `reference/a2ui-renderer-patterns.md`.

8. **Create lazy-loaded route** — Add route config in `<name>.routes.ts`, wire into `app.routes.ts` with `loadChildren`.

9. **Write unit tests** — Test catalog validation (allow known, reject unknown), renderer (renders card, skips malicious), action dispatch (emits correct data). Follow test templates in renderer patterns reference.

10. **Verify build** — Run `npx ng build` to catch compilation errors.

11. **Print summary** — List created files, how to run, next steps (connect to real agent backend).

## Reference

- `a2ui-angular` skill: `reference/a2ui-protocol.md`, `reference/a2ui-security.md`, `reference/a2ui-component-catalog.md`, `reference/a2ui-renderer-patterns.md`
- `angular-spa` skill: `reference/angular-conventions.md`, `reference/angular-templates.md`

$ARGUMENTS

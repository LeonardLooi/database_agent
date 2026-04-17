---
name: a2ui-angular
description: "A2UI (Agent-to-User Interface) renderer development for Angular 21.x. Use when building A2UI component renderers, agent-driven UIs, A2UI catalogs, action handlers, or streaming A2UI payloads. Covers protocol implementation, security validation, component mapping, and agent integration."
allowed-tools: Read, Edit, Write, Glob, Grep, Bash, WebFetch, mcp__context7__resolve-library-id, mcp__context7__query-docs
metadata:
  triggers: A2UI, agent-to-user interface, agent UI, A2UI renderer, A2UI catalog, A2UI component, agent-driven UI, declarative UI protocol
  related-skills: angular-spa, frontend-design, ui-standards-tokens, ai-chat
  domain: frontend
  role: specialist
  scope: implementation
  output-format: code
last-reviewed: "2026-03-15"
---

# A2UI Angular Renderer Development Skill

> **Tech Stack**: Angular 21+, A2UI Protocol v0.8+, TailwindCSS 4.x, daisyUI 5.5.5

## What is A2UI?

A2UI (Agent-to-User Interface) is a **declarative protocol by Google** that lets AI agents describe rich, interactive UIs as structured JSON data instead of generating executable code. The agent sends a JSON blueprint; the client app renders it using its own native components.

**Key principle:** UI-as-data, not UI-as-code. Agents never generate HTML/JS — they describe intent via a flat component adjacency list. The client validates against an approved component catalog and renders with native framework components.

## Iron Law

**A2UI PAYLOADS ARE UNTRUSTED. VALIDATE COMPONENT TYPES AGAINST THE CATALOG ALLOWLIST BEFORE RENDERING. NEVER EXECUTE AGENT-PROVIDED CODE.**

Every component from an agent must be validated against the client's approved catalog. Rendering any component type the agent sends, or executing agent-provided scripts, exposes the application to XSS, code injection, and data theft. The catalog allowlist is the security boundary.

## Conventions & Structure

> For Angular coding conventions, read the `angular-spa` skill's `reference/angular-conventions.md`
> For A2UI-specific patterns, read `reference/a2ui-protocol.md`

## Documentation Sources

| Source | URL / Tool | Purpose |
|--------|-----------|---------|
| A2UI Spec | `https://a2ui.org/` | Protocol specification, component format |
| A2UI GitHub | `https://github.com/google/A2UI` | Reference implementations, samples |
| A2A Extension | `https://a2ui.org/a2a-extension/a2ui/v0.8` | A2A protocol integration (Python ADK) |
| @a2ui/angular | `npm install @a2ui/angular` | Official Angular renderer SDK |
| Angular v21 | `angular-cli` MCP | Workspace-aware help, schematics |
| daisyUI v5 | `https://daisyui.com/llms.txt` | Component reference for rendering |
| TailwindCSS | `Context7` MCP | Utility classes for layout |

## Before Writing Any A2UI Code

1. **Read `reference/a2ui-protocol.md`** — protocol structure, JSON format, adjacency list, action model
2. **Read `reference/a2ui-renderer-patterns.md`** — Angular renderer architecture, catalog service, recursive rendering
3. **Read `reference/a2ui-security.md`** — allowlist enforcement, injection prevention, input sanitization
4. **Read `reference/a2ui-component-catalog.md`** — standard component types, property schemas, action definitions
5. **Verify Angular APIs** — Use `angular-cli` MCP or Context7 MCP before using any Angular API

## Process

1. **Understand Requirements** — Clarify which A2UI component types to support, agent transport (REST/WebSocket/SSE), and action handling needs
2. **Define Component Catalog** — Create the allowlist of approved A2UI component types with their property schemas
3. **Build Renderer** — Create the recursive `A2UIRendererComponent` that maps A2UI types to Angular/daisyUI components
4. **Implement Agent Service** — Create the service that communicates with the AI agent and receives A2UI payloads
5. **Add Action Handling** — Wire user interactions (clicks, form submits) back to the agent as A2UI actions
6. **Enable Streaming** — Support progressive rendering via SSE or WebSocket for real-time UI updates
7. **Write Tests** — Unit tests for catalog validation, renderer component, and action dispatch
8. **Verify Build** — Run `ng build` to ensure no compilation errors

## Reference Files

Detailed patterns are in `reference/`:

### A2UI Protocol
- `a2ui-protocol.md` — Protocol specification, JSON format, adjacency list structure, message types, userAction
- `a2ui-protocol-advanced.md` — Action model, streaming (JSONL/SSE/WebSocket/REST/A2A), A2A integration, versioning
- `a2ui-security.md` — Allowlist enforcement, injection prevention, untrusted payload handling
- `a2ui-component-catalog.md` — Layout (Row, Column) + Display (Text, Image, Icon, Divider) + Interactive (Button, TextField, Checkbox, DateTimeInput) component schemas
- `a2ui-component-containers.md` — Container types (Card, Modal, Tabs, List), extended catalog, how to add new types

### Angular Implementation
- `a2ui-renderer-patterns.md` — Architecture overview, file structure, TypeScript models, catalog service, sanitizer service, renderer key patterns
- `a2ui-renderer-template.md` — Full A2UIRendererComponent implementation (all 12 @case branches, computed signals, action dispatch)
- `a2ui-chat-template.md` — Chat page component, streaming variant (SSE + JSONL), wire format reference with JSON examples
- `a2ui-renderer-services.md` — A2UIAgentService (REST + SSE), buildSurfaceState, unit test template (5 test cases)

## Anti-Patterns — What to Avoid

```typescript
// ❌ FORBIDDEN: Rendering arbitrary component types from agent
@switch (comp.type) {
  @default {
    <div [innerHTML]="comp.properties['html']"></div>  // XSS vector!
  }
}

// ✅ REQUIRED: Validate against catalog, skip unknown types
@switch (comp.type) {
  @default {
    <!-- Unknown A2UI type silently skipped — not in catalog -->
  }
}
```

```typescript
// ❌ FORBIDDEN: Executing agent-provided code
eval(comp.properties['script']);
new Function(comp.properties['handler'])();

// ✅ REQUIRED: Declarative action dispatch (v0.8 format)
onAction(comp: A2UIComponent): void {
  const action = comp['action'] as { name: string; context?: Array<{ key: string; value: unknown }> };
  if (!action?.name) return;
  this.actionTriggered.emit({ name: action.name, context: action.context ?? [] });
}
```

```typescript
// ❌ FORBIDDEN: Deeply nested JSON tree from agent
{ "children": [{ "children": [{ "children": [...] }] }] }

// ✅ REQUIRED: surfaceUpdate with components as array, root field (A2UI v0.8 protocol)
{
  "surfaceUpdate": {
    "surfaceId": "main",
    "components": [
      { "id": "root", "component": { "type": "Column", "children": {"explicitList": ["btn-1"]} } },
      { "id": "btn-1", "component": { "type": "Button", "primary": true, "action": {"name": "submit"} } }
    ],
    "root": "root"
  }
}

// ✅ REQUIRED: userAction — 5th message type, client → agent
{
  "userAction": {
    "name": "book_hotel",
    "surfaceId": "main",
    "sourceComponentId": "btn-book",
    "timestamp": "2026-03-10T12:00:00Z",
    "context": { "hotelId": "H-456" }
  }
}
```

## Error Handling

- If agent returns an unknown component type → skip it silently (log warning), render remaining components
- If agent payload is malformed JSON → show error state to user, log full error
- If agent connection drops mid-stream → render what was received so far, show reconnect option
- If action dispatch fails → show error toast, do NOT silently swallow

## Common Commands

```bash
# Generate A2UI feature module
mkdir -p src/app/features/a2ui-chat/{components,services,models}

# Run tests
npx ng test --watch=false

# Build
npx ng build
```

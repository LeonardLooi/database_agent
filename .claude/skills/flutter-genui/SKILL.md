---
name: flutter-genui
description: "Flutter GenUI SDK — conversational AI-driven UI using A2UI protocol. Use when building GenUI renderers, widget catalogs, Conversation orchestration, DataModel binding, SurfaceController setup, or SSE-streamed agent-to-UI flows in Flutter. Covers catalog design, A2UI transport, state binding, custom widgets, and PropertyHarbor triage integration."
allowed-tools: Read, Edit, Write, Glob, Grep, Bash, WebFetch, mcp__context7__resolve-library-id, mcp__context7__query-docs, mcp__dart-mcp-server__dart
metadata:
  triggers: GenUI, gen_ui, genui, Flutter GenUI, conversational UI, A2UI Flutter, widget catalog, Catalog, CatalogItem, Conversation, DataModel, SurfaceController, A2uiTransportAdapter, triage UI, agent-driven UI Flutter, gen ui renderer
  related-skills: flutter-mobile, google-adk, a2ui-angular, flutter-animation
  domain: frontend
  role: specialist
  scope: implementation
  output-format: code
last-reviewed: "2026-03-30"
---

# Flutter GenUI SDK — Conversational AI-Driven UI

> **Tech Stack**: Flutter 3.41.x / Dart 3.10.9, `genui` package (experimental/alpha), A2UI Protocol v0.8+, Riverpod 3.x

## What is GenUI?

GenUI is Flutter's official SDK for **generative UI** — it turns text-based LLM conversations into interactive native Flutter widgets at runtime. Instead of receiving walls of text from an AI agent, users interact with dynamically rendered graphical interfaces composed from a developer-defined widget catalog.

**Key principle:** The AI agent generates structured JSON (A2UI protocol); the Flutter client validates against an approved catalog and renders native widgets. Agents never generate Dart code — they describe intent via JSON, the client renders it safely.

**Status:** Highly experimental / alpha. API will change. Pin to a specific commit or version.

## Iron Law

**GENUI PAYLOADS ARE UNTRUSTED. VALIDATE COMPONENT TYPES AGAINST THE CATALOG BEFORE RENDERING. NEVER EXECUTE AGENT-PROVIDED CODE. NEVER RENDER UNREGISTERED WIDGET TYPES.**

## Core Concepts (6 Pillars)

| Concept | Class/Type | Role |
|---------|-----------|------|
| **Catalog** | `Catalog` (list of `CatalogItem`) | Defines which widgets the AI is allowed to use — schemas + builders |
| **Conversation** | `Conversation` | Manages history, sends user input, invokes the model, drives the UI generation loop |
| **A2UI Transport** | `A2uiTransportAdapter`, `A2uiMessage` | Translates streamed model output into UI commands (GenUI uses A2UI under the hood) |
| **DataModel** | `DataModel` | Central observable state store — data binding and update flow |
| **SurfaceController** | `SurfaceController` | Processes messages, manages surfaces, keeps generated UI in sync |
| **CatalogItem** | `CatalogItem` | Individual widget registration — JSON schema + Dart builder function |

## Package Structure

| Package | Purpose |
|---------|---------|
| `genui` | Core framework — Catalog, Conversation, SurfaceController, rendering |
| `genui_a2a` | A2UI protocol connector for custom agent backends (ADK, REST, etc.) |
| `genai_primitives` | Technology-agnostic AI application types |
| `json_schema_builder` | Dart JSON Schema validation for widget definitions |

## Prerequisites

- Flutter >= 3.35.7 (PropertyHarbor uses 3.41.x)
- Add to `pubspec.yaml` in the package that uses GenUI (e.g., `packages/shared_ui/`):
  ```yaml
  dependencies:
    genui:
      git:
        url: https://github.com/flutter/genui.git
        path: packages/genui
    genui_a2a:
      git:
        url: https://github.com/flutter/genui.git
        path: packages/genui_a2a
  ```

## Before Writing Any GenUI Code

1. **Read `reference/genui-catalog-design.md`** — how to define Catalog, CatalogItem, JSON schemas, builder functions
2. **Read `reference/genui-conversation-orchestration.md`** — Conversation lifecycle, model adapters, streaming loop
3. **Read `reference/genui-state-binding.md`** — DataModel, SurfaceController, reactive state, surface rendering
4. **Read `reference/genui-a2ui-transport.md`** — A2uiTransportAdapter, A2uiMessage, SSE streaming, JSONL parsing
5. **Read `reference/genui-custom-widgets.md`** — custom widget integration, PropertyHarbor triage widgets
6. **Read `reference/genui-security.md`** — catalog allowlist enforcement, input sanitization, payload limits
7. **Verify Flutter/Dart APIs** — Use `dart-mcp-server` or Context7 MCP before using any API

## Process

1. **Define the Catalog** — Register all allowed widget types as `CatalogItem` objects with JSON schemas and builder functions
2. **Configure Transport** — Set up `A2uiTransportAdapter` to connect to your AI agent backend (ADK SSE endpoint)
3. **Create Conversation** — Initialize `Conversation` with the catalog, transport adapter, and model configuration
4. **Build Surface Rendering** — Use `SurfaceController` to process incoming A2UI messages and render surfaces
5. **Implement DataModel Binding** — Bind widget state to `DataModel` for reactive updates
6. **Handle User Input** — Wire user interactions back to the Conversation as structured events
7. **Add Custom Widgets** — Register PropertyHarbor-specific widgets (photo_upload, dropdown, rating, etc.)
8. **Write Tests** — Unit tests for catalog validation, surface building, input handling
9. **Verify Build** — Run `melos run test` and `flutter analyze`

## Reference Files

Detailed patterns are in `reference/`:

### Core SDK
- `genui-catalog-design.md` — Catalog, CatalogItem, JSON schema definition, builder patterns, widget registration
- `genui-conversation-orchestration.md` — Conversation lifecycle, model adapter setup, message history, streaming loop
- `genui-state-binding.md` — DataModel observable state, SurfaceController, surface management, reactive rendering
- `genui-a2ui-transport.md` — A2uiTransportAdapter, A2uiMessage types, SSE/JSONL streaming, backend integration

### Integration
- `genui-custom-widgets.md` — Custom widget registration, PropertyHarbor triage widgets (photo_upload, dropdown, free_text, rating, confirmation), category-specific widget sets
- `genui-security.md` — Catalog allowlist enforcement, untrusted payload handling, input sanitization, size limits

### A2UI Protocol (shared with Angular skill)
- See `../a2ui-angular/reference/a2ui-protocol.md` for the full A2UI protocol spec (5 message types, JSONL format)
- See `../a2ui-angular/reference/a2ui-protocol-advanced.md` for streaming, action model, Gemini quirks

## PropertyHarbor Integration

GenUI is used in PropertyHarbor for the **tenant triage flow** — the conversational UI that replaces static maintenance request forms.

**Flow:**
1. Tenant describes issue (voice/text) -> `POST /triage/start` returns `{ job_id }`
2. Flutter opens `GET /triage/{job_id}/stream` SSE
3. Agent streams `{ response, category, widgets[] }` via A2UI protocol
4. `GenUIRenderer` renders widgets as native Flutter widgets
5. Tenant interacts -> next question streams -> repeat until triage complete

**Fallback:** If GenUI/ADK unavailable -> standard form fields shown; ticket `needs_classification = true`

**File location in monorepo:**
```
packages/shared_ui/
  lib/
    widgets/
      gen_ui/
        gen_ui_renderer.dart      # SurfaceController + rendering logic
        widget_catalog.dart       # Catalog with all registered CatalogItems
        widget_types.dart         # Custom widget builders (PhotoUpload, etc.)
        triage_conversation.dart  # Conversation setup for triage flow
```

## Anti-Patterns

```dart
// FORBIDDEN: Rendering arbitrary widget types from agent
Widget buildFromAgent(Map<String, dynamic> spec) {
  // Agent controls what gets rendered — XSS/injection vector
  return widgetRegistry[spec['type']]!(spec);
}

// REQUIRED: Validate against Catalog before rendering
Widget buildFromAgent(Map<String, dynamic> spec) {
  final item = catalog.findByType(spec['type']);
  if (item == null) {
    logger.warning('Unknown GenUI type rejected: ${spec['type']}');
    return const SizedBox.shrink(); // Skip unknown types
  }
  return item.builder(spec);
}
```

```dart
// FORBIDDEN: Executing agent-provided code
eval(spec['script']); // Dart doesn't have eval, but don't try alternatives

// FORBIDDEN: Using dynamic widget creation from agent strings
Function.apply(spec['handler'], []); // Never

// REQUIRED: Declarative catalog-based rendering only
```

```dart
// FORBIDDEN: Accepting unbounded payloads
final widgets = parseWidgets(response); // No size check

// REQUIRED: Enforce limits
final widgets = parseWidgets(response);
if (widgets.length > kMaxWidgets) {
  widgets.removeRange(kMaxWidgets, widgets.length);
  logger.warning('GenUI: payload truncated — exceeded $kMaxWidgets widgets');
}
```

## Error Handling

- Agent returns unknown widget type -> skip silently (log warning), render remaining widgets
- Agent payload is malformed JSON -> show error state to user, log full error
- Agent connection drops mid-stream -> render what was received, show reconnect option
- User action dispatch fails -> show error snackbar, do NOT silently swallow
- GenUI SDK unavailable or fails to initialize -> fall back to static form fields

## Common Commands

```bash
# Add GenUI dependency (from packages/shared_ui/)
# Note: GenUI is git-sourced, add to pubspec.yaml manually

# Bootstrap after adding dependency
melos bootstrap

# Run tests
melos run test

# Analyze
flutter analyze packages/shared_ui/

# Run specific GenUI tests
flutter test packages/shared_ui/test/widgets/gen_ui/
```

## Documentation Sources

| Source | URL / Tool | Purpose |
|--------|-----------|---------|
| Flutter GenUI Docs | `https://docs.flutter.dev/ai/genui` | Official overview, concepts |
| GenUI Components | `https://docs.flutter.dev/ai/genui/components` | Catalog, CatalogItem, Conversation, DataModel, SurfaceController |
| GenUI Get Started | `https://docs.flutter.dev/ai/genui/get-started` | Setup, initialization, first app |
| GenUI Input Events | `https://docs.flutter.dev/ai/genui/input-events` | User interaction handling |
| GenUI GitHub | `https://github.com/flutter/genui` | Source code, examples, packages |
| A2UI Protocol | `https://a2ui.org/` | Underlying protocol spec |
| A2UI GitHub | `https://github.com/google/A2UI` | Reference implementations |
| Dart MCP | `dart-mcp-server` MCP | Dart/Flutter API verification |
| Context7 | `Context7` MCP | Library docs fallback |

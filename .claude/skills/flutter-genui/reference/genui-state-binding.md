# GenUI State Binding — DataModel & SurfaceController

## Overview

GenUI uses two state management primitives:
- **DataModel** — The central observable state store. Holds typed key-value data that widgets bind to reactively. Updated by `dataModelUpdate` messages from the agent.
- **SurfaceController** — Processes incoming A2UI messages, manages named surfaces, and keeps the generated UI synchronized with the latest agent output.

## DataModel

### What It Stores

The DataModel holds all data that widgets can bind to via JSON Pointer paths. When the agent sends a `dataModelUpdate` message, the DataModel is updated, and any widgets bound to the affected paths rebuild automatically.

```
Agent sends:
  { "dataModelUpdate": { "path": "/triage", "contents": [
      { "key": "category", "valueString": "plumbing" },
      { "key": "severity", "valueString": "high" }
  ]}}

DataModel state becomes:
  /triage/category = "plumbing"
  /triage/severity = "high"

Any widget bound to "/triage/category" rebuilds with new value.
```

### Binding Widgets to DataModel

Widgets reference DataModel values using JSON Pointer paths in the `{"path": "/..."}` format:

```json
{
  "id": "severity-label",
  "component": {
    "type": "Text",
    "path": "/triage/severity",
    "usageHint": "body"
  }
}
```

When `/triage/severity` changes in the DataModel, this Text widget rebuilds automatically.

### Bidirectional Binding

Interactive widgets (TextField, Checkbox) support bidirectional binding — they read from AND write to the DataModel:

```json
{
  "id": "description-input",
  "component": {
    "type": "TextField",
    "label": {"literalString": "Describe the issue"},
    "text": {"path": "/triage/description"},
    "textFieldType": "longText"
  }
}
```

When the user types, the value at `/triage/description` updates. When the agent updates `/triage/description`, the TextField reflects the new value.

### Default Values

The combined `{"path": "...", "literalString": "..."}` format provides a default when the path resolves to nothing:

```json
{
  "type": "Text",
  "path": "/triage/status",
  "literalString": "Analyzing your issue..."
}
```

If `/triage/status` exists in DataModel -> shows that value. If not -> shows "Analyzing your issue..."

## SurfaceController

### What It Does

The SurfaceController is the bridge between incoming A2UI messages and the Flutter widget tree. It:

1. **Receives A2UI messages** (surfaceUpdate, dataModelUpdate, beginRendering, deleteSurface)
2. **Builds and maintains surface state** (component map, root component, data model)
3. **Notifies listeners** when surfaces change (triggers widget rebuilds)

### Surface State

Each surface has:
- `surfaceId` — Unique name (e.g., "main", "triage-followup")
- `componentMap` — Map of component ID to component definition
- `rootComponentId` — ID of the root component (from `beginRendering`)
- `dataModel` — Key-value store (from `dataModelUpdate`)

```dart
/// Represents the rendered state of a single A2UI surface.
class SurfaceState {
  final String surfaceId;
  final Map<String, A2UIComponentDef> componentMap;
  final String rootComponentId;
  final Map<String, dynamic> dataModel;
}
```

### Processing Messages

The SurfaceController folds incoming messages into surface state:

```dart
// Pseudocode for how SurfaceController processes messages
void processMessage(A2uiMessage message) {
  if (message.hasSurfaceUpdate) {
    final update = message.surfaceUpdate;
    final surface = _getOrCreateSurface(update.surfaceId);

    // Build component map from ARRAY format (not nested tree)
    for (final entry in update.components) {
      surface.componentMap[entry.id] = entry.component;
    }
    _notifyListeners();
  }

  if (message.hasDataModelUpdate) {
    final update = message.dataModelUpdate;
    final surface = _getOrCreateSurface(update.surfaceId);
    final basePath = update.path ?? '';

    for (final entry in update.contents) {
      final fullKey = basePath.isNotEmpty
          ? '$basePath/${entry.key}'
          : entry.key;
      surface.dataModel[fullKey] = _resolveValue(entry);
    }
    _notifyListeners();
  }

  if (message.hasBeginRendering) {
    final begin = message.beginRendering;
    final surface = _getOrCreateSurface(begin.surfaceId);
    surface.rootComponentId = begin.root;
    _notifyListeners();
  }

  if (message.hasDeleteSurface) {
    _surfaces.remove(message.deleteSurface.surfaceId);
    _notifyListeners();
  }
}
```

### Gemini Resilience (Critical)

Gemini sometimes omits `beginRendering`. Add a fallback:

```dart
// After processing all messages for a surface:
if (surface.rootComponentId.isEmpty &&
    surface.componentMap.containsKey('root')) {
  surface.rootComponentId = 'root';
}
```

## Rendering Surfaces in Flutter

### Using SurfaceController with a Widget

```dart
class GenUITriageView extends StatelessWidget {
  final TriageConversationManager manager;

  const GenUITriageView({required this.manager, super.key});

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: manager.surfaceController,
      builder: (context, _) {
        final surfaces = manager.surfaceController.surfaces;
        if (surfaces.isEmpty) {
          return const Center(child: CircularProgressIndicator());
        }
        return ListView.builder(
          itemCount: surfaces.length,
          itemBuilder: (context, index) {
            final surface = surfaces[index];
            if (surface.rootComponentId.isEmpty) {
              return const SizedBox.shrink();
            }
            return GenUIRenderer(
              surface: surface,
              componentId: surface.rootComponentId,
              catalog: manager.catalog,
              onAction: (action) => manager.sendAction(action),
            );
          },
        );
      },
    );
  }
}
```

### Recursive Renderer

The `GenUIRenderer` widget recursively renders the component tree:

```dart
class GenUIRenderer extends StatelessWidget {
  final SurfaceState surface;
  final String componentId;
  final Catalog catalog;
  final ValueChanged<UserAction> onAction;

  const GenUIRenderer({
    required this.surface,
    required this.componentId,
    required this.catalog,
    required this.onAction,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    final comp = surface.componentMap[componentId];
    if (comp == null) return const SizedBox.shrink();

    // Validate against catalog
    final catalogItem = catalog.items
        .where((item) => item.name == comp.type)
        .firstOrNull;

    if (catalogItem == null) {
      // Unknown type — skip silently, log warning
      return const SizedBox.shrink();
    }

    // For standard layout types, handle children recursively
    if (comp.type == 'Column' || comp.type == 'Row') {
      return _buildLayout(context, comp);
    }
    if (comp.type == 'Card') {
      return _buildCard(context, comp);
    }

    // For custom/leaf types, use catalog builder
    return catalogItem.builder(context, comp.properties);
  }

  Widget _buildLayout(BuildContext context, A2UIComponentDef comp) {
    final childIds = comp.children?.explicitList ?? [];
    final children = childIds.map((id) => GenUIRenderer(
      surface: surface,
      componentId: id,
      catalog: catalog,
      onAction: onAction,
    )).toList();

    if (comp.type == 'Row') {
      return Row(children: children);
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: children,
    );
  }

  Widget _buildCard(BuildContext context, A2UIComponentDef comp) {
    final childId = comp.child;
    if (childId == null) return const SizedBox.shrink();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: GenUIRenderer(
          surface: surface,
          componentId: childId,
          catalog: catalog,
          onAction: onAction,
        ),
      ),
    );
  }
}
```

## Text Resolution

All text in A2UI uses typed value objects. Resolution follows this pattern:

```dart
/// Resolves a text value from either literalString or DataModel path.
String resolveText(A2UIComponentDef comp, String field, SurfaceState surface) {
  final value = comp.properties[field];
  if (value == null) return '';

  if (value is Map<String, dynamic>) {
    // Try path first (reactive binding)
    if (value.containsKey('path')) {
      final pathValue = surface.dataModel[value['path'] as String];
      if (pathValue != null) return pathValue.toString();
      // Fall back to literalString default
      if (value.containsKey('literalString')) {
        return value['literalString'] as String;
      }
      return '';
    }
    // Static literal
    if (value.containsKey('literalString')) {
      return value['literalString'] as String;
    }
  }

  // Plain string fallback (non-standard but defensive)
  if (value is String) return value;
  return '';
}
```

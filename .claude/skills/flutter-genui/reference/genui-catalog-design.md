# GenUI Catalog Design

## Overview

The **Catalog** is the central registry of widgets the AI agent is allowed to use. It is a list of `CatalogItem` objects, each defining a widget type with its JSON schema and a Dart builder function. The catalog serves as both the API contract with the AI model and the security boundary — only registered types can be rendered.

## Core Classes

### Catalog

A `Catalog` is a collection of `CatalogItem` objects. It is passed to the `Conversation` during initialization, which makes it available to the AI model (as schema) and to the renderer (as builder lookup).

```dart
import 'package:genui/genui.dart';

final triageCatalog = Catalog(
  items: [
    dropdownItem,
    freeTextItem,
    photoUploadItem,
    ratingItem,
    confirmationItem,
    // Standard A2UI types
    textItem,
    buttonItem,
    columnItem,
    rowItem,
    cardItem,
    imageItem,
  ],
);
```

### CatalogItem

Each `CatalogItem` defines:
1. **name** — The type identifier the AI uses in JSON output (must match exactly)
2. **description** — Human-readable description (sent to the model as context)
3. **schema** — JSON Schema defining the allowed properties (used for model guidance and validation)
4. **builder** — A Dart function that takes the JSON properties and returns a Flutter Widget

```dart
final dropdownItem = CatalogItem(
  name: 'dropdown',
  description: 'A dropdown selector for multiple-choice questions. '
      'Use when presenting 2-6 options for the user to choose from.',
  schema: JsonSchema.object({
    'label': JsonSchema.string(description: 'Question text displayed above the dropdown'),
    'options': JsonSchema.array(
      items: JsonSchema.string(),
      description: 'List of selectable options',
    ),
    'required': JsonSchema.boolean(description: 'Whether selection is mandatory'),
    'placeholder': JsonSchema.string(description: 'Placeholder text when no option selected'),
  }),
  builder: (context, properties) {
    final label = properties['label'] as String? ?? '';
    final options = (properties['options'] as List?)?.cast<String>() ?? [];
    final required = properties['required'] as bool? ?? false;
    return TriageDropdownWidget(
      label: label,
      options: options,
      required: required,
      placeholder: properties['placeholder'] as String?,
    );
  },
);
```

## Schema Design Principles

### 1. Be Specific in Descriptions

The description is sent to the AI model as part of the prompt. Write it so the model knows WHEN to use this widget and WHAT properties to provide.

```dart
// BAD: Vague description
CatalogItem(
  name: 'input',
  description: 'An input field',
  // ...
);

// GOOD: Specific with usage guidance
CatalogItem(
  name: 'free_text',
  description: 'A text input field for open-ended responses. '
      'Use when the user needs to provide a description, detail, or '
      'free-form answer. Supports single-line (short) and multi-line (long) modes.',
  // ...
);
```

### 2. Use JSON Schema Types Correctly

```dart
// String property
JsonSchema.string(description: 'The label text')

// Number property
JsonSchema.number(description: 'Maximum value')

// Boolean property
JsonSchema.boolean(description: 'Whether this is required')

// Array of strings
JsonSchema.array(items: JsonSchema.string())

// Enum (fixed set of values)
JsonSchema.string(
  description: 'Severity level',
  enumValues: ['low', 'medium', 'high', 'critical'],
)

// Nested object
JsonSchema.object({
  'min': JsonSchema.number(),
  'max': JsonSchema.number(),
})
```

### 3. Mark Required vs Optional Properties

The schema should clearly indicate which properties are required for the widget to function:

```dart
schema: JsonSchema.object(
  {
    'label': JsonSchema.string(description: 'Question text — always required'),
    'options': JsonSchema.array(items: JsonSchema.string()),
    'placeholder': JsonSchema.string(description: 'Optional hint text'),
  },
  required: ['label', 'options'], // Only these are required
),
```

### 4. Defensive Builder Functions

Builders receive `Map<String, dynamic>` from the AI. Never trust the shape:

```dart
builder: (context, properties) {
  // Always provide defaults for missing properties
  final label = properties['label'] as String? ?? 'Select an option';
  final options = (properties['options'] as List?)?.cast<String>() ?? [];

  // Validate before rendering
  if (options.isEmpty) {
    return const Text('No options available');
  }

  // Enforce limits
  final safeOptions = options.take(20).toList(); // Cap at 20 options

  return TriageDropdownWidget(
    label: label,
    options: safeOptions,
  );
},
```

## Catalog Granularity — Atomic Design for GenUI

Applying Brad Frost's Atomic Design to GenUI catalog items: atoms → molecules → organisms → templates → pages. The key decision is **what size building blocks to expose to the LLM**.

### The Sweet Spot: Molecules and Organisms

| Granularity | What Happens | Recommendation |
|-------------|-------------|----------------|
| **Atoms** (Text, Button, Image) | LLM controls layout, order, alignment — high risk of disjointed "Mr. Potato Head" UIs | Avoid as standalone catalog items |
| **Molecules** (SearchForm, RatingInput, PhotoUpload) | Layout within the component is fixed. LLM decides *when* and *whether* to show it | **Default choice** — consistent UX with LLM flexibility |
| **Organisms** (TriageCard, VendorProfile, LeaseSection) | Composed of molecules. LLM picks which organism to display | Good for complex, self-contained UI sections |
| **Pages** (FullTriageFlow, CompleteOnboarding) | All decisions already made — LLM has nothing to control | Defeats the purpose of GenUI |

**Rule**: Default to molecules and organisms. Use atoms only as children within larger catalog items (via `explicitList`), never as top-level catalog entries the LLM selects independently.

### Property Exposure Calibration

It's not just *which* components to expose — it's *which properties* of each component the LLM controls. Each exposed property is an additional degree of freedom.

| Property Decision | Example | Risk |
|-------------------|---------|------|
| LLM controls text content | `label: "Describe the issue"` | Low — this is the point of GenUI |
| LLM controls color/style | `color: "red"`, `fontSize: 24` | High — bypasses design system, inconsistent brand |
| LLM controls layout | `alignment: "center"`, `padding: 16` | High — visual inconsistency across sessions |
| LLM controls behavior | `maxPhotos: 10`, `multiline: true` | Medium — bound by schema validation |

**Rule**: Expose content properties (labels, options, descriptions). Lock down visual properties (colors, spacing, typography) — those come from the design system. Expose behavioral properties only when bounded by schema constraints.

### Iterative Calibration

Getting the catalog right is not a one-off decision — it's ongoing calibration:

1. Start with molecules and organisms as defaults
2. Watch what the LLM renders in production (log A2UI payloads)
3. If the LLM assembles atoms poorly → promote to a molecule
4. If a molecule is too rigid for the use case → expose one more property
5. If an organism is always used identically → consider making it a template (static)

## PropertyHarbor Triage Catalog

### 5 Custom Widget Types

| Type | Description | Key Properties |
|------|-------------|---------------|
| `photo_upload` | Camera + gallery picker for issue photos | `label`, `maxPhotos`, `required` |
| `dropdown` | Native dropdown for multiple-choice follow-ups | `label`, `options[]`, `required`, `placeholder` |
| `free_text` | Text field for open-ended responses | `label`, `hint`, `maxLength`, `multiline` |
| `rating` | Star rating for urgency/severity | `label`, `maxStars`, `required` |
| `confirmation` | Yes/No buttons for binary questions | `label`, `yesText`, `noText` |

### 6 Issue-Category Widget Sets

Each category maps to a set of widgets the AI is trained to use for that issue type:

| Category | Typical Widget Sequence |
|----------|------------------------|
| `plumbing` | Location picker (dropdown) -> severity dropdown (drip/flood/burst) -> photo upload -> availability window (free_text) |
| `hvac` | System type (dropdown: AC/heat/both) -> symptom multi-select (dropdown) -> photo upload -> last-service date (free_text) |
| `electrical` | Hazard flag (confirmation: sparks/smell) -> circuit breaker check (confirmation) -> affected outlets (rating as counter) -> photo upload |
| `appliance` | Appliance type (dropdown) -> brand/model (free_text) -> error code (free_text) -> photo upload |
| `pest_control` | Pest type (dropdown) -> sighting locations (dropdown multi) -> frequency (rating) -> confirm (confirmation) |
| `structural` | Damage type (dropdown: crack/water/collapse) -> location (dropdown) -> urgency (rating) -> photo upload |

### Standard A2UI Types (Always Include)

In addition to the 5 custom types, always register the standard A2UI component types in the catalog:

| Type | Purpose |
|------|---------|
| `Text` | Display text content (agent responses, labels) |
| `Button` | Action triggers (submit, next, cancel) |
| `Column` | Vertical layout container |
| `Row` | Horizontal layout container |
| `Card` | Content grouping container |
| `Image` | Display images (issue photos, diagrams) |
| `Divider` | Visual separator |

## Catalog Registration Pattern

```dart
// widget_catalog.dart

import 'package:genui/genui.dart';
import 'widget_types.dart';

/// PropertyHarbor triage widget catalog.
/// Registers all allowed widget types for the AI triage agent.
Catalog buildTriageCatalog() {
  return Catalog(
    items: [
      // PropertyHarbor custom triage widgets
      _photoUploadItem(),
      _dropdownItem(),
      _freeTextItem(),
      _ratingItem(),
      _confirmationItem(),

      // Standard A2UI layout/display types
      _textItem(),
      _buttonItem(),
      _columnItem(),
      _rowItem(),
      _cardItem(),
      _imageItem(),
      _dividerItem(),
    ],
  );
}
```

## Testing Catalog Items

```dart
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('TriageCatalog', () {
    late Catalog catalog;

    setUp(() {
      catalog = buildTriageCatalog();
    });

    test('contains all 12 registered widget types', () {
      expect(catalog.items.length, 12);
    });

    test('dropdown builder renders with valid properties', () {
      final item = catalog.items.firstWhere((i) => i.name == 'dropdown');
      final widget = item.builder(
        MockBuildContext(),
        {'label': 'Select severity', 'options': ['low', 'medium', 'high']},
      );
      expect(widget, isA<TriageDropdownWidget>());
    });

    test('dropdown builder handles missing options gracefully', () {
      final item = catalog.items.firstWhere((i) => i.name == 'dropdown');
      final widget = item.builder(
        MockBuildContext(),
        {'label': 'Select severity'}, // options missing
      );
      // Should render fallback, not throw
      expect(widget, isA<Widget>());
    });

    test('rejects unregistered widget type', () {
      final found = catalog.items.where((i) => i.name == 'malicious_script');
      expect(found, isEmpty);
    });
  });
}
```

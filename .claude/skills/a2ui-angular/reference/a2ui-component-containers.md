# A2UI Component Catalog — Container Components and Extensions

## Container Components

### `Card`

Elevated container with padding and optional border, holding a single child component.

```json
{
  "id": "hotel-card",
  "component": {
    "type": "Card",
    "child": "hotel-column"
  }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `child` | string | Component ID of the single child to render inside the card |

`child` is a single component ID string — not a `children` explicitList. Use a `Column` or `Row` as the child if multiple items are needed inside the card.

**Angular/daisyUI mapping:** `<div class="card bg-base-100 shadow-md">`

---

### `Modal`

Overlay dialog with a designated entry point trigger and content area.

```json
{
  "id": "booking-modal",
  "component": {
    "type": "Modal",
    "entryPointChild": "btn-open-modal",
    "contentChild": "modal-content-column"
  }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `entryPointChild` | string | Component ID of the trigger element (e.g., a Button) |
| `contentChild` | string | Component ID of the modal body content |

**Angular/daisyUI mapping:** `<dialog class="modal">` with a trigger button and modal-box content

---

### `Tabs`

Tabbed interface grouping multiple content panels.

```json
{
  "id": "search-tabs",
  "component": {
    "type": "Tabs",
    "tabItems": [
      {"title": {"literalString": "Flights"}, "child": "flights-column"},
      {"title": {"literalString": "Hotels"}, "child": "hotels-column"},
      {"title": {"literalString": "Cars"}, "child": "cars-column"}
    ]
  }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `tabItems` | array | Ordered list of tab definitions |
| `tabItems[].title` | value object | Tab button label — `{"literalString": "..."}` or `{"path": "/..."}` |
| `tabItems[].child` | string | Component ID of the tab's content panel |

**Angular/daisyUI mapping:** `<div class="tabs tabs-bordered">` with `<div role="tabpanel">`

---

### `List`

Dynamic scrollable list with template binding for repeated data.

```json
{
  "id": "results-list",
  "component": {
    "type": "List",
    "children": {
      "template": {
        "dataBinding": "/search/results",
        "componentId": "result-card-template"
      }
    }
  }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `children` | children object | Must use `template` form: `{"template": {"dataBinding": "/path/to/array", "componentId": "template-id"}}` — one rendered instance per array item |

**Angular/daisyUI mapping:** `@for` loop over data model array, each item rendered via the template component

---

## Extended Catalog (Angular/daisyUI Extensions)

The following types are not in the A2UI v0.8 core spec but are supported as renderer extensions for Angular/daisyUI deployments. They must be explicitly added to `A2UICatalogService.allowedTypes` and documented here.

| Type | Purpose | daisyUI Mapping |
|------|---------|-----------------|
| `table` | Tabular data display with column definitions and row data | `<table class="table">` |
| `chart` | Bar, line, or pie data visualization | Custom chart library wrapper |
| `badge` | Status indicator or label with semantic color variants | `<span class="badge badge-success">` |

Each extension type follows the same property format rules as official types — text fields use `{"literalString": "..."}` or `{"path": "/..."}`. Extension types must have unit tests and a property schema entry in this file before they are added to the allowlist.

---

## Extending the Catalog

To add a new component type:

1. Add the type string to `A2UICatalogService.allowedTypes`
2. Define its property schema in this file under the Extended Catalog section
3. Add a `@case` branch in `A2UIRendererComponent`
4. Map to an Angular/daisyUI component
5. Write a unit test for the new type

Unknown component types received from an agent are rejected by the renderer — they are not rendered and an error is logged. The rest of the surface renders normally.

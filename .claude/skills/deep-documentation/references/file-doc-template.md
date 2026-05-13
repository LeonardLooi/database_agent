# File Documentation Template

Applies to: single source files (`.py`, `.ts`, `.java`, `.dart`) and Angular component folders (treated as one unit).

---

## Document Header (always first line)

```
<!-- generated: {ISO8601-UTC} | skill: deep-documentation | target: file -->
```

---

## Output Path

| Mode | Path |
|------|------|
| Co-located | `{source-dir}/{filename-without-extension}.md` |
| Centralized | `docs/files/{relative-path-from-project-root}.md` |

**Angular component:** output is `{component-folder}/{component-name}.md`, covering `.ts`, `.html`, `.scss`, and `.spec.ts` as a single unit.

---

## Template

````markdown
<!-- generated: {ISO8601-UTC} | skill: deep-documentation | target: file -->

# `{filename}` — {one-line purpose}

## 1. Objective and Description

{One paragraph. What this file does, its single responsibility within the system, and where it sits in the architecture (e.g., "This service is the sole owner of user authentication logic, sitting between the API controller and the database layer").}

---

## 2. How to Use the Code

{Show concrete usage examples. Match the stack pattern:}

**Python:**
```python
from {module}.{file} import {ClassName}

instance = {ClassName}(dep1, dep2)
result = instance.{primary_method}({example_args})
```

**TypeScript (NestJS):**
```typescript
// Inject via constructor
constructor(private readonly {serviceName}: {ServiceClass}) {}

// Usage
const result = await this.{serviceName}.{primaryMethod}({exampleArgs});
```

**TypeScript (Angular component):**
```html
<!-- Selector usage in a parent template -->
<{selector} [inputProp]="value" ({outputEvent})="handler($event)"></{selector}>
```

**Java:**
```java
// Spring injection
@Autowired
private {ServiceClass} {serviceName};

// Usage
Mono<{ReturnType}> result = {serviceName}.{primaryMethod}({exampleArgs});
```

**Dart (Flutter widget):**
```dart
{WidgetName}(
  {param1}: value1,
  {param2}: value2,
  onTap: () => {},
)
```

---

## 3. Data Pipeline

{Describe how data moves through this file. Include a diagram for non-trivial flows.}

```
{Input source} → [{Transformation step 1}] → [{Transformation step 2}] → {Output destination}
```

| Stage | Description | Data shape |
|-------|-------------|-----------|
| Input | {Where data enters and from where} | `{type}` |
| Transform | {What happens to the data} | — |
| Output | {Where data goes after processing} | `{type}` |

---

## 4. Data Handling

{Describe how this file manages data quality and error states.}

- **Validation:** {What inputs are validated and how}
- **Sanitization / transformation:** {How data is cleaned or reshaped}
- **Null / empty handling:** {What happens with null, empty list, zero, or missing fields}
- **Error states:** {How errors are caught, logged, and propagated}
- **Edge cases handled:** {Any specific edge cases with explicit handling}

---

## 5. Data Contract

{Public API surface — include types. Load `docstring-patterns.md` for stack-specific format.}

### Inputs

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `{param}` | `{Type}` | Yes/No | {description} |

### Outputs / Return Types

| Method / Function | Return type | Description |
|-------------------|-------------|-------------|
| `{methodName}()` | `{ReturnType}` | {description} |

### Angular-specific (if applicable)

| Decorator | Name | Type | Description |
|-----------|------|------|-------------|
| `@Input()` | `{name}` | `{Type}` | {description} |
| `@Output()` | `{name}` | `EventEmitter<{Type}>` | {description} |
| Selector | `{selector}` | — | HTML tag used in templates |

### Exceptions / Error states

| Exception | When thrown | Caller responsibility |
|-----------|------------|----------------------|
| `{ExceptionType}` | {condition} | {how caller should handle} |

---

## 6. Data Dependencies

### Internal dependencies

| Import | From | Purpose |
|--------|------|---------|
| `{Symbol}` | `{relative-path}` | {why it's needed} |

### External dependencies

| Library | Version | Purpose |
|---------|---------|---------|
| `{package}` | `{version}` | {what it provides} |

### Infrastructure

| Resource | Access pattern | Description |
|----------|---------------|-------------|
| {Database / API / Queue / Cache} | {read / write / both} | {what is accessed} |

### Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `{ENV_VAR}` | Yes/No | {purpose} |

---

## 7. Output

{What this file produces — distinguish return values from side effects.}

### Return values

| Method | Returns | Description |
|--------|---------|-------------|
| `{method}` | `{type}` | {description} |

### Side effects

| Effect | Trigger | Description |
|--------|---------|-------------|
| DB write | `{method call}` | {what is written and to which table} |
| API call | `{method call}` | {external endpoint called} |
| Event emitted | `{method call}` | {event type and payload shape} |
| File written | `{method call}` | {path pattern and format} |
| State mutation | `{method call}` | {what state changes} |

---

## 8. Possible Bugs and Room for Improvement

{Analyze against all 10 lenses. For each finding: describe the issue, provide file location context, and suggest a fix. Write "None found" per lens if clean.}

### Lens 1 — Unhandled error paths (exceptions, nulls, empty collections)
{Finding or "None found"}

### Lens 2 — Hard-coded values or magic numbers
{Finding or "None found"}

### Lens 3 — Performance hotspots (N+1 queries, synchronous I/O in async context)
{Finding or "None found"}

### Lens 4 — Missing input validation at system boundaries
{Finding or "None found"}

### Lens 5 — Security gaps (missing auth checks, exposed sensitive data, injection risks)
{Finding or "None found"}

### Lens 6 — Deprecated API usage
{Finding or "None found"}

### Lens 7 — Missing test coverage (no corresponding test file or spec)
{Finding or "None found"}

### Lens 8 — Tight coupling / single-responsibility violations
{Finding or "None found"}

### Lens 9 — Circular or unexpected dependencies
{Finding or "None found"}

### Lens 10 — TODO / FIXME comments left in code
{Finding or "None found"}

---

## 9. Related Files

| File | Relationship |
|------|-------------|
| `{path}` | {calls this / called by this / shares types with this} |
````

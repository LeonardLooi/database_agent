# Feature Documentation Template

Applies to: a named user capability spanning ≥2 files or ≥1 folder.

**Definition:** A major feature = a named user capability that spans ≥2 files or ≥1 folder.
Entry point = the primary service / controller / route handler / Riverpod provider.
Read files in call-chain order starting from the entry point, tracing outward through the call graph. Do NOT read in filesystem order.

---

## Document Header (always first line)

```
<!-- generated: {ISO8601-UTC} | skill: deep-documentation | target: feature -->
```

---

## Output Path

| Mode | Path |
|------|------|
| Co-located | `{entry-point-folder}/{feature-name}.md` |
| Centralized | `docs/features/{feature-name}.md` |

---

## Read Strategy

1. Identify the entry point (ask the user if not obvious)
2. Read the entry point file in full
3. Identify all files called from the entry point (imports, injected dependencies, function calls)
4. Read each in call-chain order — depth-first, following the data
5. Continue until reaching leaf nodes (DB repositories, external API clients, shared utilities)
6. Read all files in full — do not skim

---

## Template

````markdown
<!-- generated: {ISO8601-UTC} | skill: deep-documentation | target: feature -->

# Feature: {Feature Name}

## 1. Objective and Description

{One to two paragraphs in user/business terms — not technical. What problem does this feature solve for the user? What can the user do because this feature exists?

Example: "The Authentication feature allows users to register accounts, log in with email and password, and maintain authenticated sessions. It issues JWT access tokens (15-minute expiry) and refresh tokens (7-day expiry), and validates identity on every protected endpoint."}

---

## 2. Entry Point

| Property | Value |
|----------|-------|
| File | `{relative-path/file.ext}` |
| Class / Function | `{ClassName}` or `{functionName}` |
| HTTP method + path | `{POST /api/v1/auth/login}` (if HTTP) |
| Trigger | {HTTP request / event / scheduled job / provider initialization} |

---

## 3. How to Use the Feature

{Developer or end-user guide. Match to the feature type.}

**HTTP feature — request/response example:**
```bash
curl -X POST https://api.example.com/v1/{endpoint} \
  -H "Content-Type: application/json" \
  -d '{
    "{field}": "{value}"
  }'

# Response
{
  "{field}": "{value}"
}
```

**Angular UI feature — component usage:**
```html
<!-- Route or component to render -->
<app-{feature-name}></ app-{feature-name}>
```
```typescript
// Route configuration
{ path: '{route}', component: {FeatureComponent} }
```

**Flutter feature — widget or provider usage:**
```dart
// Navigate to feature screen
context.push('/{route}');

// Or use the provider directly
final result = ref.watch({featureProvider});
```

**Library/service feature — programmatic usage:**
```typescript
// Import and invoke
import { {FeatureService} } from './{path}';
const service = new {FeatureService}(deps);
const result = await service.{primaryMethod}({args});
```

---

## 4. Data Pipeline

{End-to-end flow from entry point to final output. Trace every layer. Mark async boundaries with `async`.}

```
[Client / Caller]
      │
      ▼ {input type}
[{Entry point: controller / route / provider}]
      │
      ▼ {transformed type}  async
[{Service layer}]
      │
      ├──▶ [{External API / Cache}] ──▶ {response type}
      │
      ▼ {query params}
[{Repository / DB layer}]
      │
      ▼ {entity / model}
[{Service layer — post-processing}]
      │
      ▼ {response type}
[Client / Caller]
```

| Layer | File | Input | Output | Notes |
|-------|------|-------|--------|-------|
| Entry | `{file}` | `{InputType}` | `{HandlerInput}` | {validation, auth check} |
| Service | `{file}` | `{ServiceInput}` | `{ServiceOutput}` | {business logic} |
| Repository | `{file}` | `{Query}` | `{Entity}` | {DB access pattern} |
| Response | `{file}` | `{Entity}` | `{ResponseDTO}` | {mapping / serialization} |

---

## 5. Data Handling

{How data is managed across the full feature lifecycle.}

- **Entry validation:** {Which layer validates input, what rules apply, what happens on invalid input}
- **Data transformation:** {How raw input becomes business objects; how entities become responses}
- **Error handling strategy:** {How errors propagate from DB → service → controller → client}
- **Null / empty handling:** {How missing data is handled at each layer}
- **Concurrency / async:** {Race conditions addressed, transaction boundaries, async patterns used}
- **Caching:** {What is cached, TTL, invalidation strategy — or "None"}

---

## 6. Data Contract

{All contracts between layers and with the outside world.}

### External API contract (HTTP / GraphQL / event)

| Direction | Type | Schema | Description |
|-----------|------|--------|-------------|
| Request | `{RequestDTO}` | {fields and types} | {what the caller sends} |
| Response (success) | `{ResponseDTO}` | {fields and types} | {what the caller receives} |
| Response (error) | `{ErrorSchema}` | {status code, message shape} | {error responses} |

### Inter-layer contracts

| From | To | Contract type | Shape |
|------|----|--------------|-------|
| Controller → Service | `{CommandType}` | method call | `{field: Type}` |
| Service → Repository | `{QueryType}` | method call | `{field: Type}` |
| Repository → Service | `{EntityType}` | return value | `{field: Type}` |

### Events emitted / consumed

| Direction | Event | Payload | Consumers / Producers |
|-----------|-------|---------|----------------------|
| Emitted | `{EventName}` | `{PayloadType}` | {downstream consumer} |
| Consumed | `{EventName}` | `{PayloadType}` | {upstream producer} |

### Shared types / interfaces

| Type | File | Used by |
|------|------|---------|
| `{TypeName}` | `{file}` | {list of files} |

### Database schema owned by this feature

| Table / Collection | Key columns | Access pattern |
|--------------------|-------------|---------------|
| `{table_name}` | `{col1}`, `{col2}` | {read/write/own} |

---

## 7. Data Dependencies

{What this feature depends on from outside itself.}

### Other features / modules

| Feature / Module | Dependency | Why |
|------------------|-----------|-----|
| `{FeatureName}` | `{Symbol}` | {what is needed from it} |

### External services

| Service | Protocol | Purpose | Failure impact |
|---------|----------|---------|----------------|
| `{ServiceName}` | REST / gRPC / SDK | {what it provides} | {what breaks if unavailable} |

### Infrastructure

| Resource | Type | Access | Owner file |
|----------|------|--------|-----------|
| `{resource}` | DB / Queue / Cache / Storage | read/write | `{file}` |

### Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `{ENV_VAR}` | Yes/No | {purpose} |

---

## 8. Output

{What this feature produces.}

### Primary outputs

| Output | Type | Description |
|--------|------|-------------|
| {HTTP response / return value / rendered UI} | `{Type}` | {description} |

### Side effects

| Effect | Trigger | Description |
|--------|---------|-------------|
| DB write | `{layer}.{method}` | {table, what is written, frequency} |
| Event emitted | `{layer}.{method}` | {event type, payload, consumers} |
| External API call | `{layer}.{method}` | {endpoint, method, payload} |
| Notification / email | `{layer}.{method}` | {recipient, content, trigger} |
| File / storage write | `{layer}.{method}` | {path pattern, format} |
| Cache update | `{layer}.{method}` | {cache key, TTL} |

---

## 9. Modules Involved

{All files that participate in this feature, in call-chain order.}

| # | Module | File | Responsibility |
|---|--------|------|---------------|
| 1 | Entry point | `{file}` | {what it does in this feature} |
| 2 | {Layer name} | `{file}` | {what it does in this feature} |
| 3 | {Layer name} | `{file}` | {what it does in this feature} |
| N | Leaf node | `{file}` | {what it does in this feature} |

---

## 10. Possible Bugs and Room for Improvement

{Feature-level analysis — assess the feature end-to-end, not individual files in isolation.}

### Lens 1 — Unhandled error paths (exceptions, nulls, empty collections across layers)
{Finding or "None found"}

### Lens 2 — Hard-coded values or magic numbers
{Finding or "None found"}

### Lens 3 — Performance hotspots (N+1 queries, missing indexes, sync I/O in async path)
{Finding or "None found"}

### Lens 4 — Missing input validation at system boundaries
{Finding or "None found"}

### Lens 5 — Security gaps (missing auth/authz, data exposure, injection risks)
{Finding or "None found"}

### Lens 6 — Deprecated API usage
{Finding or "None found"}

### Lens 7 — Missing test coverage (no integration or e2e tests for the full flow)
{Finding or "None found"}

### Lens 8 — Tight coupling between layers / single-responsibility violations
{Finding or "None found"}

### Lens 9 — Circular or unexpected cross-feature dependencies
{Finding or "None found"}

### Lens 10 — TODO / FIXME comments across any file in this feature
{Finding or "None found"}

---

## 11. Related Features

| Feature | Relationship |
|---------|-------------|
| `{FeatureName}` | {depends on / depended on by / shares contracts with / peer feature} |
````

# Folder Documentation Template

Applies to: a single directory. Documents all immediate files and their relationships.
Default scope: one level deep. Sub-folders are referenced but not recursed into unless explicitly requested.

---

## Document Header (always first line)

```
<!-- generated: {ISO8601-UTC} | skill: deep-documentation | target: folder -->
```

---

## Output Path

| Mode | Path |
|------|------|
| Co-located | `{folder}/README.md` |
| Centralized | `docs/folders/{relative-folder-path-from-project-root}.md` |

---

## Read Strategy

Read all files in the folder in full before writing any section. For large folders (>15 files), read all files — do not skim. Accuracy over speed.

---

## Template

````markdown
<!-- generated: {ISO8601-UTC} | skill: deep-documentation | target: folder -->

# `{folder-name}/` — {one-line purpose}

## 1. Objective and Description

{One to two paragraphs. What this folder/module is responsible for in the system. Its role in the architecture (e.g., "This folder owns all authentication logic — token issuance, validation, and session management — and is the single entry point for auth from the rest of the API layer").}

---

## 2. Files in This Folder

{List every immediate file. Exclude sub-folders here — reference them in section 11.}

| File | Purpose | Key exports |
|------|---------|-------------|
| `{filename}` | {one-line purpose} | `{ExportedClass}`, `{exportedFn}` |

---

## 3. Data Flow Between Files

{How files within this folder interact with each other. Use a diagram for folders with ≥3 files.}

```
{file-a} --[calls]--> {file-b}
{file-b} --[returns {Type}]--> {file-a}
{file-c} --[reads from]--> {file-b}
```

| Interaction | From | To | Data passed |
|-------------|------|----|------------|
| {description} | `{file-a}` | `{file-b}` | `{Type}` |

---

## 4. Data Pipeline

{End-to-end data flow through this folder as a module.}

```
[Entry point from outside] → {file-a} → {file-b} → {file-c} → [Exit to outside]
```

| Stage | File | Description | Data shape |
|-------|------|-------------|-----------|
| Entry | `{file}` | {how data arrives in this folder} | `{Type}` |
| Processing | `{file}` | {transformations applied} | `{Type}` |
| Exit | `{file}` | {how data leaves this folder} | `{Type}` |

---

## 5. Data Handling

{Shared data handling patterns across the folder.}

- **Validation approach:** {how the folder validates incoming data — which file owns validation}
- **Error propagation:** {how errors are passed between files and out of the folder}
- **Null / empty handling:** {folder-level conventions for handling missing data}
- **Shared utilities:** {utility files within the folder used by multiple siblings}

---

## 6. Data Contract

{What this folder exposes to the rest of the system.}

### Public exports (consumed by code outside this folder)

| Symbol | Type | File | Description |
|--------|------|------|-------------|
| `{ClassName}` | class | `{file}` | {what it does for callers} |
| `{functionName}` | function | `{file}` | {what it does for callers} |
| `{InterfaceName}` | interface/type | `{file}` | {shape it defines} |

### Events emitted (if applicable)

| Event | Emitted from | Payload type | Description |
|-------|-------------|-------------|-------------|
| `{EventName}` | `{file}` | `{Type}` | {when and why emitted} |

### Database tables / collections owned by this folder

| Table / Collection | Access | File responsible |
|--------------------|--------|-----------------|
| `{table_name}` | read/write | `{file}` |

---

## 7. Data Dependencies

{What this folder depends on from outside itself.}

### Internal (other folders in this project)

| Folder | Imports | Purpose |
|--------|---------|---------|
| `{other-folder}/` | `{Symbol}` | {why needed} |

### External libraries

| Library | Version | Used by | Purpose |
|---------|---------|---------|---------|
| `{package}` | `{version}` | `{file}` | {what it provides} |

### Infrastructure

| Resource | Access | Files | Description |
|----------|--------|-------|-------------|
| {Database / API / Queue / Cache} | read/write | `{file}` | {what is accessed} |

### Environment variables

| Variable | Required | Consumed by | Description |
|----------|----------|------------|-------------|
| `{ENV_VAR}` | Yes/No | `{file}` | {purpose} |

---

## 8. Output

{What this folder produces for the rest of the system.}

### Return values / responses

| Entry point | Output | Description |
|-------------|--------|-------------|
| `{file}.{method}()` | `{Type}` | {description} |

### Side effects

| Effect | Triggered by | Description |
|--------|-------------|-------------|
| DB write | `{file}.{method}` | {table and what is written} |
| API call | `{file}.{method}` | {external endpoint and payload} |
| Event emitted | `{file}.{method}` | {event and consumer} |
| State mutation | `{file}.{method}` | {what state changes} |

---

## 9. How to Use This Module

{How a developer imports and uses this folder's public API from elsewhere in the project.}

**Python:**
```python
from {package}.{folder} import {ClassName}
result = {ClassName}().{primary_method}({args})
```

**TypeScript (NestJS):**
```typescript
import { {ClassName} } from './{folder}';
// Inject or instantiate and call primary method
```

**TypeScript (Angular):**
```typescript
import { {FeatureModule} } from './{folder}/{feature}.module';
// Add to imports array in consuming module
```

**Java:**
```java
import com.{org}.{folder}.{ClassName};
// Inject via @Autowired or constructor injection
```

**Dart:**
```dart
import 'package:{app}/{folder}/{file}.dart';
// Use exported widget or class
```

---

## 10. Possible Bugs and Room for Improvement

{Folder-level analysis — assess the folder as a whole, not individual files. For per-file findings, see each file's own documentation.}

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

### Lens 7 — Missing test coverage (no test folder or insufficient spec files)
{Finding or "None found"}

### Lens 8 — Tight coupling / single-responsibility violations across files
{Finding or "None found"}

### Lens 9 — Circular or unexpected dependencies between files in this folder
{Finding or "None found"}

### Lens 10 — TODO / FIXME comments left in any file in this folder
{Finding or "None found"}

---

## 11. Sub-folders and Related Areas

### Sub-folders (not recursed — document separately if needed)

| Sub-folder | Purpose |
|------------|---------|
| `{sub-folder}/` | {one-line purpose} |

### Related folders

| Folder | Relationship |
|--------|-------------|
| `{folder}/` | {calls into this / called by this / shares types / peer module} |
````

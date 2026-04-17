---
name: typescript-advanced-types
description: "Master TypeScript's advanced type system — generics, conditional types, mapped types, template literals, and utility types — for building type-safe Angular 21.x components, NestJS 11.x APIs, and MCP Builder integrations. Use when implementing complex type inference, type-safe API clients, branded types, DeepPartial/DeepReadonly patterns, or migrating JS to TS."
allowed-tools: Read
metadata:
  triggers: "Generic types, Conditional types, Mapped types, Utility types, Template literal types, Type-safe API client, Type-safe form, DeepPartial, DeepReadonly, Branded types, type inference"
  related-skills: nestjs-api, angular-spa, mcp-builder, nestjs-coding-standard, typescript-expert, typescript-pro
  domain: backend
  role: specialist
  scope: implementation
  output-format: code
  risk: safe
  source: "antigravity-awesome-skills (community)"
  date_added: "2026-03-14"
last-reviewed: "2026-03-14"
---

# TypeScript Advanced Types

> **Iron Law:** Before applying any type pattern, READ the actual TypeScript file first. Do not suggest type changes from memory — verify the actual code (file:line) before making any claim.

## When to Use

- Building type-safe libraries or frameworks
- Creating reusable generic components
- Implementing complex type inference logic
- Designing type-safe API clients
- Building form validation systems
- Creating strongly-typed configuration objects
- Implementing type-safe state management
- Migrating JavaScript codebases to TypeScript

## Do Not Use

- The task is unrelated to TypeScript advanced types
- You need a different domain or tool outside this scope (Flutter/Dart, Java, Python)

## Core Type Patterns

### 1. Generics
Create reusable, type-flexible components while maintaining type safety. Use generic constraints (`T extends HasLength`) to narrow what types are accepted. Supports multiple type parameters, default types, and conditional constraints. See playbook §1 for examples.

### 2. Conditional Types
Create types that depend on conditions: `T extends string ? true : false`. Supports `infer` for extracting type components (e.g., return type, promise type, array element type). Distributive conditional types apply over union members automatically. See playbook §2 for examples.

### 3. Mapped Types
Transform existing types by iterating over their properties with `[P in keyof T]`. Supports modifiers (`readonly`, `?`), key remapping via `as`, and filtering properties by type. Enables patterns like `Partial<T>`, `Readonly<T>`, and `Getters<T>`. See playbook §3 for examples.

### 4. Template Literal Types
Create string-based types with pattern matching: `` `on${Capitalize<EventName>}` ``. Enables type-safe event names, path builders, getter/setter name generation. Built-in helpers: `Uppercase`, `Lowercase`, `Capitalize`, `Uncapitalize`. See playbook §4 for examples.

### 5. Utility Types
TypeScript's built-in transformation utilities: `Partial<T>`, `Required<T>`, `Readonly<T>`, `Pick<T,K>`, `Omit<T,K>`, `Exclude<T,U>`, `Extract<T,U>`, `NonNullable<T>`, `Record<K,T>`. Combine with custom mapped types for `DeepPartial<T>` and `DeepReadonly<T>`. See playbook §5 and Pattern 4 for examples.

## Tech Stack Applicability

| Stack | Applicable | Notes |
|-------|-----------|-------|
| Angular 21.x | Yes | Type-safe forms, component inputs, RxJS operator types, signal types |
| NestJS 11.x | Yes | Type-safe DTOs, guards, interceptors, Prisma query result types |
| MCP Builder (TypeScript) | Yes | Type-safe tool definitions, request/response contracts |
| Flutter / Dart | No | Dart has its own type system — use the flutter-mobile skill |
| Java / Spring Boot | No | Java generics differ significantly — use the java-spring-api skill |
| Python / FastAPI | No | Use Pydantic models via the python-dev skill |

## Resources

`resources/implementation-playbook.md` contains full patterns, checklists, and code samples covering:

- **Core Concepts:** Generics, Conditional Types, Mapped Types, Template Literal Types, Utility Types
- **Advanced Patterns:**
  - Pattern 1: Type-Safe Event Emitter
  - Pattern 2: Type-Safe API Client
  - Pattern 3: Builder Pattern with Type Safety
  - Pattern 4: Deep Readonly / Deep Partial
  - Pattern 5: Type-Safe Form Validation
  - Pattern 6: Discriminated Unions
- **Type Inference Techniques:** `infer` keyword, Type Guards, Assertion Functions
- **Best Practices:** 10 rules including `unknown` over `any`, strict mode, type testing
- **Common Pitfalls and Performance Considerations**

## Related Skills

| Combine With | When |
|-------------|------|
| `nestjs-api` | Typing NestJS DTOs, guards, interceptors, Prisma result shapes with advanced utility types |
| `angular-spa` | Typing Angular reactive forms, component inputs/outputs, RxJS pipe operators |
| `mcp-builder` | Defining type-safe tool schemas, strongly-typed request/response contracts for MCP tools |

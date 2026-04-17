---
name: typescript-pro
description: TypeScript architecture design specialist for strict type safety, decorator and metadata programming, type-safe configuration, and module-level type contracts — use when architecting shared types, hardening type safety, or designing enterprise-grade TypeScript patterns for NestJS, Angular, or MCP servers.
allowed-tools: Read
metadata:
  triggers: TypeScript architecture, Type-safe design, Decorator design, Type safety hardening, Strict TypeScript, Type contract, TypeScript enterprise, Module type contracts, Metadata programming, Shared types
  related-skills: typescript-advanced-types, typescript-expert, nestjs-coding-standard, angular-spa, nestjs-api, mcp-builder
  domain: backend
  role: specialist
  scope: design
  output-format: code
  risk: safe
  source: "antigravity-awesome-skills (community)"
  date_added: "2026-03-14"
last-reviewed: "2026-03-16"
---

> **Iron Law:** Before designing any TypeScript architecture, READ the actual source files and existing type definitions first. Do not propose type contracts from memory — verify the actual code (file:line) before making any claim.

You are a TypeScript expert specializing in advanced typing and enterprise-grade development.

## When to Use

- Designing TypeScript architectures or shared types across NestJS, Angular, or MCP server projects
- Solving complex typing, generics, or inference issues
- Hardening type safety for production systems
- Designing decorator-based APIs (NestJS guards, interceptors, pipes, Angular components)
- Creating enterprise shared type libraries used across multiple services

## Do Not Use

- You only need JavaScript guidance with no TypeScript in the build pipeline
- You cannot enforce TypeScript in the build pipeline
- You need UI/UX design rather than type design
- The task is Flutter/Dart or Python — those have dedicated skills

## Focus Areas

- Advanced type systems (generics, conditional types, mapped types)
- Strict TypeScript configuration and compiler options
- Type inference optimization and utility types
- Decorators and metadata programming (NestJS guards, interceptors, Angular components)
- Module systems and namespace organization
- Enterprise shared type libraries used across NestJS and Angular workspaces

## Approach

1. Define runtime targets and strictness requirements — confirm `tsconfig.json` `strict: true` baseline
2. Model types and contracts for critical surfaces before writing implementation code
3. Implement with compiler and linting safeguards (`noImplicitAny`, `strictNullChecks`, `exactOptionalPropertyTypes`)
4. Validate build performance and developer ergonomics — avoid over-generic types that destroy IDE hints
5. Implement proper error boundaries with typed exceptions and discriminated union result types

## Output

- Strongly-typed TypeScript with comprehensive interfaces
- Generic functions and classes with proper constraints
- Custom utility types and advanced type manipulations
- Jest/Vitest tests with proper type assertions
- TSConfig optimization for project requirements
- Type declaration files (.d.ts) for external libraries

## Tech Stack Applicability

| Stack | Applicable |
|-------|-----------|
| Angular 21.x | yes |
| NestJS 11.x | yes |
| MCP Builder TypeScript | yes |
| Flutter / Dart | no |
| Java / Spring Boot | no |
| Python / FastAPI | no |

## Workspace Examples

### 1. NestJS type-safe config hierarchy using branded types

```typescript
// Branded type prevents raw strings from being passed as config values
type DatabaseUrl = string & { readonly __brand: 'DatabaseUrl' };

function asDatabaseUrl(raw: string): DatabaseUrl {
  if (!raw.startsWith('postgresql://')) throw new Error('Invalid DB URL');
  return raw as DatabaseUrl;
}

interface AppConfig {
  database: { url: DatabaseUrl; poolSize: number };
  auth: { jwtSecret: string; expiresIn: number };
}
```

### 2. Custom NestJS decorator with type extraction

```typescript
import { SetMetadata } from '@nestjs/common';

export const ROLES_KEY = 'roles';
export type Role = 'admin' | 'user' | 'guest';

// Type-safe decorator — enforces only valid Role values at call site
export const Roles = (...roles: Role[]) => SetMetadata(ROLES_KEY, roles);

// Guard reads metadata with full type safety
const requiredRoles = this.reflector.getAllAndOverride<Role[]>(ROLES_KEY, [
  context.getHandler(),
  context.getClass(),
]);
```

### 3. Angular generic service interface design

```typescript
// Generic CRUD service interface — Angular services implement per entity
interface CrudService<T, CreateDto, UpdateDto> {
  findAll(): Observable<T[]>;
  findOne(id: string): Observable<T>;
  create(dto: CreateDto): Observable<T>;
  update(id: string, dto: UpdateDto): Observable<T>;
  remove(id: string): Observable<void>;
}

// Concrete implementation bound to specific types
@Injectable({ providedIn: 'root' })
export class UserService implements CrudService<User, CreateUserDto, UpdateUserDto> {
  // compiler enforces all 5 methods with correct signatures
}
```

## Related Skills

- **nestjs-coding-standard** — combine when the type design is inside a NestJS service or controller; that skill enforces naming, module structure, and Fastify-specific patterns on top of the type contracts designed here
- **typescript-advanced-types** — combine when the problem requires deep utility type manipulation (template literal types, infer, recursive mapped types) beyond standard enterprise patterns
- **angular-spa** — combine when designing Angular-specific type contracts (component inputs/outputs, reactive form types, RxJS operator typing)
- **mcp-builder** — combine when designing TypeScript type contracts for MCP server tools and resource handlers

## TypeScript Code Quality Rules

These rules apply across all TypeScript stacks (NestJS, Angular, MCP servers). Full patterns with examples are in `nestjs-coding-standard` — this is the authoritative cross-stack reference.

**Immutability** — Never mutate objects or arrays in place. Use spread (`{ ...obj, key: val }`, `[...arr, item]`). Shared references (Prisma entities, DTOs) are especially dangerous to mutate.

**No magic numbers** — Extract all numeric/string literals to named constants (`MAX_RETRY_ATTEMPTS`, `DEFAULT_PAGE_SIZE`). Unnamed literals are a bug waiting for context.

**Early returns** — Use guard clauses instead of nesting. Max 2 levels of nesting. Throw/return early, process late.

**Parallel async** — Use `Promise.all([...])` when multiple independent async calls are made in the same function. Sequential `await` for independent calls is a latency bug.

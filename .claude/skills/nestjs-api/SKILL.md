---
name: nestjs-api
description: This skill provides patterns and templates for NestJS 11.x with Fastify, Prisma ORM, and TypeScript 5.x development. It should be activated when creating NestJS modules, controllers, services, DTOs, guards, interceptors, or tests.
allowed-tools: Bash, Read, Write, Edit
metadata:
  triggers: NestJS, Nest, TypeScript backend, NestJS module, NestJS controller, NestJS service, Fastify, Prisma, NestJS guard
  related-skills: nestjs-coding-standard, openapi-spec-generation, database-schema-designer
  domain: backend
  role: specialist
  scope: implementation
  output-format: code
last-reviewed: "2026-03-14"
---

## Iron Law

**NO NESTJS MODULE WITHOUT READING `reference/nestjs-conventions.md` FIRST — Fastify adapter quirks, Prisma 7.x patterns, and DTO validation rules are defined there**

# NestJS 11.x + Fastify + Prisma REST API Skill

## Conventions & Rules

> For code conventions, package layout, NestJS rules, Prisma 7.x rules, and environment file rules, read `reference/nestjs-conventions.md`

## Quick Scaffold — New NestJS Project

```bash
# Using NestJS CLI
npx @nestjs/cli new my-service --package-manager npm --strict
```

## Process

1. **Scaffold** using NestJS CLI or the command above
2. **Configure** package.json and tsconfig — read `reference/nestjs-config-basics.md`, `reference/nestjs-config-npm-ts.md`, and `reference/nestjs-config-prisma7.md`
3. **Create files** using templates — read `reference/nestjs-templates-core.md` for main.ts, AppModule, CoreModule; read `reference/nestjs-templates-features.md` for feature modules, controllers, services, DTOs
4. **Follow conventions** below for package layout and NestJS rules
5. **Write tests** with Vitest + supertest or NestJS Testing utilities
6. **Format and check**: `npm run lint && npm run typecheck`

## Key Patterns

| Pattern | Implementation |
|---------|---------------|
| **Modules** | `@Module()` with imports/providers/exports, aggregation pattern |
| **Controllers** | `@Controller('api/v1/...')` with route decorators |
| **Services** | `@Injectable()` with constructor injection |
| **DTOs** | Classes with `class-validator` decorators (`@IsString()`, `@IsNotEmpty()`) |
| **Repositories** | Prisma Client via `DatabaseService` wrapper |
| **Error handling** | `@Catch()` exception filter returning `ProblemDetail` (RFC 9457) |
| **Config** | Fail-fast `registerAs()` with static config reader |
| **Migrations** | Prisma Migrate in `prisma/migrations/` |
| **Guards** | `@UseGuards()` for auth (`JwtAuthGuard`, `RolesGuard`) |
| **Interceptors** | `LoggingInterceptor`, `TransformInterceptor` (global) |
| **Pipes** | Global `ValidationPipe` with whitelist and transform |

## Reference Files

| File | Content | Load When |
|------|---------|-----------|
| `reference/nestjs-config-basics.md` | Static config reader, config module aggregation, fail-fast validation | Project setup, initial configuration |
| `reference/nestjs-config-npm-ts.md` | package.json with dependencies, tsconfig.json | Project setup, configuring dependencies |
| `reference/nestjs-config-prisma7.md` | Prisma 7.x schema, prisma.config.ts, PrismaService, .env template | Setting up database, writing Prisma queries |
| `reference/nestjs-templates-core.md` | main.ts, app.module, core.module templates | Bootstrapping app, creating core module |
| `reference/nestjs-templates-features.md` | Feature module, controller, service, DTO templates | Creating modules, controllers, services |
| `reference/nestjs-templates-infrastructure.md` | Dockerfile, docker-compose, Vitest config | Containerizing app, configuring test runner |
| `reference/nestjs-enterprise-patterns.md` | Exception hierarchy, validation pipe, API versioning | Implementing error handling, input validation, API versioning |
| `reference/nestjs-enterprise-infrastructure.md` | Security middleware (Helmet), rate limiting, Swagger, health checks | Adding security headers, rate limiting, API documentation |
| `reference/nestjs-resilience-circuit-breaker.md` | Circuit breaker, retry, timeout, database fallback | Adding resilience patterns, handling service failures |
| `reference/nestjs-resilience-context.md` | Request context with AsyncLocalStorage, correlation IDs | Adding request tracing, correlation IDs |
| `reference/nestjs-feature-flags.md` | Feature flags service, Redis fallback, gradual rollout | Implementing feature flags, gradual rollout |
| `reference/nestjs-observability.md` | OpenTelemetry tracing/metrics, structured logging, cloud logging | Adding observability, structured logging, tracing |
| `reference/nestjs-messaging-basics.md` | BullMQ queues, background job processing | Adding background jobs, queue processing |
| `reference/nestjs-messaging-queues.md` | RabbitMQ reliable messaging, dead letter queues | Implementing RabbitMQ messaging, dead letter queues |
| `reference/nestjs-messaging-streaming.md` | Kafka event streaming, high-throughput patterns | Implementing Kafka streaming, high-throughput events |
| `reference/nestjs-testing-unit-basics.md` | Unit testing with Vitest, service test patterns | Writing unit tests for services |
| `reference/nestjs-testing-unit-controllers.md` | Controller unit tests, test data factories | Writing unit tests for controllers |
| `reference/nestjs-testing-unit-mocks.md` | Prisma/Redis/HTTP mocking, ConfigService mocking | Mocking dependencies in unit tests |
| `reference/nestjs-testing-integration-setup.md` | E2E testing setup, Testcontainers, supertest | Writing integration tests, E2E tests |
| `reference/nestjs-testing-integration-patterns.md` | Auth testing, validation, pagination patterns | Testing auth flows, pagination, validation |
| `reference/nestjs-testing-patterns.md` | Circuit breaker testing, AsyncLocalStorage testing | Testing resilience patterns, context propagation |
| `reference/nestjs-testing-ci-troubleshooting.md` | Coverage standards, CI/CD, troubleshooting | Configuring CI pipelines, coverage thresholds |
| `reference/nestjs-rest-workflow.md` | REST workflow, OpenAPI/Swagger controller setup | Designing REST endpoints, setting up Swagger |
| `reference/nestjs-rest-dto-pagination.md` | DTO mapping, pagination, filter patterns | Creating DTOs, implementing pagination |
| `reference/nestjs-rest-upload-errors.md` | File uploads, API versioning, ProblemDetail errors | Implementing file uploads, error responses |
| `reference/nestjs-rest-services.md` | Service patterns, external API clients, bulk operations, soft delete | Writing service logic, calling external APIs |
| `reference/nestjs-security-auth.md` | JWT authentication (RS256), password hashing, token management | Implementing JWT auth, implementing guards |
| `reference/nestjs-security-scanning.md` | OWASP scanning, security headers, static analysis | Security auditing, dependency scanning |
| `reference/nestjs-security-validation-logging.md` | Input validation, PII masking, Prisma security | Securing input handling, masking sensitive data |
| `reference/nestjs-debugging-logging.md` | Debug mode, Prisma query logging, Fastify lifecycle | Debugging requests, tracing Prisma queries |
| `reference/nestjs-debugging-context-di.md` | AsyncLocalStorage context, DI debugging, config | Debugging DI issues, context propagation |
| `reference/nestjs-debugging-performance.md` | Memory leaks, performance profiling | Diagnosing memory leaks, profiling performance |
| `reference/nestjs-debugging-production.md` | Production debugging, structured logging, tracing | Debugging production issues, structured logging |
| `reference/nestjs-review-checklist.md` | NestJS review checklist (used by `nestjs-reviewer` agent) | Code review, pre-PR checklist |
| `reference/nestjs-real-world-issues.md` | 9 framework-level issues from GitHub/SO with frequency ratings and Vitest-adapted solutions | Debugging DI errors, circular deps, JWT config, memory leaks |
| `reference/nestjs-decision-trees.md` | Decision trees for module organization, auth method, testing strategy, caching, error responses | Architecture decisions before implementation |

## Common Commands

```bash
npm run start:dev                           # Run in dev mode (watch)
npm test                                    # Run unit tests (Vitest)
npm run test:e2e                            # Run integration/E2E tests
npm run test:cov                            # Run tests with coverage report
npm run lint                                # ESLint check
npm run typecheck                           # TypeScript type-check only
npm run build                               # Compile TypeScript
npx prisma migrate dev --name <migration>   # Create and run migration
npx prisma generate                         # Regenerate Prisma client after schema change
npx prisma studio                           # Open Prisma Studio GUI
```

## Documentation Sources

Before generating code, consult these sources for current syntax and APIs:

| Source | URL / Tool | Purpose |
|--------|-----------|---------|
| Prisma ORM | `https://www.prisma.io/docs/llms.txt` | Prisma schema, migrations, client API |
| NestJS / TypeScript | `Context7` MCP | Latest NestJS decorators, modules, patterns |

## Error Handling

**Validation errors**: Use `class-validator` decorators on DTO classes. Global ValidationPipe auto-returns 422 with details.

**Not-found errors**: Throw `NotFoundException` from services. Global exception filter returns structured 404.

**Duplicate errors**: Catch Prisma `P2002` unique constraint violation and convert to `409 Conflict`.

## Hard Prohibitions

- No raw `any` request bodies — all endpoints must use DTOs with `class-validator` decorators
- No raw SQL unless performance-critical (document why in a comment)
- No `jest` in new code — use Vitest exclusively
- `@UseGuards(JwtAuthGuard)` on every non-public route — no exceptions
- No arbitrary Tailwind values (`p-[13px]`) — use the scale (`p-4`, `gap-6`)
- Angular: no `*ngIf`/`*ngFor` — use `@if`/`@for`/`@switch`; typed reactive forms `FormGroup<T>` only

## Post-Code Review

After writing TypeScript code, dispatch these reviewer agents:
- `nestjs-reviewer` — module correctness, Prisma usage, resilience patterns
- `code-reviewer` — general quality, DRY, error handling
- `security-reviewer` — auth, input validation, OWASP Top 10

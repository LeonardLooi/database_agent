# Implementation Guidelines Reference

## Code Organization

### DDD Layer Architecture

```
<bounded-context>/
├── api/                    # Interface/Adapter layer (inbound)
│   ├── rest/               # REST controllers/handlers
│   ├── graphql/            # GraphQL resolvers (if applicable)
│   ├── grpc/               # gRPC services (if applicable)
│   └── dto/                # Request/Response objects (API-facing)
│
├── application/            # Application layer (use case orchestration)
│   ├── commands/           # Command handlers (write operations)
│   ├── queries/            # Query handlers (read operations)
│   ├── services/           # Application services (orchestration)
│   └── ports/              # Inbound ports (interfaces the app exposes)
│
├── domain/                 # Domain layer (pure business logic)
│   ├── model/              # Aggregates, entities, value objects
│   ├── events/             # Domain event definitions
│   ├── services/           # Domain services (multi-entity logic)
│   ├── repositories/       # Repository interfaces (NOT implementations)
│   └── exceptions/         # Domain-specific exceptions
│
├── infrastructure/         # Infrastructure layer (outbound adapters)
│   ├── persistence/        # Repository implementations, ORM config
│   ├── messaging/          # Event publisher/subscriber implementations
│   ├── external/           # External service clients (ACL lives here)
│   └── config/             # Framework configuration
│
└── shared/                 # Shared kernel (if applicable)
    ├── types/              # Common value objects (Money, etc.)
    └── events/             # Shared event schemas
```

### Dependency Rule

```
API → Application → Domain ← Infrastructure

Domain depends on NOTHING (pure business logic)
Application depends on Domain
Infrastructure IMPLEMENTS Domain interfaces
API calls Application services
```

- Domain layer has ZERO framework imports
- Repository interfaces in domain, implementations in infrastructure
- Framework annotations only in API and infrastructure layers

### Module Boundary Enforcement

For modular monolith, enforce boundaries:

- Each bounded context is a top-level module/package
- Modules communicate ONLY through defined interfaces (published API or events)
- No direct import of another module's internal classes
- Shared kernel module for truly shared concepts (kept minimal)

## Testing Strategy

### Test Pyramid Per Bounded Context

```
        ╱╲
       ╱ E2E ╲          Few: Critical user journeys only
      ╱────────╲
     ╱ Contract  ╲       Medium: API contracts between contexts
    ╱──────────────╲
   ╱  Integration    ╲    Medium: DB, messaging, external services
  ╱────────────────────╲
 ╱     Unit Tests        ╲  Many: Domain logic, value objects, aggregates
╱──────────────────────────╲
```

### What to Test Where

| Layer | Test Type | What to Verify |
|-------|-----------|---------------|
| **Domain** | Unit | Aggregate invariants, entity behavior, value object validation |
| **Application** | Unit + Integration | Use case orchestration, command/query handling |
| **Infrastructure** | Integration | Repository works against real DB, event publishing |
| **API** | Integration | HTTP status codes, serialization, validation |
| **Cross-context** | Contract | API contracts, event schemas |
| **End-to-end** | E2E | Critical business flows across contexts |

### Domain Layer Testing Guidelines

```
For each aggregate, test:
- [ ] All invariants are enforced (invalid state rejected)
- [ ] State transitions produce correct domain events
- [ ] Edge cases: null, empty, boundary values
- [ ] Concurrency: optimistic locking works

For each value object, test:
- [ ] Equality by value (not reference)
- [ ] Immutability (no mutation methods)
- [ ] Validation rejects invalid construction
```

### Contract Testing

Between bounded contexts, verify:

- Provider publishes the schema it promised
- Consumer can parse the schema it expects
- Breaking changes are caught before deployment

## Security Architecture

### Authentication & Authorization

| Concern | Pattern |
|---------|---------|
| Identity | Centralized identity provider (OAuth2/OIDC) |
| Token | JWT with minimal claims, short expiry |
| Authorization | Role-based (RBAC) or attribute-based (ABAC) per bounded context |
| API gateway | Token validation, rate limiting at the edge |
| Service-to-service | Mutual TLS or service tokens (not user tokens) |

### Per-Context Security

Each bounded context enforces its OWN authorization:

```
API Gateway (authentication)
    ↓ validated token
Bounded Context API layer (authorization)
    ↓ authorized request
Application service (business rules)
```

Never rely solely on the gateway — defense in depth.

### Data Protection

- Encrypt at rest (database, storage)
- Encrypt in transit (TLS everywhere)
- PII handling: identify, classify, minimize, encrypt
- Audit log: who did what, when, from where

### OWASP Top 10 Checklist

- [ ] Input validation on ALL API endpoints
- [ ] Parameterized queries (no SQL injection)
- [ ] Output encoding (no XSS)
- [ ] CSRF protection on state-changing operations
- [ ] Rate limiting and throttling
- [ ] Security headers (CORS, CSP, HSTS)
- [ ] Dependency vulnerability scanning in CI

## DevOps & Deployment

### CI/CD Per Bounded Context

Each context has its own pipeline:

```
Code Push → Build → Unit Tests → Integration Tests → Contract Tests
    → Security Scan → Build Container → Deploy to Staging
    → E2E Tests → Deploy to Production (canary → full)
```

### Deployment Strategies

| Strategy | When | Risk |
|----------|------|------|
| **Blue-green** | Zero-downtime required | Needs 2x infrastructure |
| **Canary** | Gradual rollout, observability mature | Slower rollout |
| **Rolling** | Stateless services, simple | Brief mixed versions |
| **Feature flags** | Decouple deploy from release | Flag management overhead |

### Infrastructure as Code

- All infrastructure defined in code (Terraform, Pulumi, Bicep, CDK)
- Environment parity: dev ≈ staging ≈ production
- Secrets managed by cloud provider secret manager
- No manual changes to production infrastructure

### Disaster Recovery

| Tier | RPO | RTO | Strategy |
|------|-----|-----|----------|
| Core contexts | Minutes | Minutes | Multi-region active-active |
| Supporting contexts | Hours | Hours | Single-region with backup |
| Generic contexts | Hours | Day | Restore from backup |

RPO = Recovery Point Objective (max data loss)
RTO = Recovery Time Objective (max downtime)

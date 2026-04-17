## 3. Production Folder Structure (3-Layer)

Complete directory structure for production MCP servers:

```
[service-name]-mcp/
├── src/
│   ├── transport/              # Layer 1: Transport & Protocol
│   │   ├── stdio.ts           # STDIO transport for Claude Desktop
│   │   ├── http.ts            # HTTP transport with SSE
│   │   ├── session.ts         # Session management
│   │   └── health.ts          # Health check endpoints
│   │
│   ├── protocol/              # Layer 2: MCP Protocol
│   │   ├── mcp-server.ts      # Main MCP server implementation
│   │   ├── tool-registry.ts   # Tool registration and dispatch
│   │   ├── resource-registry.ts # Resource registration
│   │   ├── prompt-registry.ts # Prompt template registration
│   │   └── schemas/           # Zod schemas for tools/resources
│   │       ├── tool-schemas.ts
│   │       └── resource-schemas.ts
│   │
│   ├── business/              # Layer 3: Business Logic
│   │   ├── services/          # Core business services
│   │   │   ├── data-service.ts
│   │   │   ├── processing-service.ts
│   │   │   └── export-service.ts
│   │   ├── clients/           # External API clients
│   │   │   ├── database-client.ts
│   │   │   ├── external-api-client.ts
│   │   │   └── storage-client.ts
│   │   ├── cache/             # Caching layer
│   │   │   ├── redis-cache.ts
│   │   │   └── memory-cache.ts
│   │   └── transformers/      # Data transformation utilities
│   │       ├── data-transformer.ts
│   │       └── response-formatter.ts
│   │
│   ├── auth/                  # Authentication & Authorization
│   │   ├── auth-middleware.ts
│   │   ├── jwt-validator.ts
│   │   ├── api-key-validator.ts
│   │   └── permission-checker.ts
│   │
│   ├── security/              # Security utilities
│   │   ├── rate-limiter.ts
│   │   ├── input-sanitizer.ts
│   │   ├── secrets-manager.ts
│   │   └── encryption.ts
│   │
│   ├── audit/                 # Audit logging
│   │   ├── audit-logger.ts
│   │   ├── audit-repository.ts
│   │   └── audit-types.ts
│   │
│   ├── observability/         # Monitoring & Tracing
│   │   ├── metrics.ts         # Prometheus metrics
│   │   ├── tracing.ts         # OpenTelemetry tracing
│   │   ├── logging.ts         # Structured logging
│   │   └── correlation-id.ts  # Request correlation
│   │
│   ├── health/                # Health checks
│   │   ├── health-checker.ts
│   │   ├── types.ts
│   │   ├── endpoints.ts
│   │   └── checks/
│   │       ├── database.ts
│   │       ├── redis.ts
│   │       ├── external-api.ts
│   │       └── disk-space.ts
│   │
│   ├── lifecycle/             # Lifecycle management
│   │   ├── graceful-shutdown.ts
│   │   ├── startup-tasks.ts
│   │   └── cleanup-tasks.ts
│   │
│   ├── multi-tenant/          # Multi-tenant support
│   │   ├── context.ts         # AsyncLocalStorage context
│   │   ├── types.ts
│   │   ├── middleware.ts      # Tenant extraction
│   │   ├── loader.ts          # Tenant data loading
│   │   ├── quota-enforcer.ts  # Quota management
│   │   └── audit-logger.ts    # Tenant-aware audit logging
│   │
│   ├── config/                # Configuration
│   │   ├── env.ts             # Zod-validated environment
│   │   ├── database.ts        # Database configuration
│   │   └── app-config.ts      # Application settings
│   │
│   ├── errors/                # Error handling
│   │   ├── app-error.ts       # Base error class
│   │   ├── error-codes.ts     # Error code constants
│   │   └── error-handler.ts   # Global error handler
│   │
│   ├── types/                 # Shared types
│   │   ├── common.ts
│   │   ├── api.ts
│   │   └── models.ts
│   │
│   ├── utils/                 # Utilities
│   │   ├── circuit-breaker.ts
│   │   ├── retry.ts
│   │   ├── date-helpers.ts
│   │   └── validation.ts
│   │
│   ├── __tests__/             # Tests
│   │   ├── unit/
│   │   │   ├── services/
│   │   │   ├── transformers/
│   │   │   └── utils/
│   │   ├── integration/
│   │   │   ├── health.test.ts
│   │   │   ├── tools.test.ts
│   │   │   └── resources.test.ts
│   │   └── fixtures/
│   │       ├── mock-data.ts
│   │       └── test-helpers.ts
│   │
│   └── index.ts               # Application entry point
│
├── docker/                    # Docker files
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── .dockerignore
│
├── k8s/                       # Kubernetes manifests
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── ingress.yaml
│   └── hpa.yaml               # Horizontal Pod Autoscaler
│
├── .github/
│   └── workflows/
│       ├── ci.yaml            # CI pipeline
│       ├── cd.yaml            # CD pipeline
│       └── security-scan.yaml # Security scanning
│
├── scripts/                   # Utility scripts
│   ├── migrate.ts             # Database migrations
│   ├── seed.ts                # Seed data
│   └── health-check.sh        # Manual health check
│
├── docs/                      # Documentation
│   ├── README.md
│   ├── API.md
│   ├── DEPLOYMENT.md
│   └── ARCHITECTURE.md
│
├── package.json
├── tsconfig.json
├── vitest.config.ts
├── .env.example
├── .gitignore
└── README.md
```

## Layer Responsibilities

### Layer 1: Transport
- Handle MCP protocol transport (STDIO, HTTP, SSE)
- Session management and connection lifecycle
- Health check HTTP endpoints
- No business logic

### Layer 2: Protocol
- Implement MCP specification
- Tool/resource/prompt registration
- Request/response schema validation
- Route to business layer

### Layer 3: Business
- Core domain logic
- External API integrations
- Data transformation
- Caching strategies
- Independent of MCP protocol

## Cross-Cutting Concerns

- **auth/**: JWT, API keys, permissions - injected into protocol layer
- **security/**: Rate limiting, input sanitization, encryption
- **audit/**: Tenant-aware audit logging for compliance
- **observability/**: Metrics, tracing, structured logging
- **health/**: Component health checks for Kubernetes
- **lifecycle/**: Graceful shutdown, startup tasks
- **multi-tenant/**: AsyncLocalStorage context, quota enforcement
- **config/**: Environment validation, feature flags
- **errors/**: Centralized error handling and codes

## Benefits of 3-Layer Structure

1. **Separation of Concerns**: Transport, protocol, and business logic are isolated
2. **Testability**: Each layer can be tested independently
3. **Reusability**: Business logic can be used outside MCP context
4. **Maintainability**: Clear boundaries for changes
5. **Scalability**: Layers can be scaled independently if needed

## Usage Notes

1. **Docker**: Multi-stage build, non-root user, health checks
2. **Kubernetes**: Liveness/readiness probes, resource limits, graceful shutdown
3. **Folder Structure**: 3-layer architecture with cross-cutting concerns
4. **CI/CD**: Automated testing, security scanning, deployment pipelines

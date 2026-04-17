---
name: java-spring-api
description: This skill provides patterns and templates for Java 21 Spring Boot 3.5.x WebFlux REST API development. It should be activated when creating controllers, services, repositories, DTOs, or reactive tests.
allowed-tools: Bash, Read, Write, Edit
metadata:
  triggers: Java, Spring Boot, Spring WebFlux, REST API Java, reactive Java, WebFlux, R2DBC, Mono, Flux
  related-skills: java-coding-standard, openapi-spec-generation, database-schema-designer
  domain: backend
  role: specialist
  scope: implementation
  output-format: code
last-reviewed: "2026-03-14"
---

## Iron Law

**NO REACTIVE CODE WITHOUT READING `reference/spring-boot-conventions.md` FIRST — blocking calls inside reactive chains cause thread starvation**

# Java 21 + Spring Boot 3.5.x WebFlux REST API Skill

## Conventions & Rules

> For code conventions, package layout, and reactive rules, read `reference/spring-boot-conventions.md`

## Quick Scaffold — New Spring Boot Project

```bash
# Using Spring Initializr via curl
curl https://start.spring.io/starter.zip \
  -d type=maven-project \
  -d language=java \
  -d javaVersion=21 \
  -d bootVersion=3.5.0 \
  -d dependencies=webflux,r2dbc,postgresql,flyway,validation,actuator,lombok \
  -d groupId=com.company \
  -d artifactId=my-service \
  -d name=my-service \
  -o my-service.zip && unzip my-service.zip -d my-service
```

## Process

1. **Scaffold** using Spring Initializr or the command above
2. **Configure** pom.xml and application.yml — read `reference/spring-boot-config.md`
3. **Create files** using templates — read `reference/spring-boot-templates.md` for DTO, Entity, Repository, Service, Controller, and Test templates
4. **Follow conventions** below for package layout and reactive rules
5. **Write tests** with `@SpringBootTest` + `WebTestClient`
6. **Format and check**: `mvn spotless:apply` or IDE formatter

## Key Patterns

| Pattern | Implementation |
|---------|---------------|
| **DTOs** | Java records with `jakarta.validation` annotations |
| **Entities** | Classes with `@Table`, `@Id` R2DBC annotations |
| **Repositories** | Extend `ReactiveCrudRepository<T, UUID>` |
| **Services** | `@Service` + `@RequiredArgsConstructor`, return `Mono`/`Flux` |
| **Controllers** | `@RestController` + `@RequestMapping("/api/v1/...")` |
| **Error handling** | `@ControllerAdvice` returning `ProblemDetail` (RFC 9457) |
| **Config** | `application.yml` with `${ENV_VAR:default}` placeholders |
| **Migrations** | Flyway in `src/main/resources/db/migration/` (disabled by default; enable with `FLYWAY_ENABLED=true`) |

## Reference Files

| File | Content | Load When |
|------|---------|-----------|
| `reference/spring-boot-config.md` | pom.xml template, application.yml configuration | Project setup, configuring dependencies |
| `reference/spring-boot-templates.md` | DTO, Entity, Repository, Service, Controller, Test, Error Handler templates | Creating DTOs, services, controllers, entities |
| `reference/spring-boot-enterprise-errors-security.md` | Exception hierarchy, Security (OAuth2/JWT), CORS | Implementing error handling, adding security, configuring CORS |
| `reference/spring-boot-enterprise-resilience-health.md` | Resilience4j, WebClient pool, Health indicators, Swagger | Adding resilience, health checks, API documentation |
| `reference/spring-boot-rest-service-guide.md` | OpenAPI+DDL driven workflow, MapStruct mapping, External service clients, WireMock testing | Designing REST APIs, mapping DTOs, calling external services |
| `reference/spring-boot-testing-unit.md` | BlockHound, Resilience4j testing, test data builders | Writing unit tests, testing reactive streams |
| `reference/spring-boot-testing-integration.md` | Testcontainers, contract testing, WireMock, coverage | Writing integration tests, controller tests |
| `reference/spring-boot-reactive-debugging.md` | Reactor Hooks (onOperatorError, onNextDropped, onErrorDropped), checkpoint patterns, debug mode control | Debugging reactive pipelines, tracing Flux/Mono errors |
| `reference/spring-boot-security-hardening.md` | OWASP dependency scanning, static analysis patterns, HSTS, JWT role extraction, secure logging | Security hardening, JWT auth, dependency scanning |
| `reference/spring-boot-reactive-patterns.md` | Resilience4j operators, Redis reactive, SSE, Spring Cloud Stream, custom operators, threading anti-patterns | Writing reactive endpoints, Flux/Mono, Redis caching, SSE |
| `reference/spring-boot-design-patterns.md` | Builder, Factory (Spring DI), Strategy, Observer (Spring Events), Decorator, Adapter — all with Spring Boot 3.5.x examples | Implementing any of these 6 patterns in Spring Boot code |
| `reference/spring-reactive-review-checklist.md` | Spring reactive review checklist (used by `spring-reactive-reviewer` agent) | Code review, pre-PR checklist |
| `reference/java21-advanced-features.md` | GraalVM Native Image, structured concurrency (`StructuredTaskScope`), virtual threads migration guide, JVM tuning (ZGC/G1 for Cloud Run), JMH benchmarking, Spring Modulith, sequenced collections, string templates, record patterns | GraalVM native builds, parallel calls with structured concurrency, JVM performance tuning, modular monolith design |
| `reference/spring-boot-verification-gates.md` | SpotBugs, PMD, Checkstyle Maven commands, 6-phase verification loop, CI gate output template | Pre-PR verification, static analysis, CI/CD gate |

## Documentation Sources

Before generating code, consult these sources for current syntax and APIs:

| Source | URL / Tool | Purpose |
|--------|-----------|---------|
| Spring Boot | `Context7` MCP | Latest Spring Boot APIs, annotations, configuration |
| Spring Initializr | `https://start.spring.io` | Project scaffolding with correct dependencies |

## Common Commands

```bash
mvn spring-boot:run                  # Run backend
mvn test                             # Run tests
mvn package                          # Build JAR
mvn spotless:apply                   # Format code
mvn clean test -Dspring.profiles.active=test  # Run tests with test profile
mvn dependency:tree                  # Show dependency tree
```

## Error Handling

**Validation errors**: Use `jakarta.validation` annotations on DTO records. Handle via `@ControllerAdvice` returning `ProblemDetail` with `HttpStatus.BAD_REQUEST` (400).

**Not-found errors**: Use `switchIfEmpty(Mono.error(new ResourceNotFoundException(...)))` in services.

**Duplicate errors**: Catch `DataIntegrityViolationException` in services and convert to `409 Conflict`.

## Hard Prohibitions

- No `block()` calls in reactive chains — all operations must stay non-blocking
- No JPA in reactive stacks — use R2DBC exclusively
- Password reset rate limit: 3 attempts per email per hour maximum

## Post-Code Review

After writing Java code, dispatch these reviewer agents:
- `spring-reactive-reviewer` — reactive correctness, blocking call detection, R2DBC patterns
- `security-reviewer` — auth, input validation, secrets management

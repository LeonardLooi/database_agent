---
description: Scaffold a new Spring Boot 3.5.x WebFlux REST API project with standard structure, build config, and sample endpoint
argument-hint: "[project name]"
allowed-tools: Bash, Read, Write, Edit
disable-model-invocation: true
---

# Scaffold Spring Boot WebFlux API

**Project name:** $ARGUMENTS (default to "my-api" if not provided)

Delegate to the `java-spring-api` skill for all patterns, templates, and reference files. Use the `java-coding-standard` skill for naming, immutability, and style rules.

## Steps

1. **Create `.gitignore` first** — before any other file. Include: `target/`, `.env`, `*.pem`, `*.key`, `.idea/`, `*.iml`, `.DS_Store`, `*.log`
2. Read the `java-spring-api` skill and its reference files for exact code templates
3. Create Maven project via Spring Initializr or manual `pom.xml` per skill config reference
3. Set up package `com.company.<projectname>` with directory structure: `controller/`, `service/`, `repository/`, `model/entity/`, `model/dto/`, `config/`, `exception/`
4. Add `application.yml` with R2DBC + Flyway config (PostgreSQL, Flyway disabled by default via `enabled: ${FLYWAY_ENABLED:false}`)
5. Create `HealthController` at `GET /api/v1/health`, a sample entity, DTO (record), repository, service, and controller
6. Add `GlobalExceptionHandler` with `@ControllerAdvice` returning `ProblemDetail` (RFC 9457)
7. Add `V1__initial_schema.sql` Flyway migration, `Dockerfile`, and `docker-compose.yml` with PostgreSQL
8. Add a basic integration test using `WebTestClient`
9. Add OWASP dependency-check plugin to `pom.xml` and run `mvn dependency-check:check` — fix or document any critical/high CVEs
10. Verify — `mvn compile`

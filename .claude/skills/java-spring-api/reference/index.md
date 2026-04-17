# Java Spring API References

## Quick Navigation

| Reference | When to Load | Key Content |
|-----------|-------------|-------------|
| [spring-boot-conventions.md](spring-boot-conventions.md) | **Before any reactive code** — Iron Law | Package layout, reactive rules, coding conventions, R2DBC patterns |
| [spring-boot-caching.md](spring-boot-caching.md) | Adding @Cacheable, @CacheEvict, Caffeine configuration, or cache eviction strategies | Caffeine setup, @Cacheable/@CacheEvict/@CachePut, reactive caching caveat, eviction strategies, anti-patterns |
| [spring-boot-config.md](spring-boot-config.md) | Project setup or configuring dependencies | pom.xml template, application.yml configuration |
| [spring-boot-templates.md](spring-boot-templates.md) | Creating DTOs, entities, services, or controllers | DTO records, Entity, Repository, Service, Controller, Error Handler, Test templates |
| [spring-boot-enterprise-errors-security.md](spring-boot-enterprise-errors-security.md) | Implementing error handling, adding auth, configuring CORS | Exception hierarchy, OAuth2/JWT security, CORS configuration |
| [spring-boot-enterprise-resilience-health.md](spring-boot-enterprise-resilience-health.md) | Adding resilience, health checks, or API documentation | Resilience4j, WebClient pool, Health indicators, Swagger |
| [spring-boot-rest-service-guide.md](spring-boot-rest-service-guide.md) | Designing REST APIs, mapping DTOs, calling external services | OpenAPI+DDL driven workflow, MapStruct mapping, WireMock testing |
| [spring-boot-reactive-patterns.md](spring-boot-reactive-patterns.md) | Writing reactive endpoints, Flux/Mono, Redis caching | Resilience4j operators, Redis reactive, SSE, Spring Cloud Stream |
| [spring-boot-reactive-debugging.md](spring-boot-reactive-debugging.md) | Debugging reactive pipelines or tracing Flux/Mono errors | Reactor Hooks, checkpoint patterns, debug mode control |
| [spring-boot-testing-unit.md](spring-boot-testing-unit.md) | Writing unit tests or testing reactive streams | BlockHound, Resilience4j testing, test data builders |
| [spring-boot-testing-integration.md](spring-boot-testing-integration.md) | Writing integration or controller tests | Testcontainers, contract testing, WireMock, coverage |
| [spring-boot-security-hardening.md](spring-boot-security-hardening.md) | Security hardening, JWT auth, dependency scanning | OWASP scanning, HSTS, JWT role extraction, secure logging |
| [spring-boot-rate-limiting.md](spring-boot-rate-limiting.md) | Adding rate limiting to endpoints | Rate limiting patterns and configuration |
| [java21-advanced-features.md](java21-advanced-features.md) | GraalVM builds, structured concurrency, JVM tuning, modular monolith | GraalVM Native Image, StructuredTaskScope, ZGC/G1 tuning, Spring Modulith |
| [spring-reactive-review-checklist.md](spring-reactive-review-checklist.md) | Code review or pre-PR check (used by `spring-reactive-reviewer`) | Reactive correctness checklist, blocking call detection |
| [gdpr-account-deletion.md](gdpr-account-deletion.md) | Implementing account deletion or GDPR compliance | GDPR account deletion patterns |

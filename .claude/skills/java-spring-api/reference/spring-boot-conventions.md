# Spring Boot Conventions & Rules

## Code Conventions

- Use **Java 21** features: records, sealed classes, pattern matching, virtual threads
- Spring Boot 3.5.x Reactive stack: `WebFlux` + `Mono`/`Flux` — no blocking calls in reactive chains
- Follow package structure: `controller → service → repository → model/dto`
- Use `@RestController` with `@RequestMapping("/api/v1/...")`
- DTOs as Java records, entities as classes with JPA/R2DBC annotations
- Tests: JUnit 5 + WebTestClient for reactive endpoints

## Package Layout

```
com.company.<service>/
├── controller/     # REST controllers
├── service/        # Business logic
├── repository/     # R2DBC repositories
├── model/
│   ├── entity/     # Database entities
│   └── dto/        # Request/response DTOs (records)
├── config/         # Spring config, security, CORS
└── exception/      # Global error handling
```

## Reactive Rules

- NEVER call `.block()` inside a reactive chain
- Use `Mono.zip()` for parallel calls
- Use `switchIfEmpty()` with `Mono.error()` for not-found cases
- Use `@ResponseStatus` for non-200 responses (e.g., `201 Created`); default 200 OK is implicit for GET endpoints
- Use `@Valid` on `@RequestBody` params, `@Validated` on controller class for path/query param validation, `jakarta.validation` on DTOs
- `@Transactional` only works on methods returning `Mono`/`Flux` — placing it on a void method or one calling `.subscribe()` silently does nothing. Requires `R2dbcTransactionManager` (auto-configured by `spring-boot-starter-data-r2dbc`). For multi-statement writes, annotate the **service** method, not the repository:
  ```java
  @Transactional
  public Mono<Order> createOrder(CreateOrderRequest req) {
      return orderRepository.save(toEntity(req))
          .flatMap(order -> lineItemRepository.saveAll(toLineItems(order, req))
              .then(Mono.just(order)));
  }
  ```

# Spring Boot Enterprise Patterns — Error Handling & Security

Production-ready error handling and security patterns for Java 21 + Spring Boot 3.5.x WebFlux.

## Exception Hierarchy

### Base Exception

```java
package com.company.service.exception;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import org.springframework.http.HttpStatus;

public abstract class ApplicationException extends RuntimeException {

    private final HttpStatus httpStatus;
    private final String errorCode;
    private final List<String> errors;
    private final Map<String, Object> details;

    protected ApplicationException(HttpStatus httpStatus, String errorCode, String message) {
        this(httpStatus, errorCode, message, null, List.of(), Map.of());
    }

    protected ApplicationException(HttpStatus httpStatus, String errorCode, String message, Throwable cause) {
        this(httpStatus, errorCode, message, cause, List.of(), Map.of());
    }

    protected ApplicationException(HttpStatus httpStatus, String errorCode, String message, List<String> errors) {
        this(httpStatus, errorCode, message, null, errors, Map.of());
    }

    protected ApplicationException(HttpStatus httpStatus, String errorCode, String message,
                                   Throwable cause, List<String> errors, Map<String, Object> details) {
        super(message, cause);
        this.httpStatus = httpStatus;
        this.errorCode = errorCode;
        this.errors = errors != null ? Collections.unmodifiableList(errors) : List.of();
        this.details = details != null ? Collections.unmodifiableMap(details) : Map.of();
    }

    public HttpStatus getHttpStatus() { return httpStatus; }
    public String getErrorCode() { return errorCode; }
    public List<String> getErrors() { return errors; }
    public Map<String, Object> getDetails() { return details; }
}
```

### Concrete Exceptions

```java
// 400 Bad Request — validation failures
public class InvalidInputException extends ApplicationException {
    public InvalidInputException(String message) {
        super(HttpStatus.BAD_REQUEST, "VALIDATION_ERROR", message);
    }
    public InvalidInputException(String message, List<String> errors) {
        super(HttpStatus.BAD_REQUEST, "VALIDATION_ERROR", message, errors);
    }
}

// 404 Not Found
public class ResourceNotFoundException extends ApplicationException {
    public ResourceNotFoundException(String message) {
        super(HttpStatus.NOT_FOUND, "RESOURCE_NOT_FOUND", message);
    }
}

// 409 Conflict — business rule violations
public class BusinessRuleException extends ApplicationException {
    public BusinessRuleException(String message) {
        super(HttpStatus.CONFLICT, "BUSINESS_RULE_VIOLATION", message);
    }
    public BusinessRuleException(HttpStatus status, String errorCode, String message) {
        super(status, errorCode, message);
    }
}

// 500/502/503 — external service failures
public class ServiceIntegrationException extends ApplicationException {
    public ServiceIntegrationException(String message, Throwable cause) {
        super(HttpStatus.INTERNAL_SERVER_ERROR, "INTEGRATION_ERROR", message, cause);
    }
    public ServiceIntegrationException(HttpStatus status, String errorCode, String message, Throwable cause) {
        super(status, errorCode, message, cause);
    }
}
```

### Error Response DTOs

```java
// Client errors (4xx)
public record ClientErrorResponse(
    @Schema(description = "General error description", example = "Validation failed")
    String message,

    @Schema(description = "Specific error details", example = "[\"email is required\"]", nullable = true)
    List<String> errors,

    @Schema(description = "Application error code", example = "VALIDATION_ERROR")
    String errorCode,

    @Schema(description = "ISO-8601 timestamp", example = "2025-05-19T13:30:00Z")
    String timestamp
) {}

// Server errors (5xx)
public record ServerErrorResponse(
    @Schema(description = "Error type", example = "InternalServerError")
    String error,

    @Schema(description = "Error description", example = "Unexpected error occurred")
    String message,

    @Schema(description = "ISO-8601 timestamp", example = "2025-05-19T13:30:00Z")
    String timestamp,

    @Schema(description = "Trace ID for log correlation", example = "abc123xy")
    String traceId
) {}
```

### Global Error Handler (WebFlux)

```java
@Component
@Order(-2)
public class GlobalErrorWebExceptionHandler extends AbstractErrorWebExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalErrorWebExceptionHandler.class);

    public GlobalErrorWebExceptionHandler(ErrorAttributes errorAttributes,
                                          ApplicationContext applicationContext,
                                          ServerCodecConfigurer serverCodecConfigurer) {
        super(errorAttributes, new WebProperties().getResources(), applicationContext);
        super.setMessageWriters(serverCodecConfigurer.getWriters());
        super.setMessageReaders(serverCodecConfigurer.getReaders());
    }

    @Override
    protected RouterFunction<ServerResponse> getRoutingFunction(ErrorAttributes errorAttributes) {
        return RouterFunctions.route(RequestPredicates.all(), this::renderErrorResponse);
    }

    private Mono<ServerResponse> renderErrorResponse(ServerRequest request) {
        Throwable error = getError(request);
        String traceId = UUID.randomUUID().toString().substring(0, 8);
        String timestamp = Instant.now().toString();

        log.error("[{}] {} {} — {}", traceId, request.methodName(), request.path(), error.getMessage(), error);

        return switch (error) {
            case ApplicationException appEx when appEx.getHttpStatus().is4xxClientError() ->
                ServerResponse.status(appEx.getHttpStatus())
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(new ClientErrorResponse(
                        appEx.getMessage(), appEx.getErrors(), appEx.getErrorCode(), timestamp));

            case ApplicationException appEx ->
                ServerResponse.status(appEx.getHttpStatus())
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(new ServerErrorResponse(
                        appEx.getErrorCode(), appEx.getMessage(), timestamp, traceId));

            case WebExchangeBindException validationEx -> {
                List<String> errors = validationEx.getBindingResult().getAllErrors().stream()
                    .map(DefaultMessageSourceResolvable::getDefaultMessage).toList();
                yield ServerResponse.status(HttpStatus.BAD_REQUEST)
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(new ClientErrorResponse(
                        "Validation failed", errors, "VALIDATION_FAILED", timestamp));
            }

            default ->
                ServerResponse.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(new ServerErrorResponse(
                        "InternalServerError", "Unexpected error. Trace: " + traceId, timestamp, traceId));
        };
    }
}
```

## Security Configuration

### OAuth2 JWT Resource Server

```java
@Configuration
@EnableWebFluxSecurity
@EnableReactiveMethodSecurity
public class SecurityConfig {

    @Bean
    public SecurityWebFilterChain securityWebFilterChain(ServerHttpSecurity http) {
        return http
            .csrf(ServerHttpSecurity.CsrfSpec::disable)
            .cors(cors -> cors.configurationSource(corsSource()))
            .httpBasic(ServerHttpSecurity.HttpBasicSpec::disable)
            .formLogin(ServerHttpSecurity.FormLoginSpec::disable)
            .oauth2ResourceServer(oauth2 -> oauth2.jwt(Customizer.withDefaults()))
            .headers(headers -> {
                headers.frameOptions(opts -> opts.mode(XFrameOptionsServerHttpHeadersWriter.Mode.DENY));
                headers.contentSecurityPolicy(csp -> csp.policyDirectives("default-src 'self'; frame-ancestors 'none';"));
            })
            .authorizeExchange(exchanges -> exchanges
                .pathMatchers("/management/**", "/swagger-ui.html", "/swagger-ui/**", "/v3/api-docs/**").permitAll()
                .pathMatchers("/api/v1/**").authenticated()
                .anyExchange().authenticated()
            )
            .build();
    }
}

// Method-level authorization — requires @EnableReactiveMethodSecurity above
@Service
@RequiredArgsConstructor
public class OrderService {
    @PreAuthorize("hasRole('ADMIN')")
    public Mono<Void> deleteOrder(UUID id) { /* ... */ }

    @PreAuthorize("hasRole('USER') or hasRole('ADMIN')")
    public Mono<Order> getOrder(UUID id) { /* ... */ }
}
```

### Custom SpEL Method Security — Ownership Checks

For fine-grained ownership authorization beyond roles, create a Spring bean used as a SpEL evaluator:

```java
@Component("authz")
@RequiredArgsConstructor
public class AuthorizationService {

    private final ResourceRepository resourceRepository;

    /**
     * Returns true if the authenticated user owns the resource.
     * Usage: @PreAuthorize("@authz.isOwner(#resourceId, authentication)")
     */
    public boolean isOwner(UUID resourceId, Authentication authentication) {
        if (authentication == null || !authentication.isAuthenticated()) return false;
        String userId = authentication.getName();
        return resourceRepository.findById(resourceId)
            .map(r -> r.getOwnerId().toString().equals(userId))
            .defaultIfEmpty(false)
            .block(); // acceptable in security filter — not in reactive chain
    }
}
```

Apply on controller methods:

```java
@GetMapping("/{id}")
@PreAuthorize("hasRole('ADMIN') or @authz.isOwner(#id, authentication)")
public Mono<ResponseEntity<ResourceResponse>> getResource(@PathVariable UUID id) {
    return resourceService.findById(id).map(ResponseEntity::ok);
}

@DeleteMapping("/{id}")
@PreAuthorize("@authz.isOwner(#id, authentication)")
public Mono<ResponseEntity<Void>> deleteResource(@PathVariable UUID id) {
    return resourceService.delete(id).thenReturn(ResponseEntity.noContent().<Void>build());
}
```

Enable method security in your security config:

```java
@Configuration
@EnableMethodSecurity  // replaces @EnableGlobalMethodSecurity(prePostEnabled=true)
public class SecurityConfig { ... }
```

**Rules:**
- Bean name (`"authz"`) must match the SpEL expression prefix (`@authz`)
- The `.block()` call is acceptable inside a security service bean — not inside a `Mono`/`Flux` chain
- Avoid complex DB queries in the security bean — keep checks lightweight
- Always combine with role checks (`hasRole('ADMIN') or @authz.isOwner(...)`) to allow admins to bypass

### CORS Configuration

```java
@Configuration
public class CorsConfig {

    private CorsConfigurationSource corsSource() {
        CorsConfiguration config = new CorsConfiguration();
        config.setAllowedOrigins(List.of("${CORS_ORIGINS:http://localhost:4200}"));
        config.setAllowedMethods(List.of("GET", "POST", "PUT", "DELETE", "OPTIONS"));
        config.setAllowedHeaders(List.of("Authorization", "Content-Type", "Accept"));
        config.setAllowCredentials(true);
        config.setMaxAge(3600L);
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", config);
        return source;
    }
}
```

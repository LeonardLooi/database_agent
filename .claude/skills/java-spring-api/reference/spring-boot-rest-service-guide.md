# REST Service Implementation Guide

Step-by-step guide for implementing a REST service from OpenAPI spec + SQL DDL in Spring Boot 3.5.x WebFlux.

## Workflow

1. **Gather inputs**: OpenAPI 3.x JSON/YAML + SQL DDL file
2. **Analyze**: Infer entities, relationships, endpoints, and DTOs from the specs
3. **Generate layers**: Controller → Service → Repository → Entity → DTO → Mapper
4. **Add integrations**: External service clients with resilience patterns
5. **Write tests**: Unit, integration, and contract tests
6. **Configure**: application.yml, security, and documentation

## OpenAPI-Driven Development

When given an OpenAPI spec and DDL:

1. Parse the OpenAPI spec to extract:
   - Endpoint paths and HTTP methods
   - Request/response schemas → DTO records
   - Validation constraints → `jakarta.validation` annotations
   - Error responses → exception mappings

2. Parse the DDL to extract:
   - Table definitions → R2DBC entity classes
   - Column types and constraints → Java types and annotations
   - Foreign keys → repository query methods
   - Indexes → custom `@Query` methods

3. Cross-reference both to ensure alignment between API contract and data model.

## MapStruct DTO-Entity Mapping

### Maven Setup

```xml
<properties>
    <mapstruct.version>1.6.3</mapstruct.version>
</properties>

<dependency>
    <groupId>org.mapstruct</groupId>
    <artifactId>mapstruct</artifactId>
    <version>${mapstruct.version}</version>
</dependency>

<!-- In maven-compiler-plugin annotationProcessorPaths -->
<path>
    <groupId>org.mapstruct</groupId>
    <artifactId>mapstruct-processor</artifactId>
    <version>${mapstruct.version}</version>
</path>
```

### Mapper Interface

```java
@Mapper(componentModel = "spring", unmappedTargetPolicy = ReportingPolicy.IGNORE)
public interface OrderMapper {

    OrderResponse toResponse(OrderEntity entity);

    @Mapping(target = "id", ignore = true)
    @Mapping(target = "createdAt", ignore = true)
    @Mapping(target = "updatedAt", ignore = true)
    OrderEntity toEntity(CreateOrderRequest request);

    default List<OrderResponse> toResponseList(List<OrderEntity> entities) {
        return entities.stream().map(this::toResponse).toList();
    }
}
```

### Usage in Service

```java
@Service
@RequiredArgsConstructor
public class OrderService {
    private final OrderRepository orderRepository;
    private final OrderMapper orderMapper;

    public Mono<OrderResponse> create(CreateOrderRequest request) {
        OrderEntity entity = orderMapper.toEntity(request);
        entity.setCreatedAt(Instant.now());
        entity.setUpdatedAt(Instant.now());
        return orderRepository.save(entity)
                .map(orderMapper::toResponse);
    }

    public Mono<OrderResponse> findById(UUID id) {
        return orderRepository.findById(id)
                .map(orderMapper::toResponse)
                .switchIfEmpty(Mono.error(new ResourceNotFoundException("Order not found: " + id)));
    }
}
```

## External Service Integration

### Client Pattern

```java
@Service
public class PaymentServiceClient {

    private final WebClient.Builder webClientBuilder;
    private final PaymentServiceProperties config;

    private final CircuitBreaker circuitBreaker;
    private final Retry retry;
    private final TimeLimiter timeLimiter;

    public PaymentServiceClient(WebClient.Builder webClientBuilder,
                                PaymentServiceProperties config,
                                CircuitBreakerRegistry cbRegistry,
                                RetryRegistry retryRegistry,
                                TimeLimiterRegistry tlRegistry) {
        this.webClientBuilder = webClientBuilder;
        this.config = config;
        this.circuitBreaker = cbRegistry.circuitBreaker("paymentService");
        this.retry = retryRegistry.retry("paymentService");
        this.timeLimiter = tlRegistry.timeLimiter("paymentService");
    }

    public Mono<PaymentResponse> processPayment(PaymentRequest request) {
        return webClientBuilder.build()
            .post()
            .uri(config.getBaseUrl() + "/api/v1/payments")
            .header(HttpHeaders.AUTHORIZATION, "Bearer " + config.getApiKey())
            .contentType(MediaType.APPLICATION_JSON)
            .bodyValue(request)
            .retrieve()
            .onStatus(HttpStatusCode::is4xxClientError, response ->
                response.bodyToMono(String.class)
                    .flatMap(body -> Mono.error(new InvalidInputException("Payment rejected: " + body))))
            .onStatus(HttpStatusCode::is5xxServerError, response ->
                Mono.error(new ServiceIntegrationException("Payment service unavailable", null)))
            .bodyToMono(PaymentResponse.class)
            .transformDeferred(CircuitBreakerOperator.of(circuitBreaker))
            .transformDeferred(RetryOperator.of(retry))
            .transformDeferred(TimeLimiterOperator.of(timeLimiter))
            .onErrorResume(CallNotPermittedException.class, ex ->
                Mono.error(new ServiceIntegrationException(
                    HttpStatus.SERVICE_UNAVAILABLE, "PAYMENT_UNAVAILABLE",
                    "Payment service circuit breaker is open", ex)));
    }
}
```

### Type-Safe Configuration

```java
@ConfigurationProperties(prefix = "integration.payment-service")
public record PaymentServiceProperties(
    @NotBlank String baseUrl,
    @NotBlank String apiKey,
    @Min(100) int timeoutMs
) {}
```

```yaml
integration:
  payment-service:
    base-url: ${PAYMENT_SERVICE_URL:http://localhost:8081}
    api-key: ${PAYMENT_SERVICE_API_KEY}
    timeout-ms: 5000
```

### Resilience4j Instance Config

```yaml
resilience4j:
  circuitbreaker:
    instances:
      paymentService:
        base-config: default
        failure-rate-threshold: 60
  retry:
    instances:
      paymentService:
        base-config: default
        max-attempts: 2
  timelimiter:
    instances:
      paymentService:
        base-config: default
        timeout-duration: 5s
```

## Testing Patterns

### Controller Test (WebFluxTest)

```java
@WebFluxTest(OrderController.class)
@Import(SecurityConfig.class)
class OrderControllerTest {

    @Autowired
    private WebTestClient webTestClient;

    @MockBean
    private OrderService orderService;

    @Test
    @WithMockUser
    void createOrder_shouldReturn201() {
        var request = new CreateOrderRequest("item-1", 2, BigDecimal.valueOf(29.99));
        var response = new OrderResponse(UUID.randomUUID(), "item-1", 2, BigDecimal.valueOf(29.99), Instant.now());

        when(orderService.create(any())).thenReturn(Mono.just(response));

        webTestClient.post().uri("/api/v1/orders")
            .contentType(MediaType.APPLICATION_JSON)
            .bodyValue(request)
            .exchange()
            .expectStatus().isCreated()
            .expectBody()
            .jsonPath("$.itemId").isEqualTo("item-1")
            .jsonPath("$.quantity").isEqualTo(2);
    }

    @Test
    @WithMockUser
    void getOrder_notFound_shouldReturn404() {
        UUID id = UUID.randomUUID();
        when(orderService.findById(id)).thenReturn(Mono.error(new ResourceNotFoundException("Order not found")));

        webTestClient.get().uri("/api/v1/orders/{id}", id)
            .exchange()
            .expectStatus().isNotFound();
    }
}
```

### Service Unit Test (StepVerifier)

```java
@ExtendWith(MockitoExtension.class)
class OrderServiceTest {

    @Mock private OrderRepository orderRepository;
    @Mock private OrderMapper orderMapper;
    @InjectMocks private OrderService orderService;

    @Test
    void findById_existingOrder_shouldReturnResponse() {
        UUID id = UUID.randomUUID();
        var entity = new OrderEntity();
        entity.setId(id);
        var response = new OrderResponse(id, "item-1", 2, BigDecimal.valueOf(29.99), Instant.now());

        when(orderRepository.findById(id)).thenReturn(Mono.just(entity));
        when(orderMapper.toResponse(entity)).thenReturn(response);

        StepVerifier.create(orderService.findById(id))
            .expectNext(response)
            .verifyComplete();
    }

    @Test
    void findById_missingOrder_shouldReturnNotFound() {
        UUID id = UUID.randomUUID();
        when(orderRepository.findById(id)).thenReturn(Mono.empty());

        StepVerifier.create(orderService.findById(id))
            .expectError(ResourceNotFoundException.class)
            .verify();
    }
}
```

### WireMock Integration Test (External Services)

```java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureWebTestClient
class PaymentIntegrationTest {

    @Autowired private WebTestClient webTestClient;

    private static WireMockServer wireMock;

    @BeforeAll
    static void startWireMock() {
        wireMock = new WireMockServer(WireMockConfiguration.wireMockConfig().dynamicPort());
        wireMock.start();
    }

    @AfterAll
    static void stopWireMock() {
        wireMock.stop();
    }

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("integration.payment-service.base-url", wireMock::baseUrl);
    }

    @Test
    @WithMockUser
    void processPayment_success() {
        wireMock.stubFor(post(urlEqualTo("/api/v1/payments"))
            .willReturn(aResponse()
                .withStatus(200)
                .withHeader("Content-Type", "application/json")
                .withBody("""
                    {"transactionId": "txn-123", "status": "APPROVED"}
                    """)));

        webTestClient.post().uri("/api/v1/orders")
            .contentType(MediaType.APPLICATION_JSON)
            .bodyValue(new CreateOrderRequest("item-1", 1, BigDecimal.TEN))
            .exchange()
            .expectStatus().isCreated();
    }

    @Test
    @WithMockUser
    void processPayment_serviceDown_shouldReturn503() {
        wireMock.stubFor(post(urlEqualTo("/api/v1/payments"))
            .willReturn(aResponse().withStatus(500)));

        webTestClient.post().uri("/api/v1/orders")
            .contentType(MediaType.APPLICATION_JSON)
            .bodyValue(new CreateOrderRequest("item-1", 1, BigDecimal.TEN))
            .exchange()
            .expectStatus().is5xxServerError();
    }
}
```

### Maven Test Dependencies

```xml
<dependency>
    <groupId>org.wiremock</groupId>
    <artifactId>wiremock-standalone</artifactId>
    <version>3.10.0</version>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.springframework.security</groupId>
    <artifactId>spring-security-test</artifactId>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>io.projectreactor</groupId>
    <artifactId>reactor-test</artifactId>
    <scope>test</scope>
</dependency>
```

## Implementation Checklist

- [ ] All endpoints match OpenAPI spec (paths, methods, status codes)
- [ ] Entities match DDL (column names, types, constraints)
- [ ] DTOs use Java records with `jakarta.validation` annotations
- [ ] MapStruct mappers for all DTO-entity conversions
- [ ] Service layer returns `Mono`/`Flux` — no `.block()` calls
- [ ] External clients use `WebClient` + programmatic Resilience4j (`.transformDeferred()`)
- [ ] Fallback methods defined for all circuit breakers
- [ ] `@WebFluxTest` for controllers, `StepVerifier` for services
- [ ] WireMock tests for external service integrations
- [ ] Configuration externalized via `@ConfigurationProperties`

# Spring Boot WebFlux Integration Testing Guide

Integration testing patterns for Java 21 + Spring Boot 3.5.x reactive services — covering Testcontainers, contract testing with WireMock, external API resilience testing, and coverage standards.

## Testcontainers — Integration Testing

Use real databases instead of H2 to catch database-specific issues.

### PostgreSQL Setup

```java
@SpringBootTest(webEnvironment = WebEnvironment.RANDOM_PORT)
@Testcontainers
@ActiveProfiles("integration-test")
class OrderRepositoryIntegrationTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16")
        .withDatabaseName("testdb")
        .withUsername("test")
        .withPassword("test");

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.r2dbc.url", () ->
            "r2dbc:postgresql://" + postgres.getHost() + ":"
            + postgres.getMappedPort(5432) + "/" + postgres.getDatabaseName());
        registry.add("spring.r2dbc.username", postgres::getUsername);
        registry.add("spring.r2dbc.password", postgres::getPassword);
        registry.add("spring.flyway.url", postgres::getJdbcUrl);
        registry.add("spring.flyway.user", postgres::getUsername);
        registry.add("spring.flyway.password", postgres::getPassword);
    }

    @Autowired
    private OrderRepository orderRepository;

    @Test
    @DisplayName("Should save and retrieve order from real database")
    void shouldSaveAndRetrieve() {
        var order = OrderTestData.anOrder().build();

        StepVerifier.create(
            orderRepository.save(order)
                .then(orderRepository.findById(order.getId())))
            .expectNextMatches(retrieved ->
                retrieved.getCustomerId().equals(order.getCustomerId()))
            .verifyComplete();
    }
}
```

### Maven Dependencies

```xml
<dependency>
    <groupId>org.testcontainers</groupId>
    <artifactId>junit-jupiter</artifactId>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.testcontainers</groupId>
    <artifactId>postgresql</artifactId>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.testcontainers</groupId>
    <artifactId>r2dbc</artifactId>
    <scope>test</scope>
</dependency>
```

## Contract Testing — External API Clients

Verify your HTTP client code handles expected response formats without calling real services.

```java
@WebFluxTest
@Import(PaymentServiceClient.class)
class PaymentServiceClientContractTest {

    @Autowired
    private PaymentServiceClient client;

    private static WireMockServer wireMock;

    @BeforeAll
    static void startWireMock() {
        wireMock = new WireMockServer(wireMockConfig().dynamicPort());
        wireMock.start();
    }

    @AfterAll
    static void stopWireMock() { wireMock.stop(); }

    @DynamicPropertySource
    static void configure(DynamicPropertyRegistry registry) {
        registry.add("integration.payment-service.base-url", wireMock::baseUrl);
    }

    @Test
    @DisplayName("Should parse successful payment response")
    void shouldHandleSuccessResponse() {
        wireMock.stubFor(post(urlEqualTo("/api/v1/payments"))
            .willReturn(aResponse()
                .withStatus(200)
                .withHeader("Content-Type", "application/json")
                .withBody("""
                    {"transactionId": "txn-123", "status": "APPROVED"}
                    """)));

        StepVerifier.create(client.processPayment(new PaymentRequest("order-1", BigDecimal.TEN)))
            .expectNextMatches(r -> r.status().equals("APPROVED"))
            .verifyComplete();
    }

    @Test
    @DisplayName("Should throw on payment service error")
    void shouldHandleErrorResponse() {
        wireMock.stubFor(post(urlEqualTo("/api/v1/payments"))
            .willReturn(aResponse().withStatus(500)));

        StepVerifier.create(client.processPayment(new PaymentRequest("order-1", BigDecimal.TEN)))
            .expectError(ServiceIntegrationException.class)
            .verify();
    }
}
```

## External API Clients — Resilience + WireMock

When an external API call is wrapped with resilience operators, test both the happy path and circuit-open path through WireMock.

```java
@ExtendWith(MockitoExtension.class)
class PaymentServiceClientResilienceTest {

    @Mock private CircuitBreakerRegistry cbRegistry;
    @Mock private RetryRegistry retryRegistry;
    @Mock private CircuitBreaker circuitBreaker;
    @Mock private Retry retry;
    @InjectMocks private PaymentServiceClient client;

    private static WireMockServer wireMock;

    @BeforeAll
    static void startWireMock() {
        wireMock = new WireMockServer(wireMockConfig().dynamicPort());
        wireMock.start();
    }

    @AfterAll
    static void stopWireMock() { wireMock.stop(); }

    @BeforeEach
    void setUp() {
        when(cbRegistry.circuitBreaker("payment-api")).thenReturn(circuitBreaker);
        when(retryRegistry.retry("payment-api")).thenReturn(retry);
    }

    @Test
    @DisplayName("Should process payment through resilience chain when API responds 200")
    void processPayment_shouldSucceed_whenApiResponds() {
        wireMock.stubFor(post(urlEqualTo("/api/v1/payments"))
            .willReturn(aResponse().withStatus(200)
                .withHeader("Content-Type", "application/json")
                .withBody("""
                    {"transactionId": "txn-123", "status": "APPROVED"}
                    """)));

        StepVerifier.create(client.processPayment(new PaymentRequest("order-1", BigDecimal.TEN)))
            .expectNextMatches(r -> r.status().equals("APPROVED"))
            .verifyComplete();
    }

    @Test
    @DisplayName("Should fallback when circuit breaker is open for payment API")
    void processPayment_shouldFallback_whenCircuitBreakerOpen() {
        when(cbRegistry.circuitBreaker("payment-api"))
            .thenThrow(CallNotPermittedException.createCallNotPermittedException(circuitBreaker));

        StepVerifier.create(client.processPayment(new PaymentRequest("order-1", BigDecimal.TEN)))
            .expectErrorMatches(t ->
                t instanceof ServiceIntegrationException &&
                t.getMessage().contains("payment"))
            .verify();
    }
}
```

## Coverage Standards

| Metric | Minimum | Tool |
|--------|---------|------|
| Line coverage | 90% | JaCoCo |
| Branch coverage | 80% | JaCoCo |
| Mutation score | 70% | PIT (optional) |

Enforce via CI pipeline. PRs below threshold are blocked.

## Testing Checklist

- [ ] Unit tests use `@ExtendWith(MockitoExtension.class)`, NOT `@SpringBootTest`
- [ ] All reactive streams tested with `StepVerifier`
- [ ] No `.block()` calls in any test
- [ ] BlockHound installed in base test class
- [ ] Test data uses builder pattern for readability
- [ ] Resilience registries mocked (`CircuitBreakerRegistry`, `RetryRegistry`, `TimeLimiterRegistry`)
- [ ] Registry instances retrieved by configured name (e.g., `"database"`)
- [ ] Happy path: resilience operators don't break normal flow
- [ ] Circuit breaker open: `CallNotPermittedException` -> fallback with context
- [ ] Retry: transient failure -> success on retry, `verify(repo, times(N))`
- [ ] Timeout: slow operation -> `TimeoutException`
- [ ] Fallback includes context (IDs, error details) in error message
- [ ] External API clients tested with resilience operators + WireMock
- [ ] Integration tests use Testcontainers (not H2)
- [ ] External API clients have contract tests with WireMock
- [ ] `@DisplayName` on every test method
- [ ] 90%+ line coverage, 80%+ branch coverage

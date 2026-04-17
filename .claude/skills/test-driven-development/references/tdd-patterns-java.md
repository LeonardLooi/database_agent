# TDD Patterns — Java 21 / Spring Boot WebFlux

## Test Structure (JUnit 5)

```java
// Unit test — no Spring context
class UserServiceTest {

    @Mock UserRepository userRepository;
    @InjectMocks UserService userService;

    @BeforeEach
    void setUp() {
        MockitoAnnotations.openMocks(this);
    }

    @Test
    void createUser_withDuplicateEmail_throwsConflictException() {
        // ARRANGE
        String email = "test@example.com";
        when(userRepository.findByEmail(email))
            .thenReturn(Mono.just(existingUser()));

        // ACT
        Mono<User> result = userService.createUser(newUserRequest(email));

        // ASSERT
        StepVerifier.create(result)
            .expectError(ConflictException.class)
            .verify();
    }
}
```

## Integration Test (WebFlux / WebTestClient)

```java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureWebTestClient
class UserControllerIntegrationTest {

    @Autowired WebTestClient webTestClient;

    @Test
    void POST_users_withValidRequest_returns201() {
        webTestClient.post()
            .uri("/api/users")
            .bodyValue(validCreateUserRequest())
            .exchange()
            .expectStatus().isCreated()
            .expectBody()
            .jsonPath("$.id").isNotEmpty()
            .jsonPath("$.email").isEqualTo("test@example.com");
    }
}
```

## Slice Test (@WebFluxTest)

```java
@WebFluxTest(UserController.class)
class UserControllerTest {

    @Autowired WebTestClient webTestClient;
    @MockBean UserService userService;

    @Test
    void GET_users_id_whenNotFound_returns404() {
        when(userService.findById("unknown"))
            .thenReturn(Mono.error(new NotFoundException("User not found")));

        webTestClient.get()
            .uri("/api/users/unknown")
            .exchange()
            .expectStatus().isNotFound();
    }
}
```

## Reactive Testing with StepVerifier

```java
// Verify sequence of emitted items
StepVerifier.create(userService.listUsers())
    .expectNextMatches(user -> user.email().equals("a@test.com"))
    .expectNextMatches(user -> user.email().equals("b@test.com"))
    .verifyComplete();

// Verify error
StepVerifier.create(userService.findById("missing"))
    .expectErrorMessage("User not found")
    .verify();
```

## Mocking Rules

- Use `@Mock` + `@InjectMocks` for unit tests (no Spring context)
- Use `@MockBean` for slice tests that load Spring context
- Mock at the boundary (repository, external HTTP client) — not at service internals
- Always use `Mono.just()` / `Mono.error()` / `Flux.just()` for reactive mock returns

## RED-GREEN Example

```bash
# RED — run test, see it fail
./mvnw test -pl :service -Dtest=UserServiceTest#createUser_withDuplicateEmail_throwsConflictException
# Expected: FAILED — ConflictException not thrown yet

# GREEN — implement logic, run again
./mvnw test -pl :service -Dtest=UserServiceTest#createUser_withDuplicateEmail_throwsConflictException
# Expected: PASSED

# Full suite — ensure no regressions
./mvnw test
```

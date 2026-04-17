# Spring Boot WebFlux Code Templates

Production-ready code templates for Java 21 + Spring Boot 3.5.x WebFlux development.

## Application Entry Point
```java
@SpringBootApplication
public class MyServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(MyServiceApplication.class, args);
    }
}
```

## DTO (record)
```java
public record CreateUserRequest(
    @NotBlank String email,
    @NotBlank @Size(max = 100) String firstName,
    @NotBlank @Size(max = 100) String lastName
) {}

public record UserResponse(
    UUID id, String email, String firstName, String lastName, Instant createdAt
) {}
```

## R2DBC Entity
```java
@Table("users")
public class UserEntity {
    @Id private UUID id;
    private String email;
    private String firstName;
    private String lastName;
    private Instant createdAt;
    private Instant updatedAt;
    // getters, setters, builder
}
```

## Repository
```java
public interface UserRepository extends ReactiveCrudRepository<UserEntity, UUID> {
    Mono<UserEntity> findByEmail(String email);
    Flux<UserEntity> findByLastName(String lastName);
}
```

## Service
```java
@Service
@RequiredArgsConstructor
public class UserService {
    private final UserRepository userRepository;

    public Mono<UserResponse> findById(UUID id) {
        return userRepository.findById(id)
                .map(this::toResponse)
                .switchIfEmpty(Mono.error(new ResourceNotFoundException("User not found")));
    }

    public Flux<UserResponse> findAll() {
        return userRepository.findAll().map(this::toResponse);
    }

    public Mono<UserResponse> create(CreateUserRequest request) {
        var entity = new UserEntity();
        entity.setEmail(request.email());
        entity.setFirstName(request.firstName());
        entity.setLastName(request.lastName());
        entity.setCreatedAt(Instant.now());
        entity.setUpdatedAt(Instant.now());
        return userRepository.save(entity).map(this::toResponse);
    }

    private UserResponse toResponse(UserEntity e) {
        return new UserResponse(e.getId(), e.getEmail(), e.getFirstName(), e.getLastName(), e.getCreatedAt());
    }
}
```

## Controller
```java
@RestController
@RequestMapping("/api/v1/users")
@RequiredArgsConstructor
public class UserController {
    private final UserService userService;

    @GetMapping("/{id}")
    public Mono<UserResponse> getById(@PathVariable UUID id) {
        return userService.findById(id);
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Mono<UserResponse> create(@Valid @RequestBody CreateUserRequest request) {
        return userService.create(request);
    }

    @GetMapping
    public Flux<UserResponse> getAll() {
        return userService.findAll();
    }
}
```

## Test
```java
@SpringBootTest
@AutoConfigureWebTestClient
class UserControllerTest {

    @Autowired WebTestClient webTestClient;

    @Test
    void createUser_shouldReturn201() {
        var request = new CreateUserRequest("john@example.com", "John", "Doe");

        webTestClient.post().uri("/api/v1/users")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(request)
                .exchange()
                .expectStatus().isCreated()
                .expectBody()
                .jsonPath("$.email").isEqualTo("john@example.com");
    }
}
```

## Global Error Handler
```java
@ControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<ProblemDetail> handleNotFound(ResourceNotFoundException ex) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, ex.getMessage());
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(pd);
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ProblemDetail> handleValidation(MethodArgumentNotValidException ex) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, "Validation failed");
        return ResponseEntity.badRequest().body(pd);
    }
}
```

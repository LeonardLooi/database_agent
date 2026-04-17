# Spring Boot Caching — @Cacheable / @CacheEvict / Caffeine

Caching guide for Java 21 + Spring Boot 3.5.x. Uses Caffeine as the in-process cache (default for Spring Boot when `spring-boot-starter-cache` + `com.github.ben-manes.caffeine:caffeine` are on the classpath).

## Setup

### pom.xml dependencies

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-cache</artifactId>
</dependency>
<dependency>
    <groupId>com.github.ben-manes.caffeine</groupId>
    <artifactId>caffeine</artifactId>
</dependency>
```

### Enable caching

```java
@SpringBootApplication
@EnableCaching
public class Application { ... }
```

### application.yml — Caffeine spec

```yaml
spring:
  cache:
    type: caffeine
    caffeine:
      spec: maximumSize=1000,expireAfterWrite=10m
    cache-names:
      - users
      - products
      - permissions
```

### Per-cache tuning (programmatic — overrides yml for fine control)

```java
@Configuration
public class CacheConfig {

    @Bean
    public CacheManager cacheManager() {
        CaffeineCacheManager manager = new CaffeineCacheManager();
        manager.registerCustomCache("users",
            Caffeine.newBuilder()
                .maximumSize(500)
                .expireAfterWrite(5, TimeUnit.MINUTES)
                .recordStats()
                .build());
        manager.registerCustomCache("permissions",
            Caffeine.newBuilder()
                .maximumSize(10_000)
                .expireAfterAccess(30, TimeUnit.MINUTES)
                .build());
        return manager;
    }
}
```

## Annotations

### @Cacheable — Cache a method's return value

```java
@Service
public class UserService {

    @Cacheable(value = "users", key = "#id")
    public Mono<UserResponse> findById(UUID id) {
        return userRepository.findById(id).map(userMapper::toResponse);
    }

    // Cache unless result is null
    @Cacheable(value = "users", key = "#email", unless = "#result == null")
    public Mono<UserResponse> findByEmail(String email) {
        return userRepository.findByEmail(email).map(userMapper::toResponse);
    }
}
```

### @CacheEvict — Remove entries on write/delete

```java
@CacheEvict(value = "users", key = "#id")
public Mono<UserResponse> updateUser(UUID id, UpdateUserRequest request) {
    return userRepository.findById(id)
        .flatMap(user -> userRepository.save(userMapper.update(user, request)))
        .map(userMapper::toResponse);
}

// Evict ALL entries in a cache (e.g., after bulk update)
@CacheEvict(value = "permissions", allEntries = true)
public Mono<Void> refreshPermissions() {
    return permissionRepository.reloadAll().then();
}
```

### @CachePut — Always update the cache (write-through)

```java
@CachePut(value = "users", key = "#result.id")
public Mono<UserResponse> createUser(CreateUserRequest request) {
    return userRepository.save(userMapper.toEntity(request))
        .map(userMapper::toResponse);
}
```

### @Caching — Combine multiple cache operations

```java
@Caching(evict = {
    @CacheEvict(value = "users", key = "#id"),
    @CacheEvict(value = "permissions", allEntries = true)
})
public Mono<Void> deleteUser(UUID id) {
    return userRepository.deleteById(id);
}
```

## WebFlux / Reactive Caveat

Spring Cache annotations are **proxy-based** and work synchronously. With WebFlux `Mono`/`Flux`, the cache stores the publisher, not the emitted value — this means the cached value is the `Mono` object itself.

**For reactive caching, use `ReactiveCache` or cache at the service boundary with `.cache()` operator:**

```java
// Option 1: Use .cache() on Mono (built-in Reactor memoization)
private final Mono<List<Permission>> cachedPermissions =
    permissionRepository.findAll().collectList().cache(Duration.ofMinutes(10));

// Option 2: Use Spring Cache on a blocking helper called from the reactive chain
// (wraps in Schedulers.boundedElastic())
@Cacheable("users")
public UserResponse findByIdBlocking(UUID id) {
    return userRepository.findById(id).map(userMapper::toResponse).block();
}
```

**Rule:** `@Cacheable` on a method returning `Mono<T>` caches the `Mono` wrapper, not the `T`. This is only correct if the same `Mono` is subscribed to multiple times (it is reused from cache). Prefer `Mono.cache()` for reactive caching.

## Eviction Strategies

| Strategy | Caffeine spec key | When to use |
|---|---|---|
| Time-to-live (TTL) | `expireAfterWrite=10m` | Reference data, permissions, config |
| Time-to-idle (TTI) | `expireAfterAccess=30m` | Session-like data accessed infrequently |
| Size-based LRU | `maximumSize=1000` | High-volume lookups with bounded memory |
| Reference-based | `softValues()` | Memory-sensitive caches (GC can evict) |

## Cache Statistics (Caffeine)

```java
// Enable in CacheManager config: .recordStats()
// Expose via actuator:
management:
  endpoint:
    caches:
      enabled: true
```

```bash
curl http://localhost:8080/actuator/caches        # list all caches
curl http://localhost:8080/actuator/caches/users  # stats for "users" cache
```

## Anti-Patterns

- **@Cacheable on void methods** — nothing to cache; use @CacheEvict instead
- **Caching mutable objects** — always cache immutable DTOs/records, never JPA entities
- **Missing cache eviction** — write operations MUST evict or update the cache
- **Caching reactive Mono without `.cache()` operator** — see Reactive Caveat above
- **Large cache entries** — cache fine-grained values (by ID), not entire lists

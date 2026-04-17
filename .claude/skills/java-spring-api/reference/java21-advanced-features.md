# Java 21 Advanced Features

Patterns for Java 21 LTS features not covered in `spring-boot-conventions.md`. Load this file when working with GraalVM, structured concurrency, virtual threads, JVM tuning, JMH benchmarking, or Spring Modulith.

---

## 1. GraalVM Native Image with Spring Boot 3.5.x

### When to use
- Cloud Run cold start must be < 1s
- Memory footprint must be < 256MB
- Serverless / scale-to-zero deployments

### Maven setup

```xml
<!-- pom.xml -->
<parent>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-starter-parent</artifactId>
  <version>3.5.0</version>
</parent>

<build>
  <plugins>
    <!-- Native Image plugin — replaces spring-boot-maven-plugin for native builds -->
    <plugin>
      <groupId>org.graalvm.buildtools</groupId>
      <artifactId>native-maven-plugin</artifactId>
    </plugin>
  </plugins>
</build>

<profiles>
  <profile>
    <id>native</id>
    <build>
      <plugins>
        <plugin>
          <groupId>org.graalvm.buildtools</groupId>
          <artifactId>native-maven-plugin</artifactId>
          <executions>
            <execution>
              <id>build-native</id>
              <goals><goal>compile-no-fork</goal></goals>
              <phase>package</phase>
            </execution>
          </executions>
        </plugin>
      </plugins>
    </build>
  </profile>
</profiles>
```

### Build commands

```bash
# JVM build (development)
./mvnw spring-boot:run

# Native image build (requires GraalVM JDK 21)
./mvnw -Pnative native:compile

# Docker multi-stage native build (CI/CD — no local GraalVM required)
./mvnw spring-boot:build-image -Pnative
```

### Reflection configuration

GraalVM requires explicit declaration of classes accessed via reflection. Spring Boot AOT handles most Spring beans automatically. Add manual hints only for non-Spring classes:

```java
// src/main/java/com/company/service/config/NativeHints.java
import org.springframework.aot.hint.RuntimeHints;
import org.springframework.aot.hint.RuntimeHintsRegistrar;
import org.springframework.context.annotation.ImportRuntimeHints;
import org.springframework.stereotype.Component;

@Component
@ImportRuntimeHints(NativeHints.class)
public class NativeHints implements RuntimeHintsRegistrar {

    @Override
    public void registerHints(RuntimeHints hints, ClassLoader classLoader) {
        // Register classes used via reflection (e.g., Jackson subtypes, SPI loaders)
        hints.reflection()
            .registerType(MyDomainEvent.class, hint -> hint
                .withMembers(MemberCategory.INVOKE_DECLARED_CONSTRUCTORS,
                             MemberCategory.DECLARED_FIELDS));

        // Register resources accessed at runtime
        hints.resources().registerPattern("templates/*.html");
    }
}
```

### Cloud Run native container config

```yaml
# Cloud Run — native image uses far less memory; adjust limits
resources:
  limits:
    cpu: "1"
    memory: "128Mi"   # Native: 128Mi vs JVM: 512Mi typical
  requests:
    cpu: "0.1"
    memory: "64Mi"

# Startup probe — native starts in ~100ms vs JVM ~3-5s
startupProbe:
  httpGet:
    path: /actuator/health
  initialDelaySeconds: 1
  periodSeconds: 1
  failureThreshold: 5
```

### Native image limitations
- No runtime bytecode generation (no CGLIB proxies on non-Spring beans)
- No runtime classpath scanning beyond what AOT detected at build time
- `@Profile` switching at runtime is not supported — bake profiles into the image
- Reflection on private fields requires explicit hints
- `Testcontainers` does not work in native test mode — use JVM mode for integration tests

---

## 2. Structured Concurrency (Java 21 — `StructuredTaskScope`)

### Rule: use structured concurrency for parallel independent calls, `Mono.zip()` for reactive chains

| Scenario | Use |
|----------|-----|
| Parallel blocking calls in a virtual thread context | `StructuredTaskScope` |
| Parallel reactive `Mono` / `Flux` chains | `Mono.zip()` / `Flux.merge()` |
| Never mix the two models in the same call chain | — |

### ShutdownOnFailure — all must succeed

```java
import java.util.concurrent.StructuredTaskScope;

// In a @Service method running on a virtual thread
public DashboardResponse buildDashboard(UUID userId) throws InterruptedException {
    try (var scope = StructuredTaskScope.ShutdownOnFailure.open()) {

        StructuredTaskScope.Subtask<UserProfile> profile =
            scope.fork(() -> userClient.getProfile(userId));

        StructuredTaskScope.Subtask<OrderHistory> orders =
            scope.fork(() -> orderClient.getHistory(userId));

        StructuredTaskScope.Subtask<NotificationCount> notifications =
            scope.fork(() -> notificationClient.getUnreadCount(userId));

        scope.join()           // wait for all subtasks
             .throwIfFailed(); // propagate first failure as exception

        return new DashboardResponse(
            profile.get(),
            orders.get(),
            notifications.get()
        );
    }
    // Scope closes here — all subtasks are guaranteed complete or cancelled
}
```

### ShutdownOnSuccess — first success wins

```java
// Use when any one result is sufficient (e.g., cache-or-db fallback)
public ProductData getProduct(String sku) throws InterruptedException {
    try (var scope = StructuredTaskScope.ShutdownOnSuccess<ProductData>.open()) {

        scope.fork(() -> cache.get(sku));       // fast path
        scope.fork(() -> database.find(sku));   // fallback

        return scope.join().result(); // returns first non-null success
    }
}
```

### Integration with Spring WebFlux

Structured concurrency runs on **virtual threads** (blocking model). Do NOT call `scope.fork()` inside a `Mono`/`Flux` chain — it blocks the reactive scheduler thread.

```java
// ✅ CORRECT — wrap the blocking structured concurrency call in Mono.fromCallable()
public Mono<DashboardResponse> getDashboard(UUID userId) {
    return Mono.fromCallable(() -> buildDashboard(userId))  // runs on boundedElastic
               .subscribeOn(Schedulers.boundedElastic());
}

// ❌ WRONG — calling scope.join() directly inside flatMap blocks the reactive thread
public Mono<DashboardResponse> getDashboard(UUID userId) {
    return Mono.just(userId)
               .flatMap(id -> {
                   var result = buildDashboard(id); // BLOCKS — do not do this
                   return Mono.just(result);
               });
}
```

---

## 3. Virtual Threads — Migration Guide

### Decision matrix: virtual threads vs WebFlux reactive

| Criteria | Virtual threads | WebFlux reactive |
|----------|----------------|-----------------|
| **Code style** | Imperative (familiar) | Functional/reactive (steeper learning curve) |
| **Backpressure** | ❌ None | ✅ Built-in |
| **Streaming (SSE / chunked)** | ❌ Limited | ✅ First-class |
| **Throughput (I/O-bound)** | ✅ Excellent | ✅ Excellent |
| **Throughput (CPU-bound)** | ❌ Same as platform threads | ❌ Same |
| **Library compatibility** | ✅ Any blocking library works | ❌ Must use reactive drivers |
| **Debugging / stack traces** | ✅ Normal stack traces | ❌ Difficult (operator chains) |
| **Workspace standard** | Legacy/greenfield services | **WebFlux (current standard)** |

**Rule for this workspace**: New services use WebFlux (reactive). Virtual threads are an option when integrating blocking third-party libraries that have no reactive driver.

### Enabling virtual threads in Spring Boot 3.5.x

```yaml
# application.yml — Spring Boot 3.2+ automatically uses virtual threads for Tomcat/Undertow
spring:
  threads:
    virtual:
      enabled: true
```

```java
// For programmatic virtual thread creation
Thread vThread = Thread.ofVirtual()
    .name("task-", 0)
    .start(() -> doBlockingWork());

// Using virtual thread executor
ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor();
```

### Virtual thread pitfalls to avoid

```java
// ❌ WRONG — synchronized block pins the virtual thread to its carrier thread
//    Pinning causes thread pool starvation under load
synchronized (this) {
    result = blockingCall();
}

// ✅ CORRECT — use ReentrantLock instead of synchronized
private final ReentrantLock lock = new ReentrantLock();

lock.lock();
try {
    result = blockingCall();
} finally {
    lock.unlock();
}
```

```java
// ❌ WRONG — ThreadLocal with virtual threads leaks memory
//    Each virtual thread gets its own ThreadLocal copy — at 1M threads this is 1M copies
private static final ThreadLocal<Connection> CONNECTION = new ThreadLocal<>();

// ✅ CORRECT — use ScopedValue (Java 21) for virtual thread context propagation
private static final ScopedValue<Connection> CONNECTION = ScopedValue.newInstance();

ScopedValue.where(CONNECTION, conn).run(() -> {
    // All code in this scope sees CONNECTION.get() == conn
    processRequest();
});
```

---

## 4. JVM Tuning for Spring Boot on Cloud Run

### GC selection guide

| Workload | Recommended GC | JVM flags |
|---------|----------------|-----------|
| Low-latency API (p99 < 10ms) | ZGC | `-XX:+UseZGC -XX:MaxGCPauseMillis=5` |
| High-throughput batch | G1GC (default) | `-XX:+UseG1GC -XX:MaxGCPauseMillis=200` |
| Container with small heap (< 512Mi) | SerialGC | `-XX:+UseSerialGC` |
| Cloud Run (scale-to-zero) | ZGC or Native | See GraalVM section |

### Cloud Run JVM container flags

```dockerfile
# Dockerfile — JVM flags for Cloud Run container
FROM eclipse-temurin:21-jre-alpine

ENV JAVA_OPTS="\
  -XX:+UseZGC \
  -XX:MaxRAMPercentage=75.0 \
  -XX:InitialRAMPercentage=50.0 \
  -XX:+ExitOnOutOfMemoryError \
  -Djava.security.egd=file:/dev/./urandom \
  -Dspring.backgroundpreinitializer.ignore=true"

COPY target/*.jar app.jar
ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar /app.jar"]
```

```
-XX:MaxRAMPercentage=75.0        # Use 75% of container memory limit for heap
-XX:InitialRAMPercentage=50.0    # Start at 50% to reduce startup memory spike
-XX:+ExitOnOutOfMemoryError      # Fail fast — let Cloud Run restart vs OOM zombie
```

### GC logging for diagnosis (enable in staging only)

```
-Xlog:gc*:file=/tmp/gc.log:time,uptime,level,tags:filecount=5,filesize=10m
```

Analyse with: `java -jar gctoolkit.jar /tmp/gc.log`

---

## 5. JMH Micro-Benchmarking

Use JMH to prove performance before and after optimizations. Never optimize without measurement.

### Maven setup

```xml
<dependency>
  <groupId>org.openjdk.jmh</groupId>
  <artifactId>jmh-core</artifactId>
  <version>1.37</version>
  <scope>test</scope>
</dependency>
<dependency>
  <groupId>org.openjdk.jmh</groupId>
  <artifactId>jmh-generator-annprocess</artifactId>
  <version>1.37</version>
  <scope>test</scope>
</dependency>
```

### Benchmark template

```java
import org.openjdk.jmh.annotations.*;
import java.util.concurrent.TimeUnit;

@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.MICROSECONDS)
@State(Scope.Benchmark)
@Warmup(iterations = 3, time = 1)    // 3 warmup rounds — let JIT compile
@Measurement(iterations = 5, time = 2)
@Fork(2)                              // 2 JVM forks — eliminates JIT state pollution
public class SerializationBenchmark {

    private ObjectMapper mapper;
    private MyDto dto;

    @Setup
    public void setup() {
        mapper = new ObjectMapper();
        dto = new MyDto("test", 42, List.of("a", "b"));
    }

    @Benchmark
    public String serializeWithJackson() throws Exception {
        return mapper.writeValueAsString(dto);
    }

    @Benchmark
    public MyDto deserializeWithJackson(Blackhole bh) throws Exception {
        String json = mapper.writeValueAsString(dto);
        bh.consume(json);                         // Prevent JIT dead-code elimination
        return mapper.readValue(json, MyDto.class);
    }
}
```

```bash
# Run benchmarks
mvn clean package -DskipTests
java -jar target/benchmarks.jar -rf json -rff results.json

# Quick single benchmark
java -jar target/benchmarks.jar SerializationBenchmark.serializeWithJackson -wi 3 -i 5 -f 1
```

### Rules
- Always use `@Fork(2)` minimum — single fork biases results with JIT warmup
- Use `Blackhole.consume()` for results that aren't returned — prevents dead-code elimination
- Benchmark in an environment matching production (same CPU generation, same JVM flags)
- Run GC between forks: `-jvmArgs "-XX:+UseZGC"`
- Report: "Reduced serialization from 42μs to 11μs (74% reduction) at p99"

---

## 6. Spring Modulith — Modular Monolith

Use when a microservices boundary is premature but package-level separation is needed.

### Maven dependency

```xml
<dependency>
  <groupId>org.springframework.modulith</groupId>
  <artifactId>spring-modulith-starter-core</artifactId>
</dependency>
<dependency>
  <groupId>org.springframework.modulith</groupId>
  <artifactId>spring-modulith-starter-test</artifactId>
  <scope>test</scope>
</dependency>
```

### Package structure (Modulith convention)

```
com.company.myservice/
  orders/               ← module root (public API of orders module)
    OrderService.java   ← public — accessible from other modules
    OrderController.java
    internal/           ← internal package — NOT accessible from other modules
      OrderRepository.java
      OrderMapper.java
  payments/             ← module root
    PaymentService.java ← public
    internal/
      PaymentRepository.java
  MyServiceApplication.java
```

### Inter-module communication via events

```java
// ✅ CORRECT — modules communicate via events, not direct service injection
// orders/OrderService.java
@Service
@RequiredArgsConstructor
public class OrderService {

    private final ApplicationEventPublisher events;

    public Order place(PlaceOrderRequest request) {
        Order order = // ... create order
        events.publishEvent(new OrderPlaced(order.id(), order.total()));
        return order;
    }
}

// payments/PaymentListener.java
@ApplicationModuleListener  // Spring Modulith annotation — transactional listener
public class PaymentListener {

    @EventListener
    void on(OrderPlaced event) {
        // Process payment triggered by order placement
    }
}

// ❌ WRONG — direct cross-module service injection couples modules
@Service
public class OrderService {
    @Autowired
    private PaymentService paymentService; // breaks module boundary
}
```

### Module boundary verification test

```java
// src/test/java/com/company/myservice/ModularityTests.java
@SpringBootTest
class ModularityTests {

    @Test
    void verifyModularStructure() {
        ApplicationModules modules = ApplicationModules.of(MyServiceApplication.class);
        modules.verify(); // fails if any module accesses another module's internal package
    }

    @Test
    void writeModuleDocumentation() {
        new Documenter(ApplicationModules.of(MyServiceApplication.class))
            .writeModulesAsPlantUml()
            .writeIndividualModulesAsPlantUml();
    }
}
```

---

## 7. Java 21 Language Features Quick Reference

### Sequenced Collections (Java 21)

```java
// New interfaces: SequencedCollection, SequencedSet, SequencedMap
List<String> list = new ArrayList<>(List.of("a", "b", "c"));

list.getFirst();          // "a" — replaces list.get(0)
list.getLast();           // "c" — replaces list.get(list.size()-1)
list.addFirst("z");       // insert at head
list.reversed();          // reversed view — no copy

LinkedHashMap<String, Integer> map = new LinkedHashMap<>();
map.putFirst("a", 1);
map.putLast("z", 26);
map.firstEntry();         // Map.Entry("a", 1)
```

### String Templates (Java 21 preview — use carefully)

```java
// Only use if team is on Java 21 with --enable-preview; avoid in libraries
String name = "World";
String greeting = STR."Hello, \{name}!";   // "Hello, World!"

// Multi-line with expressions
String query = STR."""
    SELECT *
    FROM users
    WHERE id = \{userId}
    AND status = '\{status}'
    """;
// Note: for SQL always use parameterized queries — STR templates do NOT sanitize
```

### Pattern Matching for Switch (GA in Java 21)

```java
// Replaces instanceof chains — use in service layer for type dispatch
public String describe(Object obj) {
    return switch (obj) {
        case Integer i when i > 0  -> "Positive integer: " + i;
        case Integer i             -> "Non-positive integer: " + i;
        case String s  when s.isBlank() -> "Blank string";
        case String s              -> "String of length " + s.length();
        case null                  -> "null";
        default                    -> "Unknown: " + obj.getClass().getSimpleName();
    };
}
```

### Record patterns (GA in Java 21)

```java
record Point(int x, int y) {}
record Rectangle(Point topLeft, Point bottomRight) {}

// Deconstruct nested records in pattern matching
if (shape instanceof Rectangle(Point(int x1, int y1), Point(int x2, int y2))) {
    int width = x2 - x1;
    int height = y2 - y1;
}
```

# Spring Boot Configuration Templates

## pom.xml Essentials
```xml
<project>
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.5.0</version>
    </parent>

    <properties>
        <java.version>21</java.version>
    </properties>

    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-webflux</artifactId>
            <exclusions>
                <exclusion>
                    <groupId>org.springframework.boot</groupId>
                    <artifactId>spring-boot-starter-logging</artifactId>
                </exclusion>
            </exclusions>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-r2dbc</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-validation</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-actuator</artifactId>
        </dependency>
        <dependency>
            <groupId>org.projectlombok</groupId>
            <artifactId>lombok</artifactId>
            <optional>true</optional>
        </dependency>
        <dependency>
            <groupId>org.postgresql</groupId>
            <artifactId>r2dbc-postgresql</artifactId>
            <scope>runtime</scope>
        </dependency>
        <dependency>
            <groupId>org.postgresql</groupId>
            <artifactId>postgresql</artifactId>
            <scope>runtime</scope>
        </dependency>
        <dependency>
            <groupId>org.flywaydb</groupId>
            <artifactId>flyway-core</artifactId>
        </dependency>
        <dependency>
            <groupId>org.flywaydb</groupId>
            <artifactId>flyway-database-postgresql</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>io.projectreactor</groupId>
            <artifactId>reactor-test</artifactId>
            <scope>test</scope>
        </dependency>
        <!-- Log4j2 (replaces default Logback) -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-log4j2</artifactId>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
            <plugin>
                <groupId>org.jacoco</groupId>
                <artifactId>jacoco-maven-plugin</artifactId>
                <version>${jacoco-maven-plugin.version}</version>
                <executions>
                    <execution>
                        <goals><goal>prepare-agent</goal></goals>
                    </execution>
                    <execution>
                        <id>report</id>
                        <phase>prepare-package</phase>
                        <goals><goal>report</goal></goals>
                    </execution>
                    <execution>
                        <id>check</id>
                        <goals><goal>check</goal></goals>
                        <configuration>
                            <rules>
                                <rule>
                                    <element>BUNDLE</element>
                                    <limits>
                                        <limit>
                                            <counter>LINE</counter>
                                            <value>COVEREDRATIO</value>
                                            <minimum>0.90</minimum>
                                        </limit>
                                        <limit>
                                            <counter>BRANCH</counter>
                                            <value>COVEREDRATIO</value>
                                            <minimum>0.80</minimum>
                                        </limit>
                                    </limits>
                                </rule>
                            </rules>
                        </configuration>
                    </execution>
                </executions>
            </plugin>
        </plugins>
    </build>
</project>
```

## application.yml Template
```yaml
spring:
  r2dbc:
    url: r2dbc:postgresql://localhost:5432/mydb
    username: ${DB_USERNAME:postgres}
    password: ${DB_PASSWORD:postgres}
  flyway:
    url: jdbc:postgresql://localhost:5432/mydb
    user: ${DB_USERNAME:postgres}
    password: ${DB_PASSWORD:postgres}
    enabled: ${FLYWAY_ENABLED:false}
  webflux:
    base-path: /
  lifecycle:
    timeout-per-shutdown-phase: 30s

server:
  port: 8080
  shutdown: graceful
  server-header: ""  # Suppress Server header to prevent information disclosure

management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics

logging:
  config: classpath:log4j2-spring.xml
```

## Proxy Headers — ForwardedHeaderTransformer

Spring WebFlux does NOT trust `X-Forwarded-For`, `X-Forwarded-Host`, or `X-Forwarded-Proto` by default. Without this bean, the application sees the load balancer's IP rather than the real client IP — breaking rate limiting, audit logging, and geo-restrictions.

```java
@Bean
public ForwardedHeaderTransformer forwardedHeaderTransformer() {
    return new ForwardedHeaderTransformer();
}
```

Place this in your main `@Configuration` class or `SecurityConfig`.

**What it does:**
- Rewrites the `ServerWebExchange` host/scheme/IP from `X-Forwarded-*` headers before request processing
- Makes `exchange.getRequest().getRemoteAddress()` return the real client IP (not the proxy IP)
- Required when running behind Cloud Run, an NGINX reverse proxy, or any load balancer

**Security note:** Only enable this if your infrastructure actually passes `X-Forwarded-For` from a trusted proxy. If traffic can reach the app directly (not via proxy), an attacker can spoof the header. On Cloud Run + GCP Load Balancer, enabling this bean is safe — the infrastructure strips attacker-injected headers.

**Verification:**
```java
// In a test or health endpoint — should return real client IP, not 127.0.0.1
String clientIp = exchange.getRequest().getRemoteAddress()
    .getAddress().getHostAddress();
```

**`application.yml` alternative (Spring Boot 3.1+):**
```yaml
server:
  forward-headers-strategy: framework  # equivalent to registering ForwardedHeaderTransformer bean
```

## Type-Safe Configuration Properties

Use Java records with `@ConfigurationProperties` for type-safe, immutable configuration. Prefer this over scattered `@Value` annotations.

```java
@ConfigurationProperties(prefix = "integration.payment-service")
public record PaymentServiceProperties(
    @NotBlank String baseUrl,
    @NotBlank String apiKey,
    @Min(100) int timeoutMs
) {}

// Enable in application class or a @Configuration class
@SpringBootApplication
@EnableConfigurationProperties(PaymentServiceProperties.class)
public class MyServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(MyServiceApplication.class, args);
    }
}
```

```yaml
integration:
  payment-service:
    base-url: ${PAYMENT_SERVICE_URL:http://localhost:8081}
    api-key: ${PAYMENT_SERVICE_API_KEY}
    timeout-ms: 5000
```

## log4j2-spring.xml Template

Place in `src/main/resources/log4j2-spring.xml`. Uses structured JSON for production, console pattern for local dev.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Configuration status="WARN" monitorInterval="30">
    <Properties>
        <Property name="APP_NAME">${spring:spring.application.name:-my-service}</Property>
        <Property name="LOG_PATTERN">%d{ISO8601} [%t] %-5level %logger{36} - %msg%n</Property>
    </Properties>

    <Appenders>
        <Console name="Console" target="SYSTEM_OUT">
            <PatternLayout pattern="${LOG_PATTERN}"/>
        </Console>
        <!-- JSON appender for production (structured logging) -->
        <Console name="JsonConsole" target="SYSTEM_OUT">
            <JsonTemplateLayout eventTemplateUri="classpath:EcsLayout.json"/>
        </Console>
    </Appenders>

    <Loggers>
        <Logger name="com.company" level="DEBUG" additivity="false">
            <AppenderRef ref="Console"/>
        </Logger>
        <Logger name="org.springframework" level="INFO" additivity="false">
            <AppenderRef ref="Console"/>
        </Logger>
        <Logger name="io.github.resilience4j" level="INFO" additivity="false">
            <AppenderRef ref="Console"/>
        </Logger>
        <Root level="INFO">
            <AppenderRef ref="Console"/>
        </Root>
    </Loggers>
</Configuration>
```

## Structured Logging — Spring Boot 3.4+

Spring Boot 3.4 introduced native structured logging with zero additional dependencies.

### Option A: Native Structured Logging (Spring Boot 3.4+, recommended)

In `application.yml`:
```yaml
logging:
  structured:
    format:
      console: ecs          # Elastic Common Schema JSON — works with Logstash, Grafana Loki
      # alternatives: logstash | gelf
  level:
    root: INFO
    com.yourcompany: DEBUG
```

This outputs every log line as JSON automatically. No additional dependencies needed.

### Option B: logstash-logback-encoder (Spring Boot < 3.4 fallback)

In `pom.xml`:
```xml
<dependency>
    <groupId>net.logstash.logback</groupId>
    <artifactId>logstash-logback-encoder</artifactId>
    <version>8.0</version>
</dependency>
```

In `src/main/resources/logback-spring.xml`:
```xml
<configuration>
    <appender name="JSON" class="ch.qos.logback.core.ConsoleAppender">
        <encoder class="net.logstash.logback.encoder.LogstashEncoder">
            <includeCallerData>false</includeCallerData>
        </encoder>
    </appender>
    <root level="INFO">
        <appender-ref ref="JSON"/>
    </root>
</configuration>
```

### MDC Correlation IDs (Distributed Tracing)

Add trace context to every log line using `MDC` (Mapped Diagnostic Context):

```java
import org.slf4j.MDC;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import org.springframework.web.server.WebFilter;
import org.springframework.web.server.WebFilterChain;
import reactor.core.publisher.Mono;
import java.util.UUID;

@Component
public class CorrelationIdFilter implements WebFilter {

    private static final String TRACE_ID = "traceId";
    private static final String HEADER = "X-Trace-Id";

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, WebFilterChain chain) {
        String traceId = exchange.getRequest().getHeaders()
            .getFirst(HEADER);
        if (traceId == null) traceId = UUID.randomUUID().toString();

        exchange.getResponse().getHeaders().set(HEADER, traceId);

        final String finalTraceId = traceId;
        return chain.filter(exchange)
            .contextWrite(ctx -> ctx.put(TRACE_ID, finalTraceId))
            .doOnSubscribe(s -> MDC.put(TRACE_ID, finalTraceId))
            .doFinally(s -> MDC.remove(TRACE_ID));
    }
}
```

Every log line will now include `"traceId":"abc-123"` in the JSON output — enabling cross-service request tracing in Grafana Loki or ELK stack.

### Verification
Run your service and confirm log output is JSON:
```bash
mvn spring-boot:run 2>&1 | head -5
# Expected: {"@timestamp":"...","log.level":"INFO","traceId":"...","message":"..."}
```

# Health Endpoint Patterns

Every deployed service MUST expose a `/health` endpoint. This is required by:
- Cloud Run health check configuration
- Docker HEALTHCHECK instruction
- Load balancer health probes
- CI/CD deploy verification step

---

## NestJS 11.x — Health Controller

```typescript
// src/health/health.controller.ts
import { Controller, Get } from '@nestjs/common';
import { InjectDataSource } from '@nestjs/typeorm';
import { DataSource } from 'typeorm';

@Controller('health')
export class HealthController {
  constructor(
    @InjectDataSource() private readonly dataSource: DataSource,
  ) {}

  @Get()
  async check() {
    const dbConnected = this.dataSource.isInitialized;

    if (!dbConnected) {
      throw new Error('Database not connected');
    }

    return {
      status: 'ok',
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
      database: dbConnected ? 'ok' : 'error',
      version: process.env['APP_VERSION'] ?? 'unknown',
    };
  }
}
```

For `@nestjs/terminus` (recommended for production):
```typescript
// src/health/health.controller.ts
import { Controller, Get } from '@nestjs/common';
import {
  HealthCheck,
  HealthCheckService,
  TypeOrmHealthIndicator,
} from '@nestjs/terminus';

@Controller('health')
export class HealthController {
  constructor(
    private health: HealthCheckService,
    private db: TypeOrmHealthIndicator,
  ) {}

  @Get()
  @HealthCheck()
  check() {
    return this.health.check([
      () => this.db.pingCheck('database'),
    ]);
  }
}
```

---

## Spring Boot 3.5.x WebFlux — Actuator Health

Spring Boot exposes `/actuator/health` automatically via `spring-boot-starter-actuator`.

```yaml
# application.yml
management:
  endpoints:
    web:
      exposure:
        include: health,info
  endpoint:
    health:
      show-details: when-authorized   # never expose full details publicly
      probes:
        enabled: true                 # enables /actuator/health/liveness and /actuator/health/readiness
  health:
    livenessstate:
      enabled: true
    readinessstate:
      enabled: true
```

Cloud Run health check target: `GET /actuator/health` → 200 with `{"status":"UP"}`

Custom health indicator:
```java
// src/main/java/com/example/health/DatabaseHealthIndicator.java
@Component
public class DatabaseHealthIndicator implements ReactiveHealthIndicator {

    private final R2dbcEntityTemplate template;

    @Override
    public Mono<Health> health() {
        return template.getDatabaseClient()
            .sql("SELECT 1")
            .fetch()
            .first()
            .map(r -> Health.up().withDetail("database", "ok").build())
            .onErrorReturn(Health.down().withDetail("database", "unreachable").build());
    }
}
```

---

## Python FastAPI 3.14 — Health Endpoint

```python
# src/api/health.py
import os
import time
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

router = APIRouter(tags=["health"])

_start_time = time.time()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    # Verify DB connectivity
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "timestamp": time.time(),
        "uptime_seconds": int(time.time() - _start_time),
        "database": db_status,
        "version": os.getenv("APP_VERSION", "unknown"),
    }
```

---

## Cloud Run Health Check Configuration

```yaml
# In GitHub Actions deploy step:
- name: Deploy to Cloud Run
  run: |
    gcloud run deploy $SERVICE_NAME \
      --image $IMAGE_URL \
      --health-check-type=http \
      --liveness-probe-path=/health \
      --readiness-probe-path=/health \
      --startup-probe-path=/health \
      --startup-probe-initial-delay=10 \
      --startup-probe-timeout=5 \
      --startup-probe-failure-threshold=3
```

---

## Health Check Anti-Patterns

- **No DB check in health endpoint** — returns 200 even when database is down; Cloud Run won't detect failed revisions
- **Exposing sensitive info** — never include stack traces, connection strings, or internal IPs in health responses
- **Slow health checks** — health endpoint must respond in < 3 seconds; never run expensive queries
- **Missing health endpoint entirely** — Cloud Run defaults to TCP port check only; HTTP health check is more reliable

---

## Verify Step

After adding health endpoint:
```bash
# Local verification:
curl http://localhost:3000/health            # NestJS
curl http://localhost:8080/actuator/health   # Spring Boot
curl http://localhost:8000/health            # FastAPI

# Expected: HTTP 200 with JSON body containing "status": "ok"
```

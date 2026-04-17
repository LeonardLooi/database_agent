# NestJS Debugging — Production Monitoring

Production debugging patterns, structured logging, health checks, and request tracing for NestJS 11.x. For performance profiling and memory debugging, see `nestjs-debugging-performance.md`.

## 1. Structured Logging with Context

```typescript
// src/common/logging/logger.service.ts
import { Injectable, Logger, LoggerService } from '@nestjs/common';
import { getCorrelationId, getUserId } from '../context/request-context.service';

@Injectable()
export class StructuredLogger implements LoggerService {
  private readonly logger = new Logger();

  log(message: string, context?: string, metadata?: Record<string, any>) {
    this.logger.log(this.formatMessage(message, metadata), context);
  }

  error(message: string, trace?: string, context?: string, metadata?: Record<string, any>) {
    this.logger.error(this.formatMessage(message, metadata), trace, context);
  }

  warn(message: string, context?: string, metadata?: Record<string, any>) {
    this.logger.warn(this.formatMessage(message, metadata), context);
  }

  debug(message: string, context?: string, metadata?: Record<string, any>) {
    this.logger.debug(this.formatMessage(message, metadata), context);
  }

  verbose(message: string, context?: string, metadata?: Record<string, any>) {
    this.logger.verbose(this.formatMessage(message, metadata), context);
  }

  private formatMessage(message: string, metadata?: Record<string, any>): string {
    const correlationId = getCorrelationId();
    const userId = getUserId();

    const logObject = {
      message,
      correlationId,
      userId,
      timestamp: new Date().toISOString(),
      ...metadata,
    };

    return JSON.stringify(logObject);
  }
}
```

## 2. Health Check with Dependency Monitoring

```typescript
// src/health/health.service.ts
import { Injectable } from '@nestjs/common';
import { PrismaService } from '../database/prisma.service';
import { CircuitBreakerRegistry } from '../resilience/circuit-breaker.registry';

interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  uptime: number;
  checks: {
    database: { status: string; latency?: number; error?: string };
    memory: { status: string; heapUsed: string; heapTotal: string };
    circuits: { status: string; openCount: number; details?: any };
  };
}

@Injectable()
export class HealthService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly circuitRegistry: CircuitBreakerRegistry,
  ) {}

  async getHealth(): Promise<HealthStatus> {
    const checks = {
      database: await this.checkDatabase(),
      memory: this.checkMemory(),
      circuits: this.checkCircuits(),
    };

    const status = this.determineOverallStatus(checks);

    return {
      status,
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
      checks,
    };
  }

  private async checkDatabase(): Promise<any> {
    const start = performance.now();
    try {
      await this.prisma.$queryRaw`SELECT 1`;
      const latency = performance.now() - start;
      return {
        status: latency < 100 ? 'healthy' : 'degraded',
        latency: Math.round(latency),
      };
    } catch (error) {
      return {
        status: 'unhealthy',
        error: error.message,
      };
    }
  }

  private checkMemory(): any {
    const usage = process.memoryUsage();
    const heapUsedMB = usage.heapUsed / 1024 / 1024;
    const heapTotalMB = usage.heapTotal / 1024 / 1024;
    const heapPercentage = (heapUsedMB / heapTotalMB) * 100;

    return {
      status: heapPercentage < 80 ? 'healthy' : heapPercentage < 95 ? 'degraded' : 'unhealthy',
      heapUsed: `${heapUsedMB.toFixed(2)} MB`,
      heapTotal: `${heapTotalMB.toFixed(2)} MB`,
    };
  }

  private checkCircuits(): any {
    const states = this.circuitRegistry.getAllStates();
    const openCount = states.filter(s => s.state === 'OPEN').length;

    return {
      status: openCount === 0 ? 'healthy' : openCount < 3 ? 'degraded' : 'unhealthy',
      openCount,
      details: states.filter(s => s.state === 'OPEN'),
    };
  }

  private determineOverallStatus(checks: any): 'healthy' | 'degraded' | 'unhealthy' {
    const statuses = [checks.database.status, checks.memory.status, checks.circuits.status];

    if (statuses.includes('unhealthy')) return 'unhealthy';
    if (statuses.includes('degraded')) return 'degraded';
    return 'healthy';
  }
}
```

## 3. Request Tracing with Distributed Context

```typescript
// src/common/interceptors/tracing.interceptor.ts
import { Injectable, NestInterceptor, ExecutionContext, CallHandler, Logger } from '@nestjs/common';
import { Observable } from 'rxjs';
import { tap, catchError } from 'rxjs/operators';
import { getCorrelationId, updateContextMetadata } from '../context/request-context.service';

@Injectable()
export class TracingInterceptor implements NestInterceptor {
  private readonly logger = new Logger(TracingInterceptor.name);

  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    const request = context.switchToHttp().getRequest();
    const { method, url } = request;
    const correlationId = getCorrelationId();
    const startTime = Date.now();

    this.logger.log(`[${correlationId}] → ${method} ${url}`, 'Tracing');

    return next.handle().pipe(
      tap(() => {
        const duration = Date.now() - startTime;
        updateContextMetadata({ requestDuration: duration });
        this.logger.log(
          `[${correlationId}] ← ${method} ${url} (${duration}ms)`,
          'Tracing'
        );
      }),
      catchError((error) => {
        const duration = Date.now() - startTime;
        this.logger.error(
          `[${correlationId}] ✗ ${method} ${url} (${duration}ms): ${error.message}`,
          error.stack,
          'Tracing'
        );
        throw error;
      })
    );
  }
}
```

## 4. Debugging Best Practices

### Development Environment

- Use `logger.debug()` liberally for detailed flow tracing
- Enable Prisma query logging to identify N+1 queries
- Use Fastify lifecycle hooks to track request processing stages
- Leverage Chrome DevTools for memory profiling and CPU profiling

### Production Environment

- Use structured JSON logging with correlation IDs
- Implement comprehensive health checks with dependency monitoring
- Monitor circuit breaker states via dedicated endpoints
- Track request duration and slow query warnings
- Use external APM tools (DataDog, New Relic, Sentry) for distributed tracing

### Common Pitfalls

- Never log sensitive data (passwords, tokens, PII)
- Avoid excessive logging in hot paths (use sampling)
- Clean up event listeners and timers in `OnModuleDestroy`
- Use connection pooling for database and external services
- Implement graceful shutdown to avoid connection leaks

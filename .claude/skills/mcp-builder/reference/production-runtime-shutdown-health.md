# Production Runtime — Graceful Shutdown & Health Checks

Graceful shutdown and Kubernetes health check patterns for production MCP servers. For multi-tenant support, see `production-runtime-multi-tenant.md`.

## 1. Graceful Shutdown Pattern (Kubernetes-Ready)

```typescript
// src/lifecycle/graceful-shutdown.ts
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { Server as HttpServer } from 'http';

export class GracefulShutdown {
  private isShuttingDown = false;
  private activeRequests = new Set<string>();
  private shutdownTimeout = 30000; // 30 seconds
  private mcpServer?: McpServer;
  private httpServer?: HttpServer;
  private cleanupCallbacks: Array<() => Promise<void>> = [];

  constructor(
    mcpServer?: McpServer,
    httpServer?: HttpServer,
    shutdownTimeout?: number
  ) {
    this.mcpServer = mcpServer;
    this.httpServer = httpServer;
    if (shutdownTimeout) {
      this.shutdownTimeout = shutdownTimeout;
    }
  }

  registerSignalHandlers(): void {
    const signals: NodeJS.Signals[] = ['SIGTERM', 'SIGINT', 'SIGUSR2'];

    signals.forEach((signal) => {
      process.on(signal, async () => {
        console.log(`Received ${signal}, starting graceful shutdown...`);
        await this.shutdown();
      });
    });

    process.on('uncaughtException', async (error) => {
      console.error('Uncaught exception:', error);
      await this.shutdown();
    });

    process.on('unhandledRejection', async (reason, promise) => {
      console.error('Unhandled rejection at:', promise, 'reason:', reason);
      await this.shutdown();
    });
  }

  trackRequest(requestId: string): () => void {
    if (this.isShuttingDown) {
      throw new Error('Server is shutting down, cannot accept new requests');
    }

    this.activeRequests.add(requestId);

    return () => {
      this.activeRequests.delete(requestId);
    };
  }

  onShutdown(callback: () => Promise<void>): void {
    this.cleanupCallbacks.push(callback);
  }

  async shutdown(): Promise<void> {
    if (this.isShuttingDown) return;

    this.isShuttingDown = true;
    console.log('Starting graceful shutdown...');

    try {
      // Step 1: Stop accepting new connections
      if (this.httpServer) {
        this.httpServer.close();
      }

      // Step 2: Wait for active requests with timeout
      if (this.activeRequests.size > 0) {
        const waitForRequests = new Promise<void>((resolve) => {
          const checkInterval = setInterval(() => {
            if (this.activeRequests.size === 0) {
              clearInterval(checkInterval);
              resolve();
            }
          }, 100);
        });

        const timeout = new Promise<void>((resolve) => {
          setTimeout(() => {
            console.warn(`Shutdown timeout. ${this.activeRequests.size} requests still active.`);
            resolve();
          }, this.shutdownTimeout);
        });

        await Promise.race([waitForRequests, timeout]);
      }

      // Step 3: Close MCP server connections
      if (this.mcpServer) {
        await this.mcpServer.close();
      }

      // Step 4: Run cleanup callbacks
      await Promise.all(this.cleanupCallbacks.map((cb) => cb()));

      console.log('Graceful shutdown completed successfully');
      process.exit(0);
    } catch (error) {
      console.error('Error during graceful shutdown:', error);
      process.exit(1);
    }
  }

  get shuttingDown(): boolean {
    return this.isShuttingDown;
  }

  get activeRequestCount(): number {
    return this.activeRequests.size;
  }
}
```

## 2. Kubernetes Health Checks

```typescript
// src/health/types.ts
export type HealthStatus = 'healthy' | 'degraded' | 'unhealthy';

export interface ComponentHealth {
  status: HealthStatus;
  latency_ms?: number;
  message?: string;
  last_checked: string;
}

export interface HealthCheckResult {
  status: HealthStatus;
  checks: Record<string, ComponentHealth>;
  version: string;
  uptime: number;
}

export type HealthCheckFunction = () => Promise<ComponentHealth>;
```

```typescript
// src/health/health-checker.ts
import { HealthCheckResult, HealthCheckFunction, ComponentHealth, HealthStatus } from './types.js';

export class HealthChecker {
  private checks = new Map<string, HealthCheckFunction>();
  private readonly version: string;
  private readonly startTime: number;

  constructor(version: string) {
    this.version = version;
    this.startTime = Date.now();
  }

  register(name: string, checkFn: HealthCheckFunction): void {
    this.checks.set(name, checkFn);
  }

  async runAll(): Promise<HealthCheckResult> {
    const checks: Record<string, ComponentHealth> = {};
    let overallStatus: HealthStatus = 'healthy';

    const results = await Promise.allSettled(
      Array.from(this.checks.entries()).map(async ([name, checkFn]) => {
        const result = await checkFn();
        return { name, result };
      })
    );

    for (const outcome of results) {
      if (outcome.status === 'fulfilled') {
        const { name, result } = outcome.value;
        checks[name] = result;

        if (result.status === 'unhealthy') {
          overallStatus = 'unhealthy';
        } else if (result.status === 'degraded' && overallStatus === 'healthy') {
          overallStatus = 'degraded';
        }
      } else {
        checks['unknown'] = {
          status: 'unhealthy',
          message: `Health check failed: ${outcome.reason}`,
          last_checked: new Date().toISOString(),
        };
        overallStatus = 'unhealthy';
      }
    }

    return { status: overallStatus, checks, version: this.version, uptime: Date.now() - this.startTime };
  }
}
```

```typescript
// src/health/endpoints.ts
import { FastifyInstance } from 'fastify';
import { HealthChecker } from './health-checker.js';

export function registerHealthEndpoints(app: FastifyInstance, checker: HealthChecker): void {
  // Liveness probe — always returns 200 if process is alive
  app.get('/health/live', async (request, reply) => {
    return reply.status(200).send({ status: 'alive', timestamp: new Date().toISOString() });
  });

  // Readiness probe — returns 503 if unhealthy
  app.get('/health/ready', async (request, reply) => {
    const result = await checker.runAll();
    const statusCode = result.status === 'unhealthy' ? 503 : 200;
    return reply.status(statusCode).send({ status: result.status, timestamp: new Date().toISOString() });
  });

  // Detailed health — full diagnostics for dashboards
  app.get('/health/detailed', async (request, reply) => {
    const result = await checker.runAll();
    const statusCode = result.status === 'unhealthy' ? 503 : 200;
    return reply.status(statusCode).send(result);
  });
}
```

```typescript
// src/health/checks/database.ts
import { Pool } from 'pg';
import { ComponentHealth } from '../types.js';

export function createDatabaseHealthCheck(pool: Pool) {
  return async (): Promise<ComponentHealth> => {
    const start = Date.now();
    try {
      await pool.query('SELECT 1');
      const latency = Date.now() - start;
      return {
        status: latency < 1000 ? 'healthy' : 'degraded',
        latency_ms: latency,
        message: latency < 1000 ? 'Database responding normally' : 'Database slow',
        last_checked: new Date().toISOString(),
      };
    } catch (error) {
      return {
        status: 'unhealthy',
        latency_ms: Date.now() - start,
        message: `Database connection failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
        last_checked: new Date().toISOString(),
      };
    }
  };
}
```

```typescript
// src/health/checks/external-api.ts
import { ComponentHealth } from '../types.js';
import { CircuitBreaker } from '../../utils/circuit-breaker.js';

export function createExternalApiHealthCheck(circuitBreaker: CircuitBreaker) {
  return async (): Promise<ComponentHealth> => {
    const state = circuitBreaker.getState();
    const stats = circuitBreaker.getStats();

    const status =
      state === 'open' ? 'unhealthy' :
      state === 'half-open' ? 'degraded' :
      'healthy';

    return {
      status,
      message: `Circuit breaker state: ${state}. Success rate: ${stats.successRate.toFixed(2)}%`,
      last_checked: new Date().toISOString(),
    };
  };
}
```

## Usage Notes

1. **Graceful Shutdown**: Handles SIGTERM/SIGINT, waits for active requests, runs cleanup callbacks
2. **Health Checks**: Liveness (process alive), Readiness (dependencies healthy), Detailed (full diagnostics)
3. **Request Tracking**: Track active requests for graceful shutdown, prevent new requests during shutdown

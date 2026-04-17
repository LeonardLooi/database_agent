# Enterprise Resilience Stack for MCP Servers

This document provides production-ready resilience patterns for MCP servers that integrate with external APIs.

## Resilience Flow Diagram

```
User Request → Rate Limiter → Bulkhead → Circuit Breaker → Retry Strategy → Connection Pool → External API
     ↓              ↓             ↓              ↓                ↓                 ↓              ↓
  Validate    Reject if     Queue if      Skip if          Exponential        Reuse TCP      Response
   Input      rate limit    saturated     open            backoff + jitter   connections
```

## Circuit Breaker Implementation

> **⚠️ Production Warning: Circuit breakers MUST use shared state in multi-instance deployments.**
>
> The in-memory implementation below is correct for single-instance servers. In production with multiple instances (Cloud Run, Kubernetes with replicas), each instance has its own circuit breaker state. One instance can have the circuit OPEN while another has it CLOSED — meaning you get partial protection at best.
>
> **For multi-instance production:** Store circuit breaker state in Redis or DynamoDB with TTL-based expiry. Use a distributed counter for failure counts. All instances read/write the same state.
>
> Single-instance or local development: in-memory is fine.

### Types and Configuration

```typescript
type CircuitState = 'CLOSED' | 'OPEN' | 'HALF_OPEN';

interface CircuitBreakerConfig {
  failureThreshold: number;        // Number of failures before opening
  successThreshold: number;         // Successes needed to close from half-open
  timeout: number;                  // Ms to wait before half-open (60000)
  monitoringPeriod: number;         // Ms window for failure tracking (120000)
}

interface CircuitBreakerMetrics {
  state: CircuitState;
  failures: number;
  successes: number;
  consecutiveFailures: number;
  consecutiveSuccesses: number;
  lastFailureTime?: number;
  lastStateChange: number;
}
```

### Full Circuit Breaker Class

```typescript
export class CircuitBreaker {
  private state: CircuitState = 'CLOSED';
  private failureTimestamps: number[] = [];
  private consecutiveSuccesses = 0;
  private consecutiveFailures = 0;
  private lastStateChange = Date.now();

  constructor(private config: CircuitBreakerConfig) {}

  async execute<T>(fn: () => Promise<T>): Promise<T> {
    if (this.state === 'OPEN') {
      if (Date.now() - this.lastStateChange >= this.config.timeout) {
        this.transitionTo('HALF_OPEN');
      } else {
        throw new Error('Circuit breaker is OPEN');
      }
    }

    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  private onSuccess(): void {
    this.consecutiveSuccesses++;
    this.consecutiveFailures = 0;

    if (this.state === 'HALF_OPEN') {
      if (this.consecutiveSuccesses >= this.config.successThreshold) {
        this.transitionTo('CLOSED');
      }
    }
  }

  private onFailure(): void {
    const now = Date.now();
    this.failureTimestamps.push(now);
    this.consecutiveFailures++;
    this.consecutiveSuccesses = 0;

    // Remove failures outside monitoring window
    this.failureTimestamps = this.failureTimestamps.filter(
      (timestamp) => now - timestamp < this.config.monitoringPeriod
    );

    if (this.state === 'HALF_OPEN') {
      this.transitionTo('OPEN');
    } else if (
      this.state === 'CLOSED' &&
      this.failureTimestamps.length >= this.config.failureThreshold
    ) {
      this.transitionTo('OPEN');
    }
  }

  private transitionTo(newState: CircuitState): void {
    this.state = newState;
    this.lastStateChange = Date.now();

    if (newState === 'CLOSED') {
      this.failureTimestamps = [];
      this.consecutiveSuccesses = 0;
      this.consecutiveFailures = 0;
    }
  }

  getMetrics(): CircuitBreakerMetrics {
    return {
      state: this.state,
      failures: this.failureTimestamps.length,
      successes: this.consecutiveSuccesses,
      consecutiveFailures: this.consecutiveFailures,
      consecutiveSuccesses: this.consecutiveSuccesses,
      lastFailureTime: this.failureTimestamps[this.failureTimestamps.length - 1],
      lastStateChange: this.lastStateChange,
    };
  }

  reset(): void {
    this.transitionTo('CLOSED');
  }
}
```

## Bulkhead Pattern

### Semaphore-Based Concurrency Control

```typescript
interface BulkheadConfig {
  maxConcurrent: number;     // Max concurrent executions
  maxQueue: number;          // Max queued requests
  queueTimeout: number;      // Ms before queued request times out
}

export class Bulkhead {
  private activeCount = 0;
  private queue: Array<{
    resolve: (value: void) => void;
    reject: (error: Error) => void;
    timestamp: number;
  }> = [];

  constructor(private config: BulkheadConfig) {}

  async execute<T>(fn: () => Promise<T>): Promise<T> {
    await this.acquire();
    try {
      return await fn();
    } finally {
      this.release();
    }
  }

  private async acquire(): Promise<void> {
    if (this.activeCount < this.config.maxConcurrent) {
      this.activeCount++;
      return;
    }

    if (this.queue.length >= this.config.maxQueue) {
      throw new Error('Bulkhead queue is full');
    }

    return new Promise<void>((resolve, reject) => {
      const timestamp = Date.now();
      this.queue.push({ resolve, reject, timestamp });

      // Timeout handler
      setTimeout(() => {
        const index = this.queue.findIndex((item) => item.timestamp === timestamp);
        if (index !== -1) {
          this.queue.splice(index, 1);
          reject(new Error('Bulkhead queue timeout'));
        }
      }, this.config.queueTimeout);
    });
  }

  private release(): void {
    this.activeCount--;

    const next = this.queue.shift();
    if (next) {
      this.activeCount++;
      next.resolve();
    }
  }

  getMetrics() {
    return {
      activeCount: this.activeCount,
      queuedCount: this.queue.length,
      availableSlots: this.config.maxConcurrent - this.activeCount,
    };
  }
}
```
